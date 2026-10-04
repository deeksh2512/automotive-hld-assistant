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

SEVERITY_TONE = {"high": "danger", "medium": "warning", "low": "neutral"}
KIND_TONE = {
    "component": "accent",
    "bsw_module": "neutral",
    "signal": "warning",
    "pdu": "warning",
    "interface": "info",
    "runnable": "success",
    "port": "neutral",
}

page_header(
    "HLD Analysis",
    kicker="AUTOSAR high-level design",
    chips=[theme.chip(project, "accent")],
)

# --- Toolbar ---------------------------------------------------------------

with st.container(border=True):
    theme.panel_bar("Active document")
    bar = st.columns([4, 1], gap="small")
    with bar[0]:
        document = document_selector(
            project, "hld", "Document to analyse", key="extract_doc"
        )
    with bar[1]:
        st.markdown(
            '<div style="height:1.42rem"></div>', unsafe_allow_html=True
        )
        extract = st.button(
            "Extract", type="primary", use_container_width=True, disabled=document is None
        )

if document and extract:
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
    counts = result["counts"]
    theme.kpis(
        [(kind.replace("_", " ").title(), count, "") for kind, count in counts.items()]
        or [("Entities", 0, "")]
    )
    render_review_controls(result["artifact_id"], project, "hldextract")

(
    entity_tab,
    dependency_tab,
    finding_tab,
    graph_tab,
    qa_tab,
    compare_tab,
    export_tab,
) = st.tabs(
    ["Inventory", "Dependencies", "Findings", "Map", "Ask", "Revisions", "Exports"]
)

# --- Architecture inventory ------------------------------------------------

with entity_tab:
    if not result:
        theme.empty_state(
            "No extraction loaded",
            "Choose a document above and run <b>Extract</b> to build the inventory.",
        )
    else:
        frame = pd.DataFrame(result["entities"])
        if frame.empty:
            theme.empty_state(
                "No architecture entities recognised",
                "The extractor looks for AUTOSAR naming conventions such as SWC_, "
                "Sig_ and IF_ prefixes, and for port, runnable and PDU declarations.",
            )
        else:
            kinds = sorted(frame["kind"].unique())
            filters = st.columns([2, 2], gap="small")
            selected = filters[0].multiselect("Kind", kinds, default=kinds)
            search = filters[1].text_input("Search", placeholder="Element name or detail")

            view = frame[frame["kind"].isin(selected)].copy()
            if search.strip():
                needle = search.strip().lower()
                view = view[
                    view["name"].str.lower().str.contains(needle, regex=False)
                    | view["detail"].fillna("").str.lower().str.contains(needle, regex=False)
                ]

            theme.table(
                [
                    {
                        "name": row["name"],
                        "kind": row["kind"],
                        "detail": row["detail"],
                        "pages": ", ".join(map(str, row["pages"])),
                        "sections": " / ".join(row["sections"]),
                        "occurrences": row["occurrences"],
                    }
                    for row in view.to_dict("records")
                ],
                columns=[
                    {"key": "name", "label": "Element", "style": "mono", "width": "20%"},
                    {
                        "key": "kind",
                        "label": "Kind",
                        "style": "chip",
                        "width": "11%",
                        "tones": KIND_TONE,
                    },
                    {"key": "detail", "label": "Detail", "style": "clamp"},
                    {"key": "pages", "label": "Pages", "style": "num", "width": "7%"},
                    {
                        "key": "sections",
                        "label": "Section",
                        "style": "clamp-muted",
                        "width": "20%",
                    },
                    {"key": "occurrences", "label": "Refs", "style": "num", "width": "6%"},
                ],
                max_height="27rem",
                empty="No elements match the current filter.",
            )
            theme.table_note(
                f"{len(view)} of {len(frame)} elements · every row traceable to a page"
            )

# --- Dependencies ----------------------------------------------------------

with dependency_tab:
    if not result:
        theme.empty_state("No extraction loaded", "Run <b>Extract</b> to resolve dependencies.")
    else:
        theme.table(
            result["dependencies"],
            columns=[
                {"key": "source", "label": "From", "style": "mono", "width": "32%"},
                {"key": "relation", "label": "Relation", "style": "muted", "width": "16%"},
                {"key": "target", "label": "To", "style": "mono"},
            ],
            max_height="29rem",
            empty="No interactions recognised in this document.",
        )
        theme.table_note(f"{len(result['dependencies'])} interactions")

# --- Findings --------------------------------------------------------------

with finding_tab:
    if not result:
        theme.empty_state("No extraction loaded", "Run <b>Extract</b> to run the checks.")
    elif not result["findings"]:
        theme.callout(
            "No isolated components, undefined endpoints or naming inconsistencies.",
            title="Nothing flagged.",
            tone="success",
        )
    else:
        findings = result["findings"]
        rows = []
        for finding in findings:
            pages = finding["pages"]
            if isinstance(pages, (list, tuple)):
                pages = ", ".join(str(page) for page in pages)
            rows.append(
                {
                    "severity": finding["severity"].title(),
                    "category": finding["category"].replace("_", " ").title(),
                    "entity": finding["entity"],
                    "pages": pages or "—",
                    "message": finding["message"],
                }
            )
        theme.table(
            rows,
            columns=[
                {
                    "key": "severity",
                    "label": "Severity",
                    "style": "chip",
                    "width": "9%",
                    "tones": {
                        level.title(): tone for level, tone in SEVERITY_TONE.items()
                    },
                },
                {"key": "category", "label": "Check", "style": "strong", "width": "16%"},
                {"key": "entity", "label": "Element", "style": "mono", "width": "18%"},
                {"key": "pages", "label": "Pages", "style": "num", "width": "7%"},
                {"key": "message", "label": "Observation", "style": "clamp"},
            ],
            max_height="29rem",
        )
        theme.table_note(
            f"{len(findings)} potential issue(s) from deterministic checks, not the model"
        )

# --- Dependency map --------------------------------------------------------

with graph_tab:
    if not result:
        theme.empty_state("No extraction loaded", "Run <b>Extract</b> to draw the map.")
    elif result["dependencies"]:
        try:
            st.graphviz_chart(result["dot"], use_container_width=True)
        except Exception:
            st.code(result["dot"], language="dot")
            theme.callout(
                "Install the Graphviz system package to render this diagram inline.",
                tone="warning",
            )
    else:
        theme.empty_state("No dependencies to draw")

# --- Question answering ----------------------------------------------------

with qa_tab:
    EXAMPLES = [
        "Which components produce and consume Sig_VehicleSpeed?",
        "What interfaces does SWC_DoorControl provide and require?",
        "Describe the central locking functional flow.",
        "Which basic software modules are configured for this ECU?",
    ]

    question = st.text_area(
        "Question",
        height=78,
        placeholder=EXAMPLES[0],
        key="hld_question",
    )
    controls = st.columns([1, 1.6, 1.4], gap="small")
    with controls[0]:
        st.markdown('<div style="height:1.42rem"></div>', unsafe_allow_html=True)
        ask = st.button("Ask", type="primary")
    with controls[1]:
        top_k = st.slider("Passages", 3, 12, 6)
    with controls[2]:
        restrict = st.checkbox("Restrict to one document", value=False)

    qa_document = None
    if restrict:
        qa_document = document_selector(
            project, "hld", "Document", key="qa_doc"
        )

    st.caption("Examples · " + "  ·  ".join(EXAMPLES[1:]))

    if ask and question.strip():
        with st.spinner("Retrieving evidence..."):
            try:
                answer = api_client.post(
                    "/query",
                    json={
                        "question": question,
                        "module": "hld",
                        "top_k": top_k,
                        "document_id": qa_document["id"] if qa_document else None,
                    },
                    params={"project": project},
                )
            except Exception as exc:
                show_error(exc)
                answer = None
        if answer:
            render_answer(answer)
            if answer.get("artifact_id"):
                render_review_controls(answer["artifact_id"], project, "hldqa")

# --- Revision comparison ---------------------------------------------------

with compare_tab:
    picker = st.columns([2, 2, 1], gap="small")
    with picker[0]:
        baseline = document_selector(project, "hld", "Baseline revision", key="cmp_base")
    with picker[1]:
        revision = document_selector(
            project, "hld", "New revision", key="cmp_rev", default_index=1
        )
    with picker[2]:
        st.markdown('<div style="height:1.42rem"></div>', unsafe_allow_html=True)
        compare = st.button(
            "Compare",
            type="primary",
            use_container_width=True,
            disabled=not (baseline and revision),
        )

    if baseline and revision and compare:
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
        summary = diff["summary"]
        theme.kpis(
            [
                ("Added", summary["added"], "elements"),
                ("Removed", summary["removed"], "elements"),
                ("Changed", summary["changed"], "elements"),
                ("New links", summary["dependencies_added"], "dependencies"),
                ("Dropped links", summary["dependencies_removed"], "dependencies"),
            ]
        )
        theme.table_note(
            f"{diff['baseline']['name']} ({diff['baseline']['version']}) compared against "
            f"{diff['revision']['name']} ({diff['revision']['version']})"
        )

        for label, key, columns in [
            (
                "Added elements",
                "added",
                [
                    {"key": "name", "label": "Element", "style": "mono"},
                    {"key": "kind", "label": "Kind", "style": "chip", "tones": KIND_TONE},
                    {"key": "detail", "label": "Detail", "style": "clamp"},
                ],
            ),
            (
                "Removed elements",
                "removed",
                [
                    {"key": "name", "label": "Element", "style": "mono"},
                    {"key": "kind", "label": "Kind", "style": "chip", "tones": KIND_TONE},
                    {"key": "detail", "label": "Detail", "style": "clamp"},
                ],
            ),
            (
                "Changed elements",
                "changed",
                [
                    {"key": "name", "label": "Element", "style": "mono"},
                    {"key": "kind", "label": "Kind", "style": "chip", "tones": KIND_TONE},
                    {"key": "detail", "label": "Detail", "style": "clamp"},
                ],
            ),
            (
                "Added dependencies",
                "dependencies_added",
                [
                    {"key": "source", "label": "From", "style": "mono"},
                    {"key": "relation", "label": "Relation", "style": "muted"},
                    {"key": "target", "label": "To", "style": "mono"},
                ],
            ),
            (
                "Removed dependencies",
                "dependencies_removed",
                [
                    {"key": "source", "label": "From", "style": "mono"},
                    {"key": "relation", "label": "Relation", "style": "muted"},
                    {"key": "target", "label": "To", "style": "mono"},
                ],
            ),
        ]:
            rows = diff[key]
            with st.expander(f"{label}  ({len(rows)})"):
                if rows:
                    present = [
                        column for column in columns if column["key"] in rows[0]
                    ] or [
                        {"key": name, "label": name, "style": "clamp"} for name in rows[0]
                    ]
                    theme.table(rows, present, max_height="20rem")
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
            "Run an extraction to create one.",
        )
    else:
        for inventory in inventories:
            with st.container(border=True):
                theme.panel_marker()
                columns = st.columns([4, 1.2, 0.9, 0.9], gap="small")
                columns[0].markdown(
                    f"{theme.ref(inventory['ref'])} &nbsp; {theme.esc(inventory['title'])}"
                    f"<div style='font-size:.72rem;color:#94A3B8;margin-top:.15rem'>"
                    f"{inventory['entity_count']} elements · "
                    f"{inventory['finding_count']} issues · "
                    f"{(inventory['created_at'] or '')[:16].replace('T', ' ')}</div>",
                    unsafe_allow_html=True,
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
