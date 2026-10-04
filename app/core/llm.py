"""LLM provider layer.

The platform must remain usable when no model is running: `NullProvider`
keeps retrieval, citations and the deterministic rule engines fully functional
and simply declines to generate prose.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol, runtime_checkable

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """Raised when generation is requested but no model is reachable."""


@dataclass
class LLMStatus:
    available: bool
    provider: str
    model: str
    detail: str


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def status(self) -> LLMStatus: ...

    def generate(self, system: str, user: str, temperature: float | None = None) -> str: ...


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    def status(self) -> LLMStatus:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            response.raise_for_status()
        except Exception as exc:
            return LLMStatus(
                available=False,
                provider=self.name,
                model=self.model,
                detail=f"Ollama not reachable at {self.base_url} ({exc.__class__.__name__}). "
                "Install Ollama and run 'ollama serve'.",
            )
        installed = [m.get("name", "") for m in response.json().get("models", [])]
        base = self.model.split(":")[0]
        if not any(name == self.model or name.startswith(base) for name in installed):
            return LLMStatus(
                available=False,
                provider=self.name,
                model=self.model,
                detail=f"Model '{self.model}' not pulled. Run: ollama pull {self.model}. "
                f"Installed: {', '.join(installed) or 'none'}",
            )
        return LLMStatus(
            available=True,
            provider=self.name,
            model=self.model,
            detail=f"Connected to Ollama at {self.base_url}",
        )

    def generate(self, system: str, user: str, temperature: float | None = None) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": {
                "temperature": settings.llm_temperature if temperature is None else temperature,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:
            raise LLMUnavailable(f"Ollama generation failed: {exc}") from exc
        return (response.json().get("message", {}).get("content") or "").strip()


class NullProvider:
    """Retrieval-only mode. Never fabricates engineering content."""

    name = "none"

    def status(self) -> LLMStatus:
        return LLMStatus(
            available=False,
            provider=self.name,
            model="-",
            detail="No LLM configured. Running in retrieval-only mode: search, "
            "citations and rule engines work; narrative generation is disabled.",
        )

    def generate(self, system: str, user: str, temperature: float | None = None) -> str:
        raise LLMUnavailable(
            "No language model is configured. Install Ollama and set OLLAMA_MODEL to "
            "enable generated summaries; retrieval results and rule-based outputs are "
            "still available."
        )


def build_provider() -> LLMProvider:
    provider = (settings.llm_provider or "none").lower()
    if provider == "ollama":
        return OllamaProvider()
    if provider in {"none", "null", "off", ""}:
        return NullProvider()
    logger.warning("Unknown LLM_PROVIDER '%s'; falling back to retrieval-only mode", provider)
    return NullProvider()


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    return build_provider()


def get_llm_status() -> LLMStatus:
    return get_llm().status()
