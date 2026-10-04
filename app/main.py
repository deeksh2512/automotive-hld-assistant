"""FastAPI application for the AUTOSAR HLD Analysis Assistant."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routers import artifacts, documents, hld, projects, query, system
from app.config import settings
from app.core.db import init_db
from app.core.ingest import IngestionError
from app.core.llm import LLMUnavailable, get_llm_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    init_db()
    status = get_llm_status()
    if status.available:
        logger.info("LLM ready: %s (%s)", status.model, status.detail)
    else:
        logger.warning("Retrieval-only mode: %s", status.detail)
    yield


app = FastAPI(
    title="AUTOSAR HLD Analysis Assistant",
    description=(
        "AI-assisted analysis of AUTOSAR high-level design documents: entity "
        "extraction, dependency mapping, cited question answering, consistency "
        "checks, and revision comparison. All outputs are evidence-based and "
        "require human review."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IngestionError)
async def ingestion_error_handler(request: Request, exc: IngestionError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(LLMUnavailable)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


for router in (
    system.router,
    projects.router,
    documents.router,
    query.router,
    artifacts.router,
    hld.router,
):
    app.include_router(router)


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "name": "AUTOSAR HLD Analysis Assistant",
        "version": __version__,
        "docs": "/docs",
        "capabilities": {
            "extract": "Architecture entity and dependency inventory - POST /hld/extract",
            "ask": "Cited question answering over indexed designs - POST /query",
            "compare": "Revision diff between two design documents - POST /hld/compare",
            "export": "Inventory export as CSV or JSON - GET /hld/export",
        },
        "governance": "All AI-assisted output requires review by a qualified engineer "
        "before use in compliance, design approval, software release or vehicle validation.",
    }
