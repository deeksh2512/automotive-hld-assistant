"""Human review queue and cross-artifact traceability."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client  # noqa: E402
from ui.common import (  # noqa: E402
    GOVERNANCE_NOTICE,
    confidence_badge,
    page_setup,
    require_project,
    review_badge,
    show_error,
)

page_setup("Review Queue and Traceability")
project = require_project()

st.info(GOVERNANCE_NOTICE)

queue_tab, all_tab, trace_tab = st.tabs(
    ["Awaiting review", "All artifacts", "Traceability matrix"]
)

MODULE_LABELS = {"hld": "HLD"}


def render_artifact(artifact: dict, index: int) -> None:
    with st.container(border=True):
        header = st.columns([4, 1, 1])
        header[0].markdown(
            f"**{artifact['ref']}** · {MODULE_LABELS.get(artifact['module'], artifact['module'])}"
            f" · {artifact['artifact_type']}"
        )
        header[0].caption(artifact["title"])
        with header[1]:
            confidence_badge(artifact["confidence"], artifact["confidence_score"])
        header[2].markdown(review_badge(artifact["review_status"]), unsafe_allow_html=True)

        st.caption(
            f"Produced by {artifact['generation_mode'].replace('_', ' ')} · "
            f"{artifact['created_by']} · {artifact['created_at']}"
        )

        edited_summary = st.text_area(
            "Content (edit before accepting if required)",
            value=artifact["summary"],
            height=140,
            key=f"summary_{artifact['id']}_{index}",
        )

        if artifact["citations"]:
            with st.expander(f"Evidence ({len(artifact['citations'])})"):
                for citation in artifact["citations"]:
                    label = citation.get("label") if isinstance(citation, dict) else str(citation)
                    st.markdown(f"- {label}")
                    if isinstance(citation, dict) and citation.get("excerpt"):
                        st.caption(citation["excerpt"][:300])
        else:
            st.caption("No citations attached. Rule-based artifacts cite their rule table instead.")

        with st.expander("Full payload"):
            st.json(artifact["payload"], expanded=False)

        comment = st.text_input("Reviewer comment", key=f"comment_{artifact['id']}_{index}")
        buttons = st.columns(4)
        actions = [
            ("Accept", "accepted", False),
            ("Accept with edits", "edited", True),
            ("Reject", "rejected", False),
        ]
        for column, (label, decision, send_edit) in zip(buttons, actions):
            if column.button(label, key=f"{decision}_{artifact['id']}_{index}"):
                body = {"decision": decision, "comment": comment}
                if send_edit:
                    body["edited_summary"] = edited_summary
                try:
                    api_client.post(
                        f"/artifacts/{artifact['id']}/review",
                        json=body,
                        params={"project": project},
                    )
                    st.success(f"{artifact['ref']} recorded as {decision}.")
                    st.rerun()
                except Exception as exc:
                    show_error(exc)

        try:
            history = api_client.get(
                f"/artifacts/{artifact['id']}/history", {"project": project}
            )
            if history:
                with st.expander(f"Review history ({len(history)})"):
                    st.dataframe(
                        pd.DataFrame(history), hide_index=True, use_container_width=True
                    )
        except Exception:
            pass


with queue_tab:
    try:
        pending = api_client.get(
            "/artifacts", {"project": project, "review_status": "pending_review"}
        )
    except Exception as exc:
        show_error(exc)
        pending = []

    if not pending:
        st.success("Nothing is awaiting review in this project.")
    else:
        modules = sorted({a["module"] for a in pending})
        selected = st.multiselect(
            "Filter by module", modules, default=modules,
            format_func=lambda key: MODULE_LABELS.get(key, key),
        )
        filtered = [a for a in pending if a["module"] in selected]
        st.caption(f"{len(filtered)} artifact(s) awaiting a decision.")
        for index, artifact in enumerate(filtered):
            render_artifact(artifact, index)

with all_tab:
    try:
        artifacts = api_client.get("/artifacts", {"project": project})
    except Exception as exc:
        show_error(exc)
        artifacts = []

    if not artifacts:
        st.info("No artifacts in this project yet.")
    else:
        frame = pd.DataFrame(artifacts)
        frame["module"] = frame["module"].map(lambda key: MODULE_LABELS.get(key, key))
        st.dataframe(
            frame[
                ["ref", "module", "artifact_type", "title", "confidence",
                 "generation_mode", "review_status", "created_by", "created_at"]
            ],
            hide_index=True,
            use_container_width=True,
        )
        status_counts = frame["review_status"].value_counts()
        st.bar_chart(status_counts)
        st.download_button(
            "Download all artifacts (JSON)",
            json.dumps(artifacts, indent=2),
            file_name=f"{project}_artifacts.json",
        )

with trace_tab:
    try:
        matrix = api_client.get("/artifacts/trace/matrix", {"project": project})
    except Exception as exc:
        show_error(exc)
        st.stop()

    columns = st.columns(3)
    columns[0].metric("Linked artifacts", matrix["artifact_count"])
    columns[1].metric("Link completeness", f"{matrix['link_completeness_percent']}%")
    columns[2].metric("Unlinked", len(matrix["unlinked"]))

    if matrix["rows"]:
        st.dataframe(
            pd.DataFrame(matrix["rows"]), hide_index=True, use_container_width=True
        )
    else:
        st.info(
            "No traceability links yet. Links are created automatically when a safety "
            "requirement is derived from a hazard, or a cybersecurity requirement from "
            "a threat."
        )

    if matrix["unlinked"]:
        st.warning("Artifacts with no traceability link:")
        st.dataframe(
            pd.DataFrame(matrix["unlinked"]), hide_index=True, use_container_width=True
        )
