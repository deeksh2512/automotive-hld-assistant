"""Workspace dashboard: current state of the knowledge base, queue and activity."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run ui/Home.py` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import (  # noqa: E402
    REVIEW_LABEL,
    REVIEW_TONE,
    page_header,
    page_setup,
    show_error,
    sidebar,
)

page_setup("Overview")

project = sidebar()

if project is None:
    page_header("Workspace overview", kicker="HLD Assistant")
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

try:
    activity = api_client.get("/audit", {"limit": 9})
except Exception:
    activity = []

indexed = [d for d in documents if d["status"] == "indexed"]
pending = [a for a in artifacts if a["review_status"] == "pending_review"]
approved = [a for a in artifacts if a["review_status"].startswith("approved")]
inventories = [a for a in artifacts if a["artifact_type"] == "hld_entity"]
passages = sum(d["chunk_count"] for d in documents)

page_header(
    "Workspace overview",
    kicker=project,
    chips=[
        theme.chip(f"{len(indexed)} documents", "neutral"),
        theme.chip("Model ready", "success", dot=True)
        if health["llm_available"]
        else theme.chip("Retrieval only", "warning", dot=True),
    ],
)

theme.kpis(
    [
        ("Documents", len(indexed), f"{len(documents)} ingested"),
        ("Passages", passages, "page-anchored"),
        ("Extractions", len(inventories), "architecture inventories"),
        ("Artifacts", len(artifacts), f"{len(approved)} approved"),
        ("Awaiting review", len(pending), "needs a decision" if pending else "queue clear"),
    ],
    tones=["", "", "", "", "warning" if pending else "success"],
)

if not documents:
    theme.callout(
        "No documents indexed. Load the bundled Body Control Module design to try the "
        "full workflow.",
        title="Start here.",
        tone="accent",
    )

left, right = st.columns([1.5, 1], gap="small")

with left:
    with st.container(border=True):
        theme.panel_bar(
            "Knowledge base", meta=[theme.chip(f"{passages} passages", "neutral")]
        )
        theme.table(
            [
                {
                    "name": document["name"],
                    "rev": document["version_label"],
                    "type": document["doc_type"].replace("_", " "),
                    "passages": document["chunk_count"],
                    "status": document["status"],
                }
                for document in documents
            ],
            columns=[
                {"key": "name", "label": "Document", "style": "mono"},
                {"key": "rev", "label": "Rev", "style": "mono", "width": "9%"},
                {"key": "type", "label": "Type", "style": "muted", "width": "15%"},
                {"key": "passages", "label": "Passages", "style": "num", "width": "13%"},
                {
                    "key": "status",
                    "label": "Status",
                    "style": "chip",
                    "width": "13%",
                    "tones": {"indexed": "success", "failed": "danger"},
                },
            ],
            max_height="none",
            empty="Nothing indexed in this workspace yet.",
        )
        st.page_link("pages/0_Documents.py", label="Manage documents")

    with st.container(border=True):
        theme.panel_bar("Recent activity", meta=[theme.chip("Audit log", "neutral")])
        theme.table(
            [
                {
                    "time": (entry["created_at"] or "")[:19].replace("T", " "),
                    "action": entry["action"],
                    "detail": entry["detail"],
                }
                for entry in activity
            ],
            columns=[
                {"key": "time", "label": "Timestamp", "style": "mono", "width": "19%"},
                {"key": "action", "label": "Action", "style": "strong", "width": "19%"},
                {"key": "detail", "label": "Detail", "style": "clamp"},
            ],
            max_height="none",
            empty="No activity recorded yet.",
        )
        st.page_link("pages/3_Audit_Trail.py", label="Open audit trail")

with right:
    with st.container(border=True):
        theme.panel_bar(
            "Review queue",
            meta=[theme.chip(f"{len(pending)} pending", "warning" if pending else "success")],
        )
        theme.table(
            [
                {
                    "ref": artifact["ref"],
                    "title": artifact["title"],
                    "status": REVIEW_LABEL.get(
                        artifact["review_status"], artifact["review_status"]
                    ),
                }
                for artifact in artifacts[:14]
            ],
            columns=[
                {"key": "ref", "label": "Ref", "style": "mono", "width": "22%"},
                {"key": "title", "label": "Artifact", "style": "clamp"},
                {
                    "key": "status",
                    "label": "Review",
                    "style": "chip",
                    "width": "27%",
                    "tones": {
                        label: REVIEW_TONE[status] for status, label in REVIEW_LABEL.items()
                    },
                },
            ],
            max_height="none",
            empty="No artifacts produced yet.",
        )
        st.page_link("pages/2_Review_Queue.py", label="Open review queue")
