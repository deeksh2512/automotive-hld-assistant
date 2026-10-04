"""AUTOSAR HLD document analysis workspace."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client  # noqa: E402
from ui.common import (  # noqa: E402
    document_selector,
    page_setup,
    render_answer,
    render_review_controls,
    require_project,
    review_badge,
    show_error,
)

page_setup("AUTOSAR HLD Document Analysis")
project = require_project()

st.caption(
    "Extract architecture knowledge from High-Level Design documents, ask questions "
    "with citations, compare revisions, and export structured findings."
)

qa_tab, extract_tab, compare_tab, export_tab = st.tabs(
    ["Ask the documents", "Architecture extraction", "Revision comparison", "Stored inventories"]
)

with qa_tab:
    document = document_selector(project, "hld", "Restrict to one document (optional)", key="qa_doc")
    restrict = st.checkbox("Restrict the search to the selected document", value=False)

    examples = [
        "Which components produce and consume Sig_VehicleSpeed?",
        "What interfaces does SWC_DoorControl provide and require?",
        "Describe the central locking functional flow.",
        "Which basic software modules are configured for this ECU?",
        "What open points remain in the design?",
    ]
    st.caption("Examples: " + " · ".join(f"_{example}_" for example in examples))

    question = st.text_area("Question", height=90, placeholder=examples[0])
    columns = st.columns([1, 3])
    top_k = columns[0].slider("Passages to retrieve", 3, 12, 6)
    if columns[1].button("Ask", type="primary") and question.strip():
        with st.spinner("Retrieving evidence..."):
            try:
                result = api_client.post(
                    "/query",
                    json={
                        "question": question,
                        "module": "hld",
                        "top_k": top_k,
                        "document_id": document["id"] if (document and restrict) else None,
                    },
                    params={"project": project},
                )
            except Exception as exc:
                show_error(exc)
                result = None
        if result:
            render_answer(result)
            if result.get("artifact_id"):
                render_review_controls(result["artifact_id"], project, "hldqa")

with extract_tab:
    document = document_selector(project, "hld", "Document to analyse", key="extract_doc")
    if document and st.button("Extract architecture entities", type="primary"):
        with st.spinner("Parsing and extracting..."):
            try:
                result = api_client.post(
                    "/hld/extract",
                    json={"document_id": document["id"]},
                    params={"project": project},
                )
            except Exception as exc:
                show_error(exc)
                result = None
        if result:
            st.session_state["hld_extract"] = result

    result = st.session_state.get("hld_extract")
    if result:
        counts = result["counts"]
        metric_columns = st.columns(len(counts) or 1)
        for column, (kind, count) in zip(metric_columns, counts.items()):
            column.metric(kind.replace("_", " ").title(), count)

        entity_tab, dependency_tab, finding_tab, graph_tab = st.tabs(
            ["Entities", "Dependencies", "Potential issues", "Dependency map"]
        )

        with entity_tab:
            frame = pd.DataFrame(result["entities"])
            if not frame.empty:
                kinds = sorted(frame["kind"].unique())
                selected = st.multiselect("Filter by kind", kinds, default=kinds)
                frame = frame[frame["kind"].isin(selected)]
                frame["pages"] = frame["pages"].map(lambda pages: ", ".join(map(str, pages)))
                frame["sections"] = frame["sections"].map(lambda s: " / ".join(s))
                st.dataframe(frame, hide_index=True, use_container_width=True)
            else:
                st.info("No architecture entities were recognised in this document.")

        with dependency_tab:
            dependencies = pd.DataFrame(result["dependencies"])
            if not dependencies.empty:
                st.dataframe(dependencies, hide_index=True, use_container_width=True)
            else:
                st.info("No component interactions were recognised.")

        with finding_tab:
            findings = result["findings"]
            if not findings:
                st.success("No inconsistencies detected by the completeness checks.")
            for finding in findings:
                icon = {"high": "error", "medium": "warning", "low": "info"}[finding["severity"]]
                getattr(st, icon)(
                    f"**{finding['category'].replace('_', ' ')}** · "
                    f"{finding['entity']} · pages {finding['pages']}\n\n{finding['message']}"
                )
                if finding["evidence"]:
                    st.caption(f"Evidence: {finding['evidence']}")

        with graph_tab:
            if result["dependencies"]:
                try:
                    st.graphviz_chart(result["dot"], use_container_width=True)
                except Exception:
                    st.code(result["dot"], language="dot")
                    st.caption(
                        "Install the Graphviz system package to render this diagram inline."
                    )
            else:
                st.info("No dependencies to draw.")

        render_review_controls(result["artifact_id"], project, "hldextract")

with compare_tab:
    st.markdown("Compare two indexed revisions of the same design to see what changed.")
    baseline = document_selector(project, "hld", "Baseline revision", key="cmp_base")
    revision = document_selector(project, "hld", "New revision", key="cmp_rev")
    if baseline and revision and st.button("Compare", type="primary"):
        if baseline["id"] == revision["id"]:
            st.warning("Select two different documents.")
        else:
            with st.spinner("Comparing..."):
                try:
                    diff = api_client.post(
                        "/hld/compare",
                        json={
                            "baseline_document_id": baseline["id"],
                            "revision_document_id": revision["id"],
                        },
                        params={"project": project},
                    )
                except Exception as exc:
                    show_error(exc)
                    diff = None
            if diff:
                summary = diff["summary"]
                columns = st.columns(5)
                columns[0].metric("Added", summary["added"])
                columns[1].metric("Removed", summary["removed"])
                columns[2].metric("Changed", summary["changed"])
                columns[3].metric("New links", summary["dependencies_added"])
                columns[4].metric("Removed links", summary["dependencies_removed"])

                for label, key in [
                    ("Added entities", "added"),
                    ("Removed entities", "removed"),
                    ("Changed entities", "changed"),
                    ("Added dependencies", "dependencies_added"),
                    ("Removed dependencies", "dependencies_removed"),
                ]:
                    rows = diff[key]
                    with st.expander(f"{label} ({len(rows)})"):
                        if rows:
                            st.dataframe(
                                pd.DataFrame(rows), hide_index=True, use_container_width=True
                            )
                        else:
                            st.caption("None.")

with export_tab:
    try:
        inventories = api_client.get("/hld/inventories", {"project": project})
    except Exception as exc:
        show_error(exc)
        inventories = []

    if not inventories:
        st.info("Run an extraction first to create a stored inventory.")
    else:
        for inventory in inventories:
            with st.container(border=True):
                columns = st.columns([3, 1, 1, 1])
                columns[0].markdown(f"**{inventory['ref']}** · {inventory['title']}")
                columns[0].caption(
                    f"{inventory['entity_count']} entities, "
                    f"{inventory['finding_count']} potential issues"
                )
                columns[1].markdown(
                    review_badge(inventory["review_status"]), unsafe_allow_html=True
                )
                for column, fmt, label in [(columns[2], "csv", "CSV"), (columns[3], "json", "JSON")]:
                    try:
                        payload = api_client.download(
                            "/hld/export",
                            {"project": project, "artifact_id": inventory["id"], "fmt": fmt},
                        )
                        column.download_button(
                            label,
                            payload,
                            file_name=f"{inventory['ref']}.{fmt}",
                            key=f"dl_{inventory['id']}_{fmt}",
                        )
                    except Exception:
                        column.caption("-")
