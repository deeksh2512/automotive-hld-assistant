"""Human review queue and cross-artifact traceability."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st  # noqa: E402

from ui import api_client, theme  # noqa: E402
from ui.common import (  # noqa: E402
    CONFIDENCE_TONE,
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

REVIEW_CHIP_TONES = {label: REVIEW_TONE[status] for status, label in REVIEW_LABEL.items()}
CONFIDENCE_CHIP_TONES = {level.title(): tone for level, tone in CONFIDENCE_TONE.items()}

page_header(
    "Review Queue",
    kicker=project,
    chips=[
        theme.chip(f"{len(pending)} awaiting decision", "warning" if pending else "success")
    ],
)

theme.kpis(
    [
        ("Artifacts", len(artifacts), "in this workspace"),
        ("Pending", len(pending), "draft until accepted"),
        ("Approved", len(approved), "cleared for use"),
        ("Rejected", len(rejected), ""),
    ],
    tones=["", "warning" if pending else "", "success", "danger" if rejected else ""],
)

queue_tab, all_tab, trace_tab = st.tabs(["Awaiting review", "All artifacts", "Traceability"])


def artifact_row(artifact: dict) -> dict:
    return {
        "ref": artifact["ref"],
        "type": artifact["artifact_type"].replace("_", " "),
        "title": artifact["title"],
        "confidence": artifact["confidence"].title(),
        "mode": artifact["generation_mode"].replace("_", " "),
        "review": REVIEW_LABEL.get(artifact["review_status"], artifact["review_status"]),
        "author": artifact["created_by"],
        "created": (artifact["created_at"] or "")[:16].replace("T", " "),
    }


def render_decision_panel(artifact: dict) -> None:
    """Summary, evidence and the three dispositions for one artifact."""
    with st.container(border=True):
        theme.panel_bar(
            artifact["artifact_type"].replace("_", " "),
            meta=[
                theme.ref(artifact["ref"]),
                confidence_chip(artifact["confidence"], artifact["confidence_score"]),
                review_chip(artifact["review_status"]),
            ],
        )
        st.caption(
            f"{artifact['title']} · produced by "
            f"{artifact['generation_mode'].replace('_', ' ')} · {artifact['created_by']} · "
            f"{(artifact['created_at'] or '')[:16].replace('T', ' ')}"
        )

        edited_summary = st.text_area(
            "Summary — edit before accepting if it needs correction",
            value=artifact["summary"],
            height=100,
            key=f"summary_{artifact['id']}",
        )

        comment = st.text_input(
            "Reviewer comment",
            key=f"comment_{artifact['id']}",
            placeholder="What did you check, and against which source?",
        )

        buttons = st.columns([1, 1.4, 1, 4], gap="small")
        actions = [
            ("Accept", "accepted", False, "primary"),
            ("Accept with edits", "edited", True, "secondary"),
            ("Reject", "rejected", False, "secondary"),
        ]
        for column, (label, decision, send_edit, kind) in zip(buttons, actions):
            if column.button(
                label, key=f"{decision}_{artifact['id']}", type=kind, use_container_width=True
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

    details = st.columns(3, gap="small")
    with details[0]:
        citations = artifact["citations"]
        with st.expander(f"Evidence ({len(citations)})"):
            if citations:
                for citation in citations:
                    label = (
                        citation.get("label") if isinstance(citation, dict) else str(citation)
                    )
                    st.markdown(f"- {label}")
                    if isinstance(citation, dict) and citation.get("excerpt"):
                        st.caption(citation["excerpt"][:300])
            else:
                st.caption("No passage citations. Rule-based artifacts cite their rule table.")
    with details[1]:
        with st.expander("Payload"):
            st.json(artifact["payload"], expanded=False)
    with details[2]:
        try:
            history = api_client.get(
                f"/artifacts/{artifact['id']}/history", {"project": project}
            )
        except Exception:
            history = []
        with st.expander(f"Review history ({len(history)})"):
            if history:
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
            else:
                st.caption("No decisions recorded yet.")


with queue_tab:
    if not pending:
        theme.callout(
            "Every artifact in this workspace has been dispositioned.",
            title="Queue is clear.",
            tone="success",
        )
    else:
        theme.table(
            [artifact_row(a) for a in pending],
            columns=[
                {"key": "ref", "label": "Ref", "style": "mono", "width": "10%"},
                {"key": "type", "label": "Type", "style": "muted", "width": "12%"},
                {"key": "title", "label": "Title", "style": "clamp"},
                {
                    "key": "confidence",
                    "label": "Confidence",
                    "style": "chip",
                    "width": "11%",
                    "tones": CONFIDENCE_CHIP_TONES,
                },
                {"key": "mode", "label": "Produced by", "style": "muted", "width": "13%"},
                {"key": "created", "label": "Created", "style": "mono", "width": "13%"},
            ],
            max_height="18rem",
            note=f"{len(pending)} artifact(s) awaiting a decision",
        )

        labels = {f"{a['ref']} · {a['title']}": a for a in pending}
        choice = st.selectbox("Artifact to review", list(labels))
        render_decision_panel(labels[choice])

with all_tab:
    theme.table(
        [artifact_row(a) for a in artifacts],
        columns=[
            {"key": "ref", "label": "Ref", "style": "mono", "width": "10%"},
            {"key": "type", "label": "Type", "style": "muted", "width": "11%"},
            {"key": "title", "label": "Title", "style": "clamp"},
            {
                "key": "confidence",
                "label": "Confidence",
                "style": "chip",
                "width": "10%",
                "tones": CONFIDENCE_CHIP_TONES,
            },
            {"key": "mode", "label": "Produced by", "style": "muted", "width": "11%"},
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
        max_height="30rem",
        empty="No artifacts yet. Run an extraction or ask a question.",
        note=f"{len(artifacts)} artifacts",
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
        ],
        tones=["", "accent", "warning" if matrix["unlinked"] else "success"],
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
