"""Application shell: page setup, sidebar, and the shared result components."""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError

from app.config import settings
from ui import api_client, theme
from ui.api_client import ApiError

APP_NAME = "HLD Assistant"
APP_SUBTITLE = "AUTOSAR architecture"

# Shown as the sidebar footer tooltip: the policy the review queue exists to enforce.
GOVERNANCE_NOTICE = (
    "AI-assisted output must be traceable to approved source material and reviewed by an "
    "authorised engineering specialist before it is used for compliance, design approval, "
    "software release or vehicle validation."
)

CONFIDENCE_TONE = {"high": "success", "medium": "warning", "low": "danger"}
REVIEW_TONE = {
    "pending_review": "warning",
    "approved": "success",
    "approved_with_edits": "success",
    "rejected": "danger",
}
REVIEW_LABEL = {
    "pending_review": "Pending review",
    "approved": "Approved",
    "approved_with_edits": "Approved with edits",
    "rejected": "Rejected",
}
MODE_LABEL = {
    "generated": "Model generated",
    "retrieval_only": "Retrieval only",
    "rule_based": "Rule based",
}

# Paths are resolved against the entrypoint directory. Material icons are
# deliberately omitted: Streamlit fetches that font remotely and it would show
# as raw text on a machine with no internet access.
NAVIGATION = [
    ("Overview", "Home.py"),
    ("Documents", "pages/0_Documents.py"),
    ("HLD Analysis", "pages/1_HLD_Analysis.py"),
    ("Review Queue", "pages/2_Review_Queue.py"),
    ("Audit Trail", "pages/3_Audit_Trail.py"),
]


def page_setup(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} · {APP_NAME}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    theme.inject()


def page_header(title: str, subtitle: str = "", kicker: str = "", chips=()) -> None:
    theme.page_header(title, subtitle, kicker, chips)


def _health() -> dict[str, Any] | None:
    try:
        return api_client.get("/health")
    except Exception:
        return None


def sidebar() -> str | None:
    """Render the workspace panel. Returns the selected project key."""
    with st.sidebar:
        theme.brand(APP_NAME, APP_SUBTITLE)

        theme.sidebar_label("Workflow")
        for label, path in NAVIGATION:
            try:
                st.page_link(path, label=label)
            except StreamlitPageNotFoundError:
                # Sibling pages only resolve when Home.py is the entrypoint, which
                # is not the case if someone runs a page file on its own.
                break

        st.divider()

        health = _health()
        if health is None:
            theme.callout(
                f"Cannot reach the backend at <code>{settings.api_base_url}</code>. "
                "Start it with <code>uvicorn app.main:app --port 8000</code>.",
                title="Offline.",
                tone="danger",
            )
            return None

        try:
            projects = api_client.get("/projects")
        except ApiError as exc:
            st.error(str(exc))
            return None

        keys = [project["key"] for project in projects]
        if not keys:
            st.caption("No project workspaces exist yet.")
        else:
            current = st.session_state.get("project")
            index = keys.index(current) if current in keys else 0
            st.selectbox("Workspace", keys, index=index, key="project")

        with st.expander("Create a workspace"):
            with st.form("new_project", clear_on_submit=True):
                key = st.text_input("Key", placeholder="x200-bcm")
                name = st.text_input("Name", placeholder="X200 Body Control Module")
                classification = st.selectbox(
                    "Classification", ["internal", "confidential", "strictly confidential"]
                )
                if st.form_submit_button("Create") and key and name:
                    try:
                        api_client.post(
                            "/projects",
                            json={"key": key, "name": name, "classification": classification},
                        )
                        st.session_state["project"] = key
                        st.rerun()
                    except ApiError as exc:
                        st.error(str(exc))

        st.session_state.setdefault("user", settings.default_user)
        st.text_input(
            "Identity", key="user",
            help="Sent as the X-User header. Access is checked against your project role.",
        )

        project = st.session_state.get("project")
        role = ""
        if project:
            try:
                members = api_client.get("/projects/members", {"project": project})
                role = members["your_role"]
            except ApiError:
                pass

        st.divider()
        engine = (
            theme.chip(health["llm_model"], "success", dot=True)
            if health["llm_available"]
            else theme.chip("Retrieval only", "warning", dot=True)
        )
        badges = [engine]
        if role:
            badges.append(theme.chip(role, "neutral"))
        st.markdown(
            '<div class="side-label">Engine</div>'
            f'<div class="chiprow">{"".join(badges)}</div>'
            f'<div class="side-foot">Embeddings '
            f"{theme.esc(health['embedding_model'].split('/')[-1])}<br>"
            f'<span title="{theme.esc(GOVERNANCE_NOTICE)}">'
            "Local processing · review required before use</span></div>",
            unsafe_allow_html=True,
        )
        return project


def require_project() -> str:
    project = sidebar()
    if not project:
        theme.empty_state(
            "No workspace selected",
            "Choose a project in the sidebar, or create one, to continue.",
        )
        st.stop()
    return project


def confidence_chip(confidence: str, score: float | None = None) -> str:
    tone = CONFIDENCE_TONE.get(confidence, "neutral")
    label = f"{confidence.title()} confidence"
    if score is not None:
        label += f" · {score:.2f}"
    return theme.chip(label, tone, dot=True)


def review_chip(status: str) -> str:
    return theme.chip(REVIEW_LABEL.get(status, status), REVIEW_TONE.get(status, "neutral"))


# Retained so older call sites keep working.
review_badge = review_chip


def confidence_badge(confidence: str, score: float | None = None) -> None:
    st.markdown(confidence_chip(confidence, score), unsafe_allow_html=True)


def render_answer(result: dict) -> None:
    """Answer, provenance, warnings and every supporting citation."""
    mode = result.get("mode", "")
    chips = [
        confidence_chip(result.get("confidence", "low"), result.get("confidence_score")),
        theme.chip(MODE_LABEL.get(mode, mode or "Unknown"), "neutral"),
    ]
    body = html.escape(result.get("answer", "")).replace("\n", "<br>")
    # Make the inline evidence markers scannable against the prose.
    body = re.sub(r"\[S\d{1,2}\]", r'<span class="ref-mark">\g<0></span>', body)
    st.markdown(
        f'<div class="answer"><div class="answer-head">'
        f'<span class="answer-label">Answer</span>'
        f'<span class="answer-meta">{"".join(chips)}</span></div>'
        f'<div class="answer-body">{body}</div></div>',
        unsafe_allow_html=True,
    )

    for warning in result.get("warnings", []):
        theme.callout(html.escape(warning), tone="warning")

    citations = result.get("citations") or result.get("sources") or []
    if not citations:
        theme.callout(
            "No source citations were produced for this response, so it is not grounded "
            "in the indexed documents.",
            tone="danger",
        )
        return

    st.markdown("")
    theme.section("Evidence", f"{len(citations)} passage(s) retrieved from indexed documents")
    for citation in citations:
        marker = html.escape(str(citation.get("marker", "")))
        label = html.escape(str(citation.get("label", "")))
        score = citation.get("score", 0) or 0
        # Excerpts keep the source line breaks, but runs of blank lines would
        # stretch the card out of proportion to the text it holds.
        lines = [line.rstrip() for line in str(citation.get("excerpt", "")).splitlines()]
        excerpt = html.escape("\n".join(line for line in lines if line).strip())
        marker_html = f'<span class="evidence-marker">{marker}</span>' if marker else ""
        st.markdown(
            f'<div class="evidence"><div class="evidence-head">{marker_html}'
            f'<span class="evidence-source">{label}</span>'
            f'<span class="evidence-score">relevance {score:.2f}</span></div>'
            f'<div class="evidence-text">{excerpt}</div></div>',
            unsafe_allow_html=True,
        )


def render_review_controls(artifact_id: str, project: str, key_prefix: str) -> None:
    """The human disposition control required before output may be used."""
    with st.expander("Record a review decision"):
        comment = st.text_area(
            "Reviewer comment", key=f"{key_prefix}_comment",
            placeholder="What did you check, and against which source?",
        )
        columns = st.columns([1, 1, 1, 3])
        decisions = [
            ("Accept", "accepted", "primary"),
            ("Accept with edits", "edited", "secondary"),
            ("Reject", "rejected", "secondary"),
        ]
        for column, (label, decision, kind) in zip(columns, decisions):
            if column.button(label, key=f"{key_prefix}_{decision}", type=kind):
                try:
                    api_client.post(
                        f"/artifacts/{artifact_id}/review",
                        json={"decision": decision, "comment": comment},
                        params={"project": project},
                    )
                    st.success(f"Recorded as {decision}.")
                except ApiError as exc:
                    st.error(str(exc))


def show_error(exc: Exception) -> None:
    if isinstance(exc, ApiError):
        if exc.status_code == 403:
            theme.callout(html.escape(str(exc.detail)), title="Not permitted.", tone="danger")
        elif exc.status_code == 503:
            theme.callout(html.escape(str(exc.detail)), title="Model unavailable.", tone="warning")
        else:
            theme.callout(
                html.escape(str(exc.detail)), title=f"Request failed ({exc.status_code}).",
                tone="danger",
            )
    else:
        theme.callout(html.escape(str(exc)), title="Error.", tone="danger")


def document_selector(
    project: str,
    module: str,
    label: str = "Document",
    key: str | None = None,
    default_index: int = 0,
) -> dict | None:
    try:
        documents = [
            document
            for document in api_client.get("/documents", {"project": project, "module": module})
            if document["status"] == "indexed"
        ]
    except ApiError as exc:
        show_error(exc)
        return None
    if not documents:
        theme.empty_state(
            "No indexed documents",
            "Upload a design document on the Documents page, or load the bundled samples.",
        )
        return None
    names = [f"{d['name']}  ·  {d['version_label']}  ·  {d['chunk_count']} chunks" for d in documents]
    choice = st.selectbox(
        label,
        range(len(documents)),
        index=min(default_index, len(documents) - 1),
        format_func=lambda i: names[i],
        key=key,
    )
    return documents[choice]
