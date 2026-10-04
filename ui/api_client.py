"""Thin HTTP client the Streamlit pages use to reach the FastAPI backend."""

from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from app.config import settings

TIMEOUT = 300


class ApiError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _user() -> str:
    return st.session_state.get("user", settings.default_user)


def _headers() -> dict[str, str]:
    return {"X-User": _user()}


def _handle(response: requests.Response) -> Any:
    if response.ok:
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.content
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    if isinstance(detail, list):
        detail = "; ".join(str(item.get("msg", item)) for item in detail)
    raise ApiError(response.status_code, str(detail))


def get(path: str, params: dict | None = None) -> Any:
    return _handle(
        requests.get(f"{settings.api_base_url}{path}", params=params,
                     headers=_headers(), timeout=TIMEOUT)
    )


def post(path: str, json: dict | None = None, params: dict | None = None) -> Any:
    return _handle(
        requests.post(f"{settings.api_base_url}{path}", json=json, params=params,
                      headers=_headers(), timeout=TIMEOUT)
    )


def delete(path: str, params: dict | None = None) -> Any:
    response = requests.delete(
        f"{settings.api_base_url}{path}", params=params, headers=_headers(), timeout=TIMEOUT
    )
    if response.status_code == 204:
        return None
    return _handle(response)


def upload(path: str, file, data: dict, params: dict) -> Any:
    return _handle(
        requests.post(
            f"{settings.api_base_url}{path}",
            files={"file": (file.name, file.getvalue())},
            data=data,
            params=params,
            headers=_headers(),
            timeout=TIMEOUT,
        )
    )


def download(path: str, params: dict) -> bytes:
    response = requests.get(
        f"{settings.api_base_url}{path}", params=params, headers=_headers(), timeout=TIMEOUT
    )
    if not response.ok:
        raise ApiError(response.status_code, response.text)
    return response.content


def backend_online(timeout: int = 30) -> bool:
    """Health includes a model readiness probe, so allow a generous timeout."""
    try:
        requests.get(f"{settings.api_base_url}/health", timeout=timeout).raise_for_status()
        return True
    except Exception:
        return False
