"""Human review queue and cross-artifact traceability."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import (  # noqa: E402
    GOVERNANCE_NOTICE,
    confidence_chip,
    page_header,
    page_setup,
    require_project,
    review_chip,
    show_error,
)

page_setup("Review Queue")
project = require_project()

try:
    artifacts = api_client.get("/artifacts", {"project": project})
except Exception as exc:
    show_error(exc)
    artifacts = []

pending = [a for a in artifacts if a["review_status"] == "pending_review"]

page_header(
    "Review Queue",
    "Generated output is a draft until a qualified engineer accepts it. Decisions are "
    "recorded against the artifact and written to the audit log.",
    kicker="Governance",
    chips=[
        theme.chip(f"{len(pending)} awaiting decision", "warning" if pending else "success"),
    ],
)

theme.callout(GOVERNANCE_NOTICE, tone="accent")

queue_tab, all_tab, trace_tab = st.tabs(
    ["Awaiting review", "All artifacts", "Traceability"]
)


def render_artifact(artifact: dict, index: int) -> None:
    with st.container(border=True):
        theme.card_marker()
        header = st.columns([4, 1.3, 1.2])
        header[0].markdown(
            f"{theme.ref(artifact['ref'])} &nbsp; **{artifact['title']}**",
            unsafe_allow_html=True,
        )
        header[0].caption(
            f"{artifact['artifact_type'].replace('_', ' ')} · produced by "
            f"{artifact['generation_mode'].replace('_', ' ')} · {artifact['created_by']} · "
            f"{(artifact['created_at'] or '')[:16].replace('T', ' ')}"
        )
        header[1].markdown(
            confidence_chip(artifact["confidence"], artifact["confidence_score"]),
            unsafe_allow_html=True,
        )
        header[2].markdown(review_chip(artifact["review_status"]), unsafe_allow_html=True)

        edited_summary = st.text_area(
            "Summary — edit before accepting if it needs correction",
            value=artifact["summary"],
            height=130,
            key=f"summary_{artifact['id']}_{index}",
        )

        detail_columns = st.columns(2)
        with detail_columns[0]:
            if artifact["citations"]:
                with st.expander(f"Evidence ({len(artifact['citations'])})"):
                    for citation in artifact["citations"]:
                        label = (
                            citation.get("label")
                            if isinstance(citation, dict)
                            else str(citation)
                        )
                        st.markdown(f"- {label}")
                        if isinstance(citation, dict) and citation.get("excerpt"):
                            st.caption(citation["excerpt"][:300])
            else:
                st.caption(
                    "No passage citations. Rule-based artifacts reference their rule table "
                    "instead."
                )
        with detail_columns[1]:
            with st.expander("Full payload"):
                st.json(artifact["payload"], expanded=False)

        comment = st.text_input(
            "Reviewer comment",
            key=f"comment_{artifact['id']}_{index}",
            placeholder="What did you check, and against which source?",
        )
        buttons = st.columns([1, 1.3, 1, 3])
        actions = [
            ("Accept", "accepted", False, "primary"),
            ("Accept with edits", "edited", True, "secondary"),
            ("Reject", "rejected", False, "secondary"),
        ]
        for column, (label, decision, send_edit, kind) in zip(buttons, actions):
            if column.button(
                label, key=f"{decision}_{artifact['id']}_{index}",
                type=kind, use_container_width=True,
            ):
                body = {"decision": decision, "comment": comment}
                if send_edit:
                    body["edited_summary"] = edited_summary
                try:
                    api_client.post(
                        f"/artifacts/{artifact['id']}/review",
                        json=body,
                        params={"project": project},
                    )
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
    if not pending:
        theme.callout(
            "Every artifact in this workspace has been dispositioned.",
            title="Queue is clear.",
            tone="success",
        )
    else:
        st.caption(f"{len(pending)} artifact(s) awaiting a decision.")
        for index, artifact in enumerate(pending):
            render_artifact(artifact, index)

with all_tab:
    if not artifacts:
        theme.empty_state(
            "No artifacts yet",
            "Run an extraction or ask a question to produce reviewable output.",
        )
    else:
        frame = pd.DataFrame(artifacts)
        st.dataframe(
            frame[["ref", "artifact_type", "title", "confidence",
                   "generation_mode", "review_status", "created_by", "created_at"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "ref": st.column_config.TextColumn("Ref"),
                "artifact_type": st.column_config.TextColumn("Type"),
                "title": st.column_config.TextColumn("Title", width="large"),
                "confidence": st.column_config.TextColumn("Confidence"),
                "generation_mode": st.column_config.TextColumn("Produced by"),
                "review_status": st.column_config.TextColumn("Review"),
                "created_by": st.column_config.TextColumn("Author"),
                "created_at": st.column_config.DatetimeColumn(
                    "Created", format="YYYY-MM-DD HH:mm"
                ),
            },
        )
        counts = frame["review_status"].value_counts()
        theme.stats([
            (status.replace("_", " ").title(), int(count), "")
            for status, count in counts.items()
        ])
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

    theme.stats([
        ("Linked artifacts", matrix["artifact_count"], ""),
        ("Link completeness", f"{matrix['link_completeness_percent']}%", ""),
        ("Unlinked", len(matrix["unlinked"]), "no upstream or downstream link"),
    ])

    st.markdown("")
    if matrix["rows"]:
        st.dataframe(pd.DataFrame(matrix["rows"]), hide_index=True, use_container_width=True)
    else:
        theme.empty_state(
            "No traceability links yet",
            "Links are created automatically when one artifact is derived from another.",
        )

    if matrix["unlinked"]:
        st.markdown("")
        theme.section("Unlinked artifacts", "These have no traceability relationship recorded.")
        st.dataframe(
            pd.DataFrame(matrix["unlinked"]), hide_index=True, use_container_width=True
        )
