"""Local embedding service backed by sentence-transformers (BGE by default)."""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from typing import Sequence

from app.config import settings

logger = logging.getLogger(__name__)

# BGE models expect this instruction prefix on queries but not on documents.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_lock = threading.Lock()


class EmbeddingService:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model = None
        self._dimension: int | None = None

    def _load(self):
        if self._model is None:
            with _lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    logger.info("Loading embedding model %s", self.model_name)
                    self._model = SentenceTransformer(self.model_name)
                    self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def dimension(self) -> int:
        self._load()
        return int(self._dimension or 0)

    def _uses_bge_prefix(self) -> bool:
        return "bge" in self.model_name.lower()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        vectors = model.encode(
            list(texts),
            batch_size=16,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        payload = _QUERY_PREFIX + text if self._uses_bge_prefix() else text
        vector = model.encode([payload], normalize_embeddings=True, show_progress_bar=False)
        return vector[0].tolist()

    def is_ready(self) -> bool:
        try:
            self._load()
            return True
        except Exception as exc:  # pragma: no cover - depends on local model cache
            logger.warning("Embedding model unavailable: %s", exc)
            return False


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
