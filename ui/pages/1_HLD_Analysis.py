"""AUTOSAR HLD analysis: extraction, question answering, comparison and export."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import (  # noqa: E402
    document_selector,
    page_header,
    page_setup,
    render_answer,
    render_review_controls,
    require_project,
    review_chip,
    show_error,
)

page_setup("HLD Analysis")
project = require_project()

page_header(
    "HLD Analysis",
    "Extract the architecture, interrogate the design with citations, compare revisions, "
    "and export an inventory that carries its evidence with it.",
    kicker="AUTOSAR high-level design",
    chips=[theme.chip(project, "accent")],
)

extract_tab, qa_tab, compare_tab, export_tab = st.tabs(
    ["Architecture", "Ask the design", "Revisions", "Exports"]
)

SEVERITY_TONE = {"high": "danger", "medium": "warning", "low": "neutral"}

# --- Architecture extraction ----------------------------------------------

with extract_tab:
    document = document_selector(project, "hld", "Document to analyse", key="extract_doc")
    if document:
        if st.button("Extract architecture", type="primary"):
            with st.spinner("Parsing the document and resolving entities..."):
                try:
                    st.session_state["hld_extract"] = api_client.post(
                        "/hld/extract",
                        json={"document_id": document["id"]},
                        params={"project": project},
                    )
                except Exception as exc:
                    show_error(exc)

    result = st.session_state.get("hld_extract")
    if result:
        st.markdown("")
        counts = result["counts"]
        theme.stats(
            [(kind.replace("_", " ").title(), count, "") for kind, count in counts.items()]
            or [("Entities", 0, "")]
        )

        st.markdown("")
        entity_tab, dependency_tab, finding_tab, graph_tab = st.tabs(
            ["Inventory", "Dependencies", "Findings", "Dependency map"]
        )

        with entity_tab:
            frame = pd.DataFrame(result["entities"])
            if frame.empty:
                theme.empty_state(
                    "No architecture entities recognised",
                    "The extractor looks for AUTOSAR naming conventions such as SWC_, "
                    "Sig_ and IF_ prefixes, and for port, runnable and PDU declarations.",
                )
            else:
                kinds = sorted(frame["kind"].unique())
                selected = st.multiselect("Filter by kind", kinds, default=kinds)
                view = frame[frame["kind"].isin(selected)].copy()
                view["pages"] = view["pages"].map(lambda pages: ", ".join(map(str, pages)))
                view["sections"] = view["sections"].map(lambda parts: " / ".join(parts))
                st.dataframe(
                    view[["name", "kind", "detail", "pages", "sections", "occurrences"]],
                    hide_index=True,
                    use_container_width=True,
                    height=430,
                    column_config={
                        "name": st.column_config.TextColumn("Element", width="medium"),
                        "kind": st.column_config.TextColumn("Kind"),
                        "detail": st.column_config.TextColumn("Detail", width="medium"),
                        "pages": st.column_config.TextColumn("Pages"),
                        "sections": st.column_config.TextColumn("Section", width="medium"),
                        "occurrences": st.column_config.NumberColumn("Mentions", format="%d"),
                    },
                )
                st.caption(
                    f"{len(view)} of {len(frame)} elements shown. Every row is traceable to "
                    "the page it was found on."
                )

        with dependency_tab:
            dependencies = pd.DataFrame(result["dependencies"])
            if dependencies.empty:
                theme.empty_state(
                    "No interactions recognised",
                    "Dependencies are inferred from arrow notation and from verbs such as "
                    "sends, receives, calls and provides.",
                )
            else:
                st.dataframe(
                    dependencies,
                    hide_index=True,
                    use_container_width=True,
                    height=430,
                    column_config={
                        "source": st.column_config.TextColumn("From", width="medium"),
                        "relation": st.column_config.TextColumn("Relation"),
                        "target": st.column_config.TextColumn("To", width="medium"),
                    },
                )

        with finding_tab:
            findings = result["findings"]
            if not findings:
                theme.callout(
                    "The completeness checks found no isolated components, undefined "
                    "endpoints or naming inconsistencies.",
                    title="Nothing flagged.",
                    tone="success",
                )
            else:
                theme.section(
                    f"{len(findings)} potential issue(s)",
                    "Produced by deterministic checks, not by the model. Each one names the "
                    "element and the pages it appears on.",
                )
                for finding in findings:
                    with st.container(border=True):
                        theme.card_marker()
                        head = st.columns([4, 1])
                        head[0].markdown(
                            f"**{finding['category'].replace('_', ' ').title()}** — "
                            f"`{finding['entity']}`"
                        )
                        head[1].markdown(
                            theme.chip(
                                finding["severity"].title(),
                                SEVERITY_TONE.get(finding["severity"], "neutral"),
                            ),
                            unsafe_allow_html=True,
                        )
                        pages = finding["pages"]
                        if isinstance(pages, (list, tuple)):
                            pages = ", ".join(str(page) for page in pages)
                        st.caption(f"Page {pages}" if pages else "Page unknown")
                        st.markdown(finding["message"])
                        if finding["evidence"]:
                            st.caption(f"Evidence: {finding['evidence']}")

        with graph_tab:
            if result["dependencies"]:
                try:
                    st.graphviz_chart(result["dot"], use_container_width=True)
                except Exception:
                    st.code(result["dot"], language="dot")
                    theme.callout(
                        "Install the Graphviz system package to render this diagram inline. "
                        "The DOT source above can be rendered with any Graphviz tool.",
                        tone="warning",
                    )
            else:
                theme.empty_state("No dependencies to draw")

        st.markdown("")
        render_review_controls(result["artifact_id"], project, "hldextract")

# --- Question answering ----------------------------------------------------

with qa_tab:
    EXAMPLES = [
        "Which components produce and consume Sig_VehicleSpeed?",
        "What interfaces does SWC_DoorControl provide and require?",
        "Describe the central locking functional flow.",
        "Which basic software modules are configured for this ECU?",
        "What open points remain in the design?",
    ]

    theme.callout(
        "Answers are assembled only from retrieved passages. Every claim carries a marker "
        "that resolves to a page, and any marker pointing at something that was not "
        "retrieved is stripped out and reported.",
        tone="neutral",
    )

    question = st.text_area(
        "Question",
        height=90,
        placeholder=EXAMPLES[0],
        key="hld_question",
    )
    st.caption("Try: " + "  ·  ".join(EXAMPLES[1:4]))

    with st.expander("Retrieval settings"):
        document = document_selector(
            project, "hld", "Restrict to one document", key="qa_doc"
        )
        restrict = st.checkbox("Only search the selected document", value=False)
        top_k = st.slider("Passages to retrieve", 3, 12, 6)

    if st.button("Ask", type="primary") and question.strip():
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
            st.markdown("")
            render_answer(result)
            if result.get("artifact_id"):
                render_review_controls(result["artifact_id"], project, "hldqa")

# --- Revision comparison ---------------------------------------------------

with compare_tab:
    theme.section(
        "Compare two revisions",
        "Both documents are re-extracted and their inventories diffed, so the report "
        "reflects the design, not the text.",
    )
    columns = st.columns(2, gap="medium")
    with columns[0]:
        baseline = document_selector(project, "hld", "Baseline revision", key="cmp_base")
    with columns[1]:
        revision = document_selector(
            project, "hld", "New revision", key="cmp_rev", default_index=1
        )

    if baseline and revision and st.button("Compare revisions", type="primary"):
        if baseline["id"] == revision["id"]:
            theme.callout("Select two different documents to compare.", tone="warning")
        else:
            with st.spinner("Extracting both revisions and diffing..."):
                try:
                    st.session_state["hld_diff"] = api_client.post(
                        "/hld/compare",
                        json={
                            "baseline_document_id": baseline["id"],
                            "revision_document_id": revision["id"],
                        },
                        params={"project": project},
                    )
                except Exception as exc:
                    show_error(exc)

    diff = st.session_state.get("hld_diff")
    if diff:
        st.markdown("")
        summary = diff["summary"]
        theme.stats([
            ("Added", summary["added"], "elements"),
            ("Removed", summary["removed"], "elements"),
            ("Changed", summary["changed"], "elements"),
            ("New links", summary["dependencies_added"], "dependencies"),
            ("Dropped links", summary["dependencies_removed"], "dependencies"),
        ])
        st.caption(
            f"{diff['baseline']['name']} ({diff['baseline']['version']}) "
            f"compared against {diff['revision']['name']} ({diff['revision']['version']})"
        )

        st.markdown("")
        for label, key in [
            ("Added elements", "added"),
            ("Removed elements", "removed"),
            ("Changed elements", "changed"),
            ("Added dependencies", "dependencies_added"),
            ("Removed dependencies", "dependencies_removed"),
        ]:
            rows = diff[key]
            with st.expander(f"{label}  ({len(rows)})"):
                if rows:
                    st.dataframe(
                        pd.DataFrame(rows), hide_index=True, use_container_width=True
                    )
                else:
                    st.caption("None.")

# --- Exports ---------------------------------------------------------------

with export_tab:
    try:
        inventories = api_client.get("/hld/inventories", {"project": project})
    except Exception as exc:
        show_error(exc)
        inventories = []

    if not inventories:
        theme.empty_state(
            "No stored inventories",
            "Run an extraction on the Architecture tab to create one.",
        )
    else:
        theme.section(
            "Stored inventories",
            "Each export carries its reference, citations and review state.",
        )
        for inventory in inventories:
            with st.container(border=True):
                theme.card_marker()
                columns = st.columns([4, 1.2, 1, 1])
                columns[0].markdown(
                    f"{theme.ref(inventory['ref'])} &nbsp; {inventory['title']}",
                    unsafe_allow_html=True,
                )
                columns[0].caption(
                    f"{inventory['entity_count']} elements · "
                    f"{inventory['finding_count']} potential issues · "
                    f"{(inventory['created_at'] or '')[:16].replace('T', ' ')}"
                )
                columns[1].markdown(
                    review_chip(inventory["review_status"]), unsafe_allow_html=True
                )
                for column, fmt in [(columns[2], "csv"), (columns[3], "json")]:
                    try:
                        payload = api_client.download(
                            "/hld/export",
                            {"project": project, "artifact_id": inventory["id"], "fmt": fmt},
                        )
                        column.download_button(
                            fmt.upper(),
                            payload,
                            file_name=f"{inventory['ref']}.{fmt}",
                            key=f"dl_{inventory['id']}_{fmt}",
                            use_container_width=True,
                        )
                    except Exception:
                        column.caption("—")
