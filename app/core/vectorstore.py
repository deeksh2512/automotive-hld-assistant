"""ChromaDB-backed vector store with per-project, per-module isolation.

Collections are named `{project}__{module}` so that one program's documents can
never be retrieved while working in another program's workspace.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Sequence

from app.config import settings
from app.core.embeddings import get_embedding_service
from app.core.ingest import Chunk

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_SLUG = re.compile(r"[^a-z0-9_-]+")


def slugify(value: str) -> str:
    slug = _SLUG.sub("-", value.strip().lower()).strip("-")
    return slug or "default"


def collection_name(project_key: str, module: str) -> str:
    # Chroma requires 3-63 chars, start/end alphanumeric.
    name = f"{slugify(project_key)}__{slugify(module)}"
    return name[:63].strip("-_") or "default__general"


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any]

    @property
    def document_name(self) -> str:
        return str(self.metadata.get("document_name", "unknown"))

    @property
    def heading_path(self) -> str:
        return str(self.metadata.get("heading_path", ""))

    def citation_label(self) -> str:
        start = self.metadata.get("page_start")
        end = self.metadata.get("page_end")
        if start is None:
            location = ""
        elif start == end:
            location = f"p.{start}"
        else:
            location = f"pp.{start}-{end}"
        parts = [self.document_name]
        if self.heading_path:
            parts.append(self.heading_path)
        if location:
            parts.append(location)
        return " | ".join(parts)


class VectorStore:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            with _lock:
                if self._client is None:
                    import chromadb
                    from chromadb.config import Settings as ChromaSettings

                    settings.ensure_directories()
                    self._client = chromadb.PersistentClient(
                        path=str(settings.vectorstore_dir),
                        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
                    )
        return self._client

    def _collection(self, project_key: str, module: str):
        client = self._get_client()
        return client.get_or_create_collection(
            name=collection_name(project_key, module),
            metadata={"hnsw:space": "cosine", "project": project_key, "module": module},
        )

    def add_chunks(
        self,
        project_key: str,
        module: str,
        chunks: Sequence[Chunk],
        base_metadata: dict[str, Any],
    ) -> int:
        if not chunks:
            return 0
        embedder = get_embedding_service()
        collection = self._collection(project_key, module)
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        metadatas = []
        for chunk in chunks:
            meta = dict(base_metadata)
            meta.update(chunk.to_metadata())
            metadatas.append(meta)
        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=vectors,
            metadatas=metadatas,
        )
        return len(chunks)

    def search(
        self,
        project_key: str,
        module: str,
        query: str,
        top_k: int | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        collection = self._collection(project_key, module)
        if collection.count() == 0:
            return []
        embedder = get_embedding_service()
        vector = embedder.embed_query(query)
        limit = min(top_k or settings.retrieval_top_k, max(collection.count(), 1))
        result = collection.query(
            query_embeddings=[vector],
            n_results=limit,
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[RetrievedChunk] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            hits.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=text,
                    # Cosine distance in [0, 2] -> similarity in [0, 1].
                    score=max(0.0, 1.0 - float(distance) / 2.0),
                    metadata=dict(metadata or {}),
                )
            )
        return hits

    def get_by_ids(self, project_key: str, module: str, ids: Sequence[str]) -> list[RetrievedChunk]:
        if not ids:
            return []
        collection = self._collection(project_key, module)
        result = collection.get(ids=list(ids), include=["documents", "metadatas"])
        return [
            RetrievedChunk(chunk_id=i, text=d, score=1.0, metadata=dict(m or {}))
            for i, d, m in zip(
                result.get("ids", []), result.get("documents", []), result.get("metadatas", [])
            )
        ]

    def delete_document(self, project_key: str, module: str, document_id: str) -> None:
        collection = self._collection(project_key, module)
        collection.delete(where={"document_id": document_id})

    def count(self, project_key: str, module: str) -> int:
        try:
            return self._collection(project_key, module).count()
        except Exception:
            return 0

    def list_collections(self) -> list[str]:
        try:
            return [c.name for c in self._get_client().list_collections()]
        except Exception:
            return []

    def is_ready(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("Vector store unavailable: %s", exc)
            return False


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return VectorStore()
