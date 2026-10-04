"""Streamlit entry point for the AUTOSAR HLD Analysis Assistant."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run ui/Home.py` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from ui import api_client  # noqa: E402
from ui.common import GOVERNANCE_NOTICE, page_setup, show_error, sidebar  # noqa: E402

page_setup("AUTOSAR HLD Analysis Assistant")

project = sidebar()

st.markdown(
    "An AI-assisted reader for AUTOSAR High-Level Design documents, running entirely "
    "on this machine. Every output is grounded in your approved documents, carries "
    "citations and a confidence indicator, and waits for a human decision."
)

if project is None:
    st.stop()

try:
    health = api_client.get("/health")
except Exception as exc:
    show_error(exc)
    st.stop()

if not health["llm_available"]:
    st.warning(
        "**Retrieval-only mode.** " + health["llm_detail"] + "\n\n"
        "Entity extraction, the dependency map, consistency checks, revision "
        "comparison and export all work without a model. Only narrative summaries "
        "and generated answer prose are disabled; search still returns cited passages."
    )

columns = st.columns(4)
try:
    documents = api_client.get("/documents", {"project": project})
    artifacts = api_client.get("/artifacts", {"project": project})
except Exception as exc:
    show_error(exc)
    st.stop()

pending = [a for a in artifacts if a["review_status"] == "pending_review"]
columns[0].metric("Indexed documents", len(documents))
columns[1].metric("Engineering artifacts", len(artifacts))
columns[2].metric("Awaiting review", len(pending))
columns[3].metric("Chunks indexed", sum(d["chunk_count"] for d in documents))

st.divider()

st.subheader("What it does")
features = [
    ("Architecture extraction",
     "Builds an inventory of software components, BSW modules, ports, interfaces, "
     "signals, runnables and PDUs, each one traced back to the page it came from."),
    ("Dependency map",
     "Renders the communication and dependency graph between components so the "
     "structure of a large design is visible at a glance."),
    ("Cited question answering",
     "Ask a question in plain language and get an answer where every claim points "
     "at a specific page of a specific document."),
    ("Consistency checks",
     "Flags isolated components, undefined endpoints, naming inconsistencies and "
     "elements mentioned only once."),
    ("Revision comparison",
     "Diffs two revisions of a design and reports exactly which elements and "
     "dependencies were added, removed or changed."),
]
for title, description in features:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(description)
st.page_link("pages/1_HLD_Analysis.py", label="Open HLD Analysis", icon=":material/arrow_forward:")

st.divider()

left, right = st.columns(2)
with left:
    st.subheader("Getting started")
    st.markdown(
        "1. Load the bundled synthetic design from the Documents page, or upload "
        "your own approved material.\n"
        "2. Open HLD Analysis and extract the architecture inventory.\n"
        "3. Review every artifact in the Review Queue before using it.\n"
        "4. Check the Audit Trail for a complete record of queries and decisions."
    )
with right:
    st.subheader("Governance")
    st.info(GOVERNANCE_NOTICE)
    st.caption(
        "Entity extraction and consistency findings come from deterministic rules, "
        "never from the language model. The model only explains and drafts."
    )
