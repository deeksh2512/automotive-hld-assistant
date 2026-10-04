"""Audit trail of every ingestion, query and review decision."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import page_header, page_setup, require_project, show_error  # noqa: E402

page_setup("Audit Trail")
project = require_project()

page_header(
    "Audit Trail",
    kicker="Governance",
    chips=[theme.chip(project, "accent")],
)

filters = st.columns([1.2, 2, 2], gap="small")
limit = filters[0].slider("Entries to load", 50, 1000, 200, step=50)

try:
    entries = api_client.get("/audit", {"limit": limit})
except Exception as exc:
    show_error(exc)
    st.stop()

if not entries:
    theme.empty_state(
        "No audit entries yet",
        "Index a document or ask a question, and the record will start here.",
    )
    st.stop()

frame = pd.DataFrame(entries)
actions = sorted(frame["action"].unique())
actors = sorted(frame["actor"].unique())
selected_actions = filters[1].multiselect("Action", actions, default=actions)
selected_actors = filters[2].multiselect("Actor", actors, default=actors)

filtered = frame[
    frame["action"].isin(selected_actions) & frame["actor"].isin(selected_actors)
]

theme.kpis(
    [
        ("Entries shown", len(filtered), f"of {len(frame)} loaded"),
        ("Queries", int(filtered["action"].str.contains("query").sum()), ""),
        ("Reviews", int(filtered["action"].str.contains("reviewed").sum()), ""),
        ("Ingestions", int(filtered["action"].str.contains("ingest").sum()), ""),
    ]
)

theme.table(
    [
        {
            "created_at": (row["created_at"] or "")[:19].replace("T", " "),
            "action": row["action"].replace("_", " "),
            "actor": row["actor"],
            "detail": row["detail"],
        }
        for row in filtered.to_dict("records")
    ],
    columns=[
        {"key": "created_at", "label": "Timestamp", "style": "mono", "width": "13%"},
        {"key": "action", "label": "Action", "style": "strong", "width": "14%"},
        {"key": "actor", "label": "Actor", "style": "muted", "width": "10%"},
        {"key": "detail", "label": "Detail", "style": "clamp"},
    ],
    max_height="30rem",
    empty="No entries match the current filter.",
)
theme.table_note(f"{len(filtered)} of {len(frame)} entries")

footer = st.columns([1, 2, 3], gap="small")
footer[0].download_button(
    "Download CSV",
    filtered.to_csv(index=False).encode(),
    file_name=f"{project}_audit_log.csv",
    use_container_width=True,
)

with st.expander("Action breakdown"):
    st.bar_chart(filtered["action"].value_counts(), color="#2563EB")
