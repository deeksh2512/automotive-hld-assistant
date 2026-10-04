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
    "Every ingestion, query, generated artifact and review decision is recorded with its "
    "actor and target. This is the evidence an assessor asks for.",
    kicker="Governance",
)

with st.expander("Filters", expanded=True):
    limit = st.slider("Entries to load", 50, 1000, 200, step=50)

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

columns = st.columns(2, gap="medium")
actions = sorted(frame["action"].unique())
selected_actions = columns[0].multiselect("Action", actions, default=actions)
actors = sorted(frame["actor"].unique())
selected_actors = columns[1].multiselect("Actor", actors, default=actors)

filtered = frame[
    frame["action"].isin(selected_actions) & frame["actor"].isin(selected_actors)
]

theme.stats([
    ("Entries shown", len(filtered), f"of {len(frame)} loaded"),
    ("Queries", int(filtered["action"].str.contains("query").sum()), ""),
    ("Reviews", int(filtered["action"].str.contains("reviewed").sum()), ""),
    ("Ingestions", int(filtered["action"].str.contains("ingest").sum()), ""),
])

st.markdown("")
st.dataframe(
    filtered[["created_at", "action", "actor", "detail"]],
    hide_index=True,
    use_container_width=True,
    height=480,
    column_config={
        "created_at": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm:ss"),
        "action": st.column_config.TextColumn("Action"),
        "actor": st.column_config.TextColumn("Actor"),
        "detail": st.column_config.TextColumn("Detail", width="large"),
    },
)

footer = st.columns([1, 3])
footer[0].download_button(
    "Download CSV",
    filtered.to_csv(index=False).encode(),
    file_name=f"{project}_audit_log.csv",
    use_container_width=True,
)

with st.expander("Action breakdown"):
    st.bar_chart(filtered["action"].value_counts(), color="#1D4ED8")
