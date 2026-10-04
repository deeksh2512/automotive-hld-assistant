"""Shared Streamlit widgets: sidebar, model status, citation and confidence display."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.config import settings
from ui import api_client
from ui.api_client import ApiError

CONFIDENCE_BADGE = {
    "high": ("High confidence", "#1b7f3b"),
    "medium": ("Medium confidence", "#b06a00"),
    "low": ("Low confidence", "#b02a2a"),
}

REVIEW_BADGE = {
    "pending_review": ("Pending review", "#b06a00"),
    "approved": ("Approved", "#1b7f3b"),
    "approved_with_edits": ("Approved with edits", "#1b7f3b"),
    "rejected": ("Rejected", "#b02a2a"),
}

GOVERNANCE_NOTICE = (
    "AI-assisted output must be traceable to approved source material and reviewed by an "
    "authorised engineering specialist before it is used for compliance, design approval, "
    "software release or vehicle validation."
)


def page_setup(title: str, icon: str = "") -> None:
    st.set_page_config(page_title=f"{title} | AUTOSAR HLD Assistant", layout="wide")
    st.title(title)


def _health() -> dict[str, Any] | None:
    try:
        return api_client.get("/health")
    except Exception:
        return None


def sidebar() -> str | None:
    """Render the workspace selector and status panel. Returns the project key."""
    with st.sidebar:
        st.markdown("### AUTOSAR HLD Assistant")

        st.session_state.setdefault("user", settings.default_user)
        st.text_input("Signed in as", key="user", help="Pilot identity header (X-User).")

        health = _health()
        if health is None:
            st.error(
                f"Backend not reachable at {settings.api_base_url}. "
                "Start it with: uvicorn app.main:app --port 8000"
            )
            return None

        if health["llm_available"]:
            st.success(f"Model ready: {health['llm_model']}")
        else:
            st.warning("Retrieval-only mode")
            st.caption(health["llm_detail"])

        st.caption(f"Embeddings: {health['embedding_model']}")

        st.divider()
        try:
            projects = api_client.get("/projects")
        except ApiError as exc:
            st.error(str(exc))
            return None

        keys = [project["key"] for project in projects]
        if not keys:
            st.info("No project workspaces exist yet.")
        else:
            current = st.session_state.get("project")
            index = keys.index(current) if current in keys else 0
            st.selectbox("Project workspace", keys, index=index, key="project")

        with st.expander("New project"):
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

        project = st.session_state.get("project")
        if project:
            try:
                members = api_client.get("/projects/members", {"project": project})
                st.caption(f"Your role in this project: {members['your_role']}")
            except ApiError:
                pass

        st.divider()
        st.caption(GOVERNANCE_NOTICE)
        return project


def require_project() -> str:
    project = sidebar()
    if not project:
        st.info("Select or create a project workspace in the sidebar to continue.")
        st.stop()
    return project


def badge(label: str, colour: str) -> str:
    return (
        f"<span style='background:{colour};color:white;padding:2px 8px;"
        f"border-radius:10px;font-size:0.78rem;white-space:nowrap'>{label}</span>"
    )


def confidence_badge(confidence: str, score: float | None = None) -> None:
    label, colour = CONFIDENCE_BADGE.get(confidence, ("Unknown", "#666"))
    text = f"{label}{f' ({score:.2f})' if score is not None else ''}"
    st.markdown(badge(text, colour), unsafe_allow_html=True)


def review_badge(status: str) -> str:
    label, colour = REVIEW_BADGE.get(status, (status, "#666"))
    return badge(label, colour)


def render_answer(result: dict) -> None:
    """Standard presentation: answer, confidence, warnings, then every citation."""
    columns = st.columns([3, 1])
    with columns[1]:
        confidence_badge(result.get("confidence", "low"), result.get("confidence_score"))
        mode = result.get("mode", "")
        st.caption(
            "Generated by the local model"
            if mode == "generated"
            else "Retrieval only, no model output"
            if mode == "retrieval_only"
            else "Rule-based"
        )
    with columns[0]:
        st.markdown(result.get("answer", ""))

    for warning in result.get("warnings", []):
        st.warning(warning)

    citations = result.get("citations") or result.get("sources") or []
    if citations:
        st.markdown("**Evidence**")
        for citation in citations:
            with st.expander(
                f"{citation.get('marker', '')} {citation.get('label', '')}"
                f"  ·  relevance {citation.get('score', 0):.2f}"
            ):
                st.text(citation.get("excerpt", ""))
    else:
        st.caption("No source citations were produced for this response.")


def render_review_controls(artifact_id: str, project: str, key_prefix: str) -> None:
    """The mandatory human disposition control required for consequential output."""
    with st.expander("Record review decision"):
        comment = st.text_area("Reviewer comment", key=f"{key_prefix}_comment")
        columns = st.columns(3)
        decisions = [("Accept", "accepted"), ("Accept with edits", "edited"), ("Reject", "rejected")]
        for column, (label, decision) in zip(columns, decisions):
            if column.button(label, key=f"{key_prefix}_{decision}"):
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
            st.error(f"Not permitted: {exc.detail}")
        elif exc.status_code == 503:
            st.warning(str(exc.detail))
        else:
            st.error(f"{exc.status_code}: {exc.detail}")
    else:
        st.error(str(exc))


def document_selector(
    project: str, module: str, label: str = "Document", key: str | None = None
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
        st.info(
            f"No indexed documents in the '{module}' collection. "
            "Upload one on the Documents page, or load the bundled samples."
        )
        return None
    names = [f"{d['name']} ({d['version_label']}, {d['chunk_count']} chunks)" for d in documents]
    choice = st.selectbox(label, range(len(documents)), format_func=lambda i: names[i], key=key)
    return documents[choice]
