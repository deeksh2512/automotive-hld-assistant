"""Landing page: workspace status and entry points into the analysis workflow."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run ui/Home.py` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import GOVERNANCE_NOTICE, page_header, page_setup, show_error, sidebar  # noqa: E402

page_setup("Overview")

project = sidebar()

if project is None:
    page_header(
        "AUTOSAR HLD Analysis",
        "Connect to the backend to begin.",
        kicker="Overview",
    )
    theme.empty_state(
        "Backend unavailable",
        "Start the API with <code>uvicorn app.main:app --port 8000</code>, then reload.",
    )
    st.stop()

try:
    health = api_client.get("/health")
    documents = api_client.get("/documents", {"project": project})
    artifacts = api_client.get("/artifacts", {"project": project})
except Exception as exc:
    show_error(exc)
    st.stop()

mode_chip = (
    theme.chip("Model ready", "success", dot=True)
    if health["llm_available"]
    else theme.chip("Retrieval-only", "warning", dot=True)
)

page_header(
    "AUTOSAR HLD Analysis",
    "Read High-Level Design documents with an assistant that extracts the architecture, "
    "maps dependencies, answers questions with page-level citations, and diffs revisions. "
    "Everything runs on this machine.",
    kicker="Overview",
    chips=[theme.chip(project, "accent"), mode_chip],
)

if not health["llm_available"]:
    theme.callout(
        "Extraction, the dependency map, consistency checks, revision comparison, search "
        "and export all work without a model. Questions return the retrieved passages "
        "instead of generated prose. "
        f"<br><span style='color:#94A3B8'>{health['llm_detail']}</span>",
        title="Running in retrieval-only mode.",
        tone="warning",
    )

pending = [a for a in artifacts if a["review_status"] == "pending_review"]
approved = [a for a in artifacts if a["review_status"].startswith("approved")]
chunks = sum(d["chunk_count"] for d in documents)

theme.stats([
    ("Documents", len(documents), "indexed in this workspace"),
    ("Passages", chunks, "searchable, each page-anchored"),
    ("Artifacts", len(artifacts), f"{len(approved)} approved"),
    ("Awaiting review", len(pending), "require a decision" if pending else "queue is clear"),
])

st.markdown("")

if not documents:
    theme.callout(
        "This workspace has no indexed documents yet. Load the bundled Body Control Module "
        "design from the Documents page to try the full workflow in under a minute.",
        title="Start here.",
        tone="accent",
    )
    st.page_link("pages/0_Documents.py", label="Go to Documents")
    st.markdown("")

theme.section(
    "Capabilities",
    "Deterministic extraction rules produce the inventory and findings; the model only "
    "explains and answers.",
)

CAPABILITIES = [
    ("Architecture extraction",
     "Inventories software components, BSW modules, ports, interfaces, signals, runnables "
     "and PDUs, each traced to the page and section it came from."),
    ("Dependency map",
     "Renders the communication and dependency graph so the structure of a large design "
     "is visible at a glance."),
    ("Cited question answering",
     "Plain-language questions answered with markers that resolve to a specific page of a "
     "specific document. Invented citations are stripped and reported."),
    ("Consistency checks",
     "Flags isolated components, undefined endpoints, naming inconsistencies and elements "
     "that appear only once."),
    ("Revision comparison",
     "Diffs two revisions and reports exactly which elements and dependencies were added, "
     "removed or changed."),
    ("Traceable export",
     "Inventories leave as CSV or JSON, carrying their citations and review state with them."),
]

for row in range(0, len(CAPABILITIES), 3):
    columns = st.columns(3, gap="medium")
    for column, (title, description) in zip(columns, CAPABILITIES[row:row + 3]):
        with column:
            theme.card(title, description)

st.page_link("pages/1_HLD_Analysis.py", label="Open HLD Analysis")

st.divider()

left, right = st.columns([1, 1], gap="large")
with left:
    theme.section("How a session runs")
    st.markdown(
        "1. **Index** an approved design document, or load the bundled sample.\n"
        "2. **Extract** the architecture inventory and review the dependency map.\n"
        "3. **Ask** questions and check every answer against its cited passages.\n"
        "4. **Compare** revisions when a new issue of the design arrives.\n"
        "5. **Decide** on each artifact in the Review Queue before it is used anywhere."
    )
with right:
    theme.section("Governance")
    theme.callout(GOVERNANCE_NOTICE, tone="accent")
    st.markdown(
        "Every ingestion, query, generated artifact and review decision is written to the "
        "audit log with the user, action and target. Nothing is sent off this machine."
    )
