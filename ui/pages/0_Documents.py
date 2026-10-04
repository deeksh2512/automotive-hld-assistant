"""Document ingestion and the project knowledge inventory."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client  # noqa: E402
from ui.common import page_setup, require_project, show_error  # noqa: E402

page_setup("Documents and Knowledge Sources")
project = require_project()

MODULES = {"hld": "AUTOSAR HLD"}

DOC_TYPES = {
    "hld": ["hld", "interface_spec", "architecture", "component_catalogue", "document"],
}

upload_tab, samples_tab, inventory_tab = st.tabs(
    ["Upload", "Bundled samples", "Project inventory"]
)

with upload_tab:
    st.markdown(
        "Documents are parsed, chunked by section, embedded locally and stored in a "
        "collection scoped to this project. Nothing leaves this machine."
    )
    module = "hld"
    with st.form("upload_form"):
        files = st.file_uploader(
            "Files",
            type=["pdf", "docx", "txt", "md", "xlsx", "csv", "c", "h", "cpp", "hpp", "py", "arxml", "xml"],
            accept_multiple_files=True,
        )
        columns = st.columns(3)
        doc_type = columns[0].selectbox("Document type", DOC_TYPES[module])
        version_label = columns[1].text_input("Version label", value="v1")
        approved = columns[2].checkbox(
            "Approved source", value=True,
            help="Mark only documents released through the official process.",
        )
        if st.form_submit_button("Ingest") and files:
            progress = st.progress(0.0)
            for index, file in enumerate(files, start=1):
                try:
                    result = api_client.upload(
                        "/documents/upload",
                        file,
                        data={
                            "module": module,
                            "doc_type": doc_type,
                            "version_label": version_label,
                            "approved_source": str(approved).lower(),
                        },
                        params={"project": project},
                    )
                    if result["status"] == "indexed":
                        st.success(f"{result['name']}: {result['chunk_count']} chunks indexed.")
                    else:
                        st.error(f"{result['name']}: {result['error']}")
                except Exception as exc:
                    show_error(exc)
                progress.progress(index / len(files))

with samples_tab:
    st.markdown(
        "The assistant ships with small synthetic design documents so it is "
        "demonstrable immediately. They contain no real project data."
    )
    st.markdown(
        "- A Body Control Module HLD, revision A\n"
        "- The same design at revision B, so the comparison feature has something to diff"
    )
    if st.button("Load all bundled samples into this project"):
        with st.spinner("Parsing, embedding and indexing..."):
            try:
                results = api_client.post("/documents/load-samples", params={"project": project})
            except Exception as exc:
                show_error(exc)
                results = []
        if results:
            st.success(f"Indexed {len(results)} sample documents.")
            st.dataframe(
                pd.DataFrame(results)[["name", "module", "doc_type", "chunk_count", "status"]],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Samples are already loaded in this project.")

with inventory_tab:
    try:
        documents = api_client.get("/documents", {"project": project})
    except Exception as exc:
        show_error(exc)
        documents = []

    if not documents:
        st.info("No documents indexed in this project yet.")
    else:
        frame = pd.DataFrame(documents)
        frame["module"] = frame["module"].map(lambda key: MODULES.get(key, key))
        st.dataframe(
            frame[
                ["name", "module", "doc_type", "version_label", "approved_source",
                 "chunk_count", "status", "created_at"]
            ],
            hide_index=True,
            use_container_width=True,
        )

        failed = [d for d in documents if d["status"] == "failed"]
        for document in failed:
            st.error(f"{document['name']}: {document['error']}")

        st.divider()
        names = {f"{d['name']} ({d['module']})": d["id"] for d in documents}
        choice = st.selectbox("Remove a document", list(names))
        if st.button("Delete", type="secondary"):
            try:
                api_client.delete(f"/documents/{names[choice]}", {"project": project})
                st.success("Removed from the index and from disk.")
                st.rerun()
            except Exception as exc:
                show_error(exc)
