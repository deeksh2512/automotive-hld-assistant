"""Document ingestion and the project knowledge inventory."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

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
approved = [d for d in documents if d.get("approved_source")]

page_header(
    "Documents",
    kicker=project,
    chips=[
        theme.chip(f"{len(indexed)} indexed", "success" if indexed else "neutral"),
        theme.chip(f"{len(failed)} failed", "danger") if failed else "",
    ],
)

theme.kpis(
    [
        ("Indexed", len(indexed), f"{len(documents)} ingested"),
        ("Passages", sum(d["chunk_count"] for d in documents), "section-aligned"),
        ("Approved sources", len(approved), "released material"),
        ("Failed", len(failed), "need attention" if failed else "none"),
    ],
    tones=["", "", "", "danger" if failed else ""],
)

inventory_tab, upload_tab, samples_tab = st.tabs(["Inventory", "Upload", "Bundled samples"])

with inventory_tab:
    theme.table(
        [
            {
                "name": document["name"],
                "type": document["doc_type"].replace("_", " "),
                "rev": document["version_label"],
                "approved": "Approved" if document.get("approved_source") else "Unverified",
                "passages": document["chunk_count"],
                "status": document["status"],
                "created": (document["created_at"] or "")[:16].replace("T", " "),
            }
            for document in documents
        ],
        columns=[
            {"key": "name", "label": "Document", "style": "mono"},
            {"key": "type", "label": "Type", "style": "muted", "width": "13%"},
            {"key": "rev", "label": "Rev", "style": "mono", "width": "7%"},
            {
                "key": "approved",
                "label": "Source",
                "style": "chip",
                "width": "11%",
                "tones": {"Approved": "success", "Unverified": "neutral"},
            },
            {"key": "passages", "label": "Passages", "style": "num", "width": "9%"},
            {
                "key": "status",
                "label": "Status",
                "style": "chip",
                "width": "10%",
                "tones": {"indexed": "success", "failed": "danger"},
            },
            {"key": "created", "label": "Indexed", "style": "mono", "width": "14%"},
        ],
        max_height="28rem",
        empty="Nothing indexed yet. Upload a design document or load the bundled samples.",
    )

    for document in failed:
        theme.callout(
            f"<b>{theme.esc(document['name'])}</b> — {theme.esc(document['error'])}",
            title="Ingestion failed.",
            tone="danger",
        )

    if documents:
        names = {f"{d['name']} ({d['version_label']})": d["id"] for d in documents}
        remove = st.columns([3, 1, 4], gap="small")
        choice = remove[0].selectbox("Remove a document", list(names))
        with remove[1]:
            st.markdown('<div style="height:1.3rem"></div>', unsafe_allow_html=True)
            if st.button("Delete", use_container_width=True):
                try:
                    api_client.delete(f"/documents/{names[choice]}", {"project": project})
                    st.rerun()
                except Exception as exc:
                    show_error(exc)

with upload_tab:
    with st.form("upload_form"):
        files = st.file_uploader(
            "Design documents",
            type=UPLOAD_TYPES,
            accept_multiple_files=True,
            help="PDF, Word, spreadsheets, ARXML, markdown and source files. "
                 "Scanned pages fall back to OCR.",
        )
        columns = st.columns([2, 1, 1, 1], gap="small")
        doc_type = columns[0].selectbox("Document type", DOC_TYPES)
        version_label = columns[1].text_input("Version label", value="v1")
        with columns[2]:
            st.markdown('<div style="height:1.3rem"></div>', unsafe_allow_html=True)
            approved_source = st.checkbox("Approved source", value=True)
        with columns[3]:
            st.markdown('<div style="height:1.3rem"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Parse and index", type="primary", use_container_width=True
            )

    st.caption(
        "Parsing, embedding and storage are local. Only released material should be "
        "marked as an approved source."
    )

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
                        "approved_source": str(approved_source).lower(),
                    },
                    params={"project": project},
                )
                if result["status"] == "indexed":
                    theme.callout(
                        f"<b>{theme.esc(result['name'])}</b> — "
                        f"{result['chunk_count']} passages indexed.",
                        tone="success",
                    )
                else:
                    theme.callout(
                        f"<b>{theme.esc(result['name'])}</b> — {theme.esc(result['error'])}",
                        tone="danger",
                    )
            except Exception as exc:
                show_error(exc)
            progress.progress(index / len(files), text=f"Indexed {index} of {len(files)}")
        progress.empty()
    elif submitted:
        theme.callout("Select at least one file before indexing.", tone="warning")

with samples_tab:
    theme.table(
        [
            {
                "name": "sample_hld_body_control.md",
                "rev": "rev-a",
                "content": "Central locking, window control, lighting and the diagnostic "
                           "interface: components, ports, interfaces, signals, runnables.",
            },
            {
                "name": "sample_hld_body_control_rev_b.md",
                "rev": "rev-b",
                "content": "The same design after a change cycle, with elements added, "
                           "removed and renamed so the revision diff has something to report.",
            },
        ],
        columns=[
            {"key": "name", "label": "File", "style": "mono", "width": "28%"},
            {"key": "rev", "label": "Rev", "style": "mono", "width": "8%"},
            {"key": "content", "label": "Contents", "style": "clamp"},
        ],
        max_height="none",
        note="Synthetic data. Contains no real project material.",
    )

    if st.button("Load the bundled samples", type="primary"):
        with st.spinner("Parsing, embedding and indexing..."):
            try:
                results = api_client.post("/documents/load-samples", params={"project": project})
            except Exception as exc:
                show_error(exc)
                results = []
        if results:
            theme.callout(f"Indexed {len(results)} sample document(s).", tone="success")
            st.rerun()
        else:
            theme.callout("The samples are already loaded in this workspace.", tone="neutral")
