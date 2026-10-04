"""Document ingestion and the project knowledge inventory."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import page_header, page_setup, require_project, show_error  # noqa: E402

page_setup("Documents")
project = require_project()

MODULE = "hld"
DOC_TYPES = ["hld", "interface_spec", "architecture", "component_catalogue", "document"]
UPLOAD_TYPES = [
    "pdf", "docx", "txt", "md", "xlsx", "csv", "c", "h", "cpp", "hpp", "py", "arxml", "xml",
]

try:
    documents = api_client.get("/documents", {"project": project})
except Exception as exc:
    show_error(exc)
    documents = []

indexed = [d for d in documents if d["status"] == "indexed"]
failed = [d for d in documents if d["status"] == "failed"]

page_header(
    "Documents",
    "Source material is parsed, split on section boundaries, embedded locally and stored "
    "in a vector collection scoped to this workspace.",
    kicker="Knowledge base",
    chips=[
        theme.chip(f"{len(indexed)} indexed", "success" if indexed else "neutral"),
        theme.chip(f"{len(failed)} failed", "danger") if failed else "",
    ],
)

upload_tab, samples_tab, inventory_tab = st.tabs(
    ["Upload", "Bundled samples", "Inventory"]
)

with upload_tab:
    theme.callout(
        "Only documents released through your official process should be marked as an "
        "approved source. Everything stays on this machine: parsing, embedding and storage "
        "are all local.",
        tone="neutral",
    )
    with st.form("upload_form"):
        files = st.file_uploader(
            "Design documents",
            type=UPLOAD_TYPES,
            accept_multiple_files=True,
            help="PDF, Word, spreadsheets, ARXML, markdown and source files are supported. "
                 "Scanned pages fall back to OCR.",
        )
        columns = st.columns([2, 1, 1])
        doc_type = columns[0].selectbox("Document type", DOC_TYPES)
        version_label = columns[1].text_input("Version label", value="v1")
        approved = columns[2].checkbox("Approved source", value=True)
        submitted = st.form_submit_button("Parse and index", type="primary")

    if submitted and files:
        progress = st.progress(0.0, text="Indexing...")
        for index, file in enumerate(files, start=1):
            try:
                result = api_client.upload(
                    "/documents/upload",
                    file,
                    data={
                        "module": MODULE,
                        "doc_type": doc_type,
                        "version_label": version_label,
                        "approved_source": str(approved).lower(),
                    },
                    params={"project": project},
                )
                if result["status"] == "indexed":
                    theme.callout(
                        f"<b>{result['name']}</b> — {result['chunk_count']} passages indexed.",
                        tone="success",
                    )
                else:
                    theme.callout(
                        f"<b>{result['name']}</b> — {result['error']}", tone="danger"
                    )
            except Exception as exc:
                show_error(exc)
            progress.progress(index / len(files), text=f"Indexed {index} of {len(files)}")
        progress.empty()
    elif submitted:
        theme.callout("Select at least one file before indexing.", tone="warning")

with samples_tab:
    theme.section(
        "Synthetic sample design",
        "Two revisions of a Body Control Module HLD, so extraction and comparison can be "
        "tried immediately. They contain no real project data.",
    )
    columns = st.columns(2, gap="medium")
    with columns[0]:
        theme.card(
            "Body Control Module HLD, revision A",
            "Components, ports, interfaces, signals and runnables for central locking, "
            "window control, lighting and the diagnostic interface.",
        )
    with columns[1]:
        theme.card(
            "Body Control Module HLD, revision B",
            "The same design after a change cycle, with components added, removed and "
            "renamed, so the revision diff has something to report.",
        )

    if st.button("Load the bundled samples", type="primary"):
        with st.spinner("Parsing, embedding and indexing..."):
            try:
                results = api_client.post("/documents/load-samples", params={"project": project})
            except Exception as exc:
                show_error(exc)
                results = []
        if results:
            theme.callout(
                f"Indexed {len(results)} sample document(s). Open HLD Analysis to continue.",
                tone="success",
            )
            st.rerun()
        else:
            theme.callout("The samples are already loaded in this workspace.", tone="neutral")

with inventory_tab:
    if not documents:
        theme.empty_state(
            "Nothing indexed yet",
            "Upload a design document, or load the bundled samples, to build the knowledge base.",
        )
    else:
        frame = pd.DataFrame(documents)
        st.dataframe(
            frame[["name", "doc_type", "version_label", "approved_source",
                   "chunk_count", "status", "created_at"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "name": st.column_config.TextColumn("Document", width="large"),
                "doc_type": st.column_config.TextColumn("Type"),
                "version_label": st.column_config.TextColumn("Version"),
                "approved_source": st.column_config.CheckboxColumn("Approved"),
                "chunk_count": st.column_config.NumberColumn("Passages", format="%d"),
                "status": st.column_config.TextColumn("Status"),
                "created_at": st.column_config.DatetimeColumn("Indexed", format="YYYY-MM-DD HH:mm"),
            },
        )

        for document in failed:
            theme.callout(
                f"<b>{document['name']}</b> — {document['error']}",
                title="Ingestion failed.",
                tone="danger",
            )

        st.divider()
        theme.section("Remove a document", "Deletes it from the vector index and from disk.")
        names = {f"{d['name']} ({d['version_label']})": d["id"] for d in documents}
        columns = st.columns([3, 1])
        choice = columns[0].selectbox("Document", list(names), label_visibility="collapsed")
        if columns[1].button("Delete", use_container_width=True):
            try:
                api_client.delete(f"/documents/{names[choice]}", {"project": project})
                st.rerun()
            except Exception as exc:
                show_error(exc)
