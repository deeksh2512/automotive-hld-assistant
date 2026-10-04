"""Audit trail of every query, ingestion and review decision."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client  # noqa: E402
from ui.common import page_setup, require_project, show_error  # noqa: E402

page_setup("Audit Trail")
project = require_project()

st.caption(
    "Every ingestion, query, generated artifact and review decision is recorded. "
    "This is the evidence an assessor asks for."
)

limit = st.slider("Entries to load", 50, 1000, 200, step=50)

try:
    entries = api_client.get("/audit", {"limit": limit})
except Exception as exc:
    show_error(exc)
    st.stop()

if not entries:
    st.info("No audit entries recorded yet.")
    st.stop()

frame = pd.DataFrame(entries)

columns = st.columns(3)
actions = sorted(frame["action"].unique())
selected_actions = columns[0].multiselect("Action", actions, default=actions)
actors = sorted(frame["actor"].unique())
selected_actors = columns[1].multiselect("Actor", actors, default=actors)
modules = sorted(m for m in frame["module"].unique() if m)
selected_modules = columns[2].multiselect("Module", modules, default=modules)

filtered = frame[
    frame["action"].isin(selected_actions)
    & frame["actor"].isin(selected_actors)
    & (frame["module"].isin(selected_modules) | (frame["module"] == ""))
]

metrics = st.columns(4)
metrics[0].metric("Entries shown", len(filtered))
metrics[1].metric("Queries", int((filtered["action"].str.contains("query")).sum()))
metrics[2].metric("Reviews", int((filtered["action"].str.contains("reviewed")).sum()))
metrics[3].metric("Ingestions", int((filtered["action"].str.contains("ingest")).sum()))

st.dataframe(
    filtered[["created_at", "action", "actor", "module", "detail"]],
    hide_index=True,
    use_container_width=True,
    height=520,
)

st.download_button(
    "Download audit log (CSV)",
    filtered.to_csv(index=False).encode(),
    file_name=f"{project}_audit_log.csv",
)

with st.expander("Action breakdown"):
    st.bar_chart(filtered["action"].value_counts())
