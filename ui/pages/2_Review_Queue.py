"""Human review queue and cross-artifact traceability."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import (  # noqa: E402
    REVIEW_LABEL,
    REVIEW_TONE,
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
approved = [a for a in artifacts if a["review_status"].startswith("approved")]
rejected = [a for a in artifacts if a["review_status"] == "rejected"]

page_header(
    "Review Queue",
    kicker="Governance",
    chips=[
        theme.chip(project, "accent"),
        theme.chip(
            f"{len(pending)} awaiting decision", "warning" if pending else "success"
        ),
    ],
)

theme.kpis(
    [
        ("Artifacts", len(artifacts), "in this workspace"),
        ("Pending", len(pending), "draft until accepted"),
        ("Approved", len(approved), "cleared for use"),
        ("Rejected", len(rejected), ""),
    ],
    tones=["", "warning" if pending else "", "", ""],
)

queue_tab, all_tab, trace_tab = st.tabs(["Awaiting review", "All artifacts", "Traceability"])

REVIEW_CHIP_TONES = {label: REVIEW_TONE[status] for status, label in REVIEW_LABEL.items()}


def render_artifact(artifact: dict, index: int) -> None:
    with st.container(border=True):
        theme.panel_bar(
            artifact["title"],
            meta=[
                confidence_chip(artifact["confidence"], artifact["confidence_score"]),
                review_chip(artifact["review_status"]),
            ],
        )
        st.markdown(
            f"{theme.ref(artifact['ref'])}"
            f"<span style='font-size:.72rem;color:#94A3B8;margin-left:.4rem'>"
            f"{theme.esc(artifact['artifact_type'].replace('_', ' '))} · "
            f"{theme.esc(artifact['generation_mode'].replace('_', ' '))} · "
            f"{theme.esc(artifact['created_by'])} · "
            f"{(artifact['created_at'] or '')[:16].replace('T', ' ')}</span>",
            unsafe_allow_html=True,
        )

        edited_summary = st.text_area(
            "Summary — edit before accepting if it needs correction",
            value=artifact["summary"],
            height=110,
            key=f"summary_{artifact['id']}_{index}",
        )

        detail_columns = st.columns(2, gap="small")
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
                st.caption("No passage citations. Rule-based artifacts cite their rule table.")
        with detail_columns[1]:
            with st.expander("Full payload"):
                st.json(artifact["payload"], expanded=False)

        comment = st.text_input(
            "Reviewer comment",
            key=f"comment_{artifact['id']}_{index}",
            placeholder="What did you check, and against which source?",
        )
        buttons = st.columns([1, 1.3, 1, 4], gap="small")
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
                    theme.table(
                        history,
                        [
                            {
                                "key": name,
                                "label": name.replace("_", " ").title(),
                                "style": "clamp",
                            }
                            for name in history[0]
                        ],
                        max_height="14rem",
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
        for index, artifact in enumerate(pending):
            render_artifact(artifact, index)

with all_tab:
    theme.table(
        [
            {
                "ref": artifact["ref"],
                "type": artifact["artifact_type"].replace("_", " "),
                "title": artifact["title"],
                "confidence": artifact["confidence"].title(),
                "mode": artifact["generation_mode"].replace("_", " "),
                "review": REVIEW_LABEL.get(
                    artifact["review_status"], artifact["review_status"]
                ),
                "author": artifact["created_by"],
                "created": (artifact["created_at"] or "")[:16].replace("T", " "),
            }
            for artifact in artifacts
        ],
        columns=[
            {"key": "ref", "label": "Ref", "style": "mono", "width": "11%"},
            {"key": "type", "label": "Type", "style": "muted", "width": "12%"},
            {"key": "title", "label": "Title", "style": "clamp"},
            {
                "key": "confidence",
                "label": "Confidence",
                "style": "chip",
                "width": "10%",
                "tones": {"High": "success", "Medium": "warning", "Low": "danger"},
            },
            {"key": "mode", "label": "Produced by", "style": "muted", "width": "12%"},
            {
                "key": "review",
                "label": "Review",
                "style": "chip",
                "width": "13%",
                "tones": REVIEW_CHIP_TONES,
            },
            {"key": "author", "label": "Author", "style": "muted", "width": "9%"},
            {"key": "created", "label": "Created", "style": "mono", "width": "12%"},
        ],
        max_height="27rem",
        empty="No artifacts yet. Run an extraction or ask a question.",
    )
    if artifacts:
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

    theme.kpis(
        [
            ("Linked artifacts", matrix["artifact_count"], ""),
            ("Link completeness", f"{matrix['link_completeness_percent']}%", ""),
            ("Unlinked", len(matrix["unlinked"]), "no upstream or downstream link"),
        ]
    )

    rows = matrix["rows"]
    if rows:
        theme.table(
            rows,
            [
                {"key": name, "label": name.replace("_", " ").title(), "style": "clamp"}
                for name in rows[0]
            ],
            max_height="22rem",
        )
    else:
        theme.empty_state(
            "No traceability links yet",
            "Links are created automatically when one artifact is derived from another.",
        )

    if matrix["unlinked"]:
        theme.section("Unlinked artifacts", "No traceability relationship recorded.")
        theme.table(
            matrix["unlinked"],
            [
                {"key": name, "label": name.replace("_", " ").title(), "style": "clamp"}
                for name in matrix["unlinked"][0]
            ],
            max_height="18rem",
        )
