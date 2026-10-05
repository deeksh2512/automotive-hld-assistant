# AUTOSAR HLD Analysis Assistant

A fully local, retrieval-grounded assistant for reading AUTOSAR High-Level Design documents. It
extracts the architecture inventory, maps dependencies between components, answers questions with
page-level citations, flags consistency problems, and diffs two revisions of a design.

Nothing leaves the machine. Documents, embeddings, prompts and responses stay inside the local data
directory and a locally hosted model.

## Purpose

Reviewing a large HLD by hand is slow and easy to get wrong: elements are introduced in one clause
and referenced in another, dependencies are described in prose, and a new revision rarely comes
with an accurate change list. This assistant reads the document and produces that information
directly, with every row and every claim traceable back to the page it came from.

It is scoped to AUTOSAR high-level design analysis only. There are no other engineering modules.

### Design principle

The architecture inventory, the dependency graph and the consistency findings are produced by
deterministic extraction rules, not by the language model. The model is used only to explain and to
answer questions, and every answer it produces must cite retrieved evidence or it is reported as
ungrounded.

| Concern | How it is handled |
| --- | --- |
| Hallucinated sources | Citation markers that do not match a retrieved passage are stripped and reported |
| Cross-program leakage | One vector collection per project, plus role-based access checks |
| Prompt injection | Document text is fenced as untrusted data the model is instructed not to obey |
| Traceability | Every artifact records its source citations, author and review state |
| Human authority | Artifacts enter a review queue and need a decision before use |

## Features

- **Document ingestion** — PDF, DOCX, XLSX/XLSM, CSV, Markdown and plain text, plus source and
  configuration files (C/C++, Python, Java, C#, MATLAB, CAPL, ARXML/XML, JSON, YAML). Content is
  split on section boundaries so each passage keeps its heading path and page number.
- **OCR fallback** — pages with no extractable text are passed through Tesseract, so scanned
  drawings and exported images remain searchable. Controlled by `ENABLE_OCR`.
- **HLD entity extraction** — inventories software components, BSW modules, ports, interfaces,
  signals, runnables and PDUs using AUTOSAR naming conventions, each traced to the pages and
  sections it appeared in, with a mention count.
- **Dependency analysis** — infers interactions from arrow notation and from verbs such as *sends*,
  *provides*, *requires*, *consumes*, *receives* and *calls*, and renders the result as a Graphviz
  dependency map.
- **Cited question answering** — plain-language questions answered from retrieved passages only,
  with `[S1]`-style markers that resolve to a specific page of a specific document. Answers are
  graded for confidence from retrieval score and citation coverage.
- **Consistency findings** — flags isolated components, dependency endpoints that are never defined
  as entities, naming inconsistencies, and elements mentioned only once.
- **Revision comparison** — re-extracts two revisions and diffs the inventories, reporting which
  elements and dependencies were added, removed or changed.
- **Review workflow** — generated output is a draft until a reviewer accepts it, accepts it with an
  edited summary, or rejects it. Decisions are recorded against the artifact.
- **Audit trail** — every ingestion, query, generated artifact, comparison and review decision is
  written to a searchable log with actor, action and target.
- **Export** — the inventory as CSV or JSON, carrying its reference, citations and review state.

If no language model is reachable the assistant still runs in **retrieval-only mode**: extraction,
the dependency map, consistency checks, revision comparison, search and export all keep working,
and questions return the retrieved passages instead of generated prose.

## Architecture

```
Streamlit UI (8501)  ──HTTP──>  FastAPI backend (8000)
                                  ├─ ingestion: PDF / DOCX / XLSX / ARXML / text, OCR fallback
                                  ├─ embeddings: BAAI/bge-small-en-v1.5 (sentence-transformers)
                                  ├─ vector store: ChromaDB, persistent, one collection per project
                                  ├─ LLM: Ollama, with a retrieval-only fallback
                                  ├─ extractor: AUTOSAR entity and dependency rules
                                  └─ SQLite: projects, documents, artifacts, reviews, audit log
```

| Layer | Technology |
| --- | --- |
| API | FastAPI, Uvicorn, Pydantic v2 |
| UI | Streamlit |
| Persistence | SQLAlchemy 2 over SQLite |
| Vectors | ChromaDB |
| Embeddings | sentence-transformers, `BAAI/bge-small-en-v1.5` |
| Generation | Ollama, default `qwen2.5:7b-instruct` |
| Parsing | PyMuPDF, pdfplumber, python-docx, openpyxl, pytesseract |
| Diagrams | Graphviz |
| Tests | pytest |

## Prerequisites

- **Python 3.11 or newer** (3.12 recommended; the container image uses 3.12)
- **Graphviz** — required to render the dependency map inline. Without it the page falls back to
  showing the DOT source.
- **Tesseract OCR** — optional, only needed for scanned documents. Set `TESSERACT_CMD` if it is not
  on `PATH`.
- **[Ollama](https://ollama.com/download)** — optional. Without it the assistant runs in
  retrieval-only mode.

The embedding model downloads automatically on first run (roughly 130 MB) and is cached locally.

## Installation

```powershell
git clone <your-repository-url>
cd automotive-hld-assistant
.\run.ps1 -Setup
```

`run.ps1 -Setup` creates `.venv`, installs the dependencies from `requirements.txt` — several
minutes the first time, as PyTorch is large — and copies `.env.example` to `.env`.

To set up manually, or on Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: Copy-Item .env.example .env
```

## Running

### Everything at once (Windows)

```powershell
.\run.ps1
```

This reports whether Ollama is reachable, starts the backend, waits for it to become healthy, then
opens the UI at <http://localhost:8501>. Press `Ctrl+C` to stop both processes.

### Services individually

```bash
# 1. Ollama — optional; skip for retrieval-only mode
ollama pull qwen2.5:7b-instruct
ollama serve                       # usually already running as a service after install

# 2. FastAPI backend — http://127.0.0.1:8000, interactive docs at /docs
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Streamlit UI — http://localhost:8501
python -m streamlit run ui/Home.py --server.port 8501
```

Start the backend before the UI; the UI reads `API_BASE_URL` to reach it.

To use a different model, pull it and set `OLLAMA_MODEL` in `.env`:

```
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M
```

### Docker

```bash
docker compose up --build
```

Starts the API on 8000 and the UI on 8501 with persistent volumes for the database, vector store,
uploads and the embedding model cache. Ollama is expected on the host and is reached through
`host.docker.internal`, so the model files are not duplicated into the containers.

## Project structure

```
app/
  api/
    routers/         FastAPI routers: system, projects, documents, query, artifacts, hld
    deps.py          identity, project resolution, role enforcement
    schemas.py       request and response models
  core/
    ingest.py        parsing, OCR fallback, heading detection, section-aware chunking
    embeddings.py    sentence-transformers wrapper
    vectorstore.py   ChromaDB collections, scoped per project
    llm.py           Ollama client and availability probe
    rag.py           grounded answering, citation validation, confidence grading
    db.py            SQLAlchemy models, roles, audit log
  modules/hld/
    extractor.py     AUTOSAR entity and dependency rules, findings, revision diff, DOT output
  config.py          settings loaded from .env
  main.py            FastAPI application
ui/
  Home.py            workspace dashboard and Streamlit entrypoint
  pages/             Documents, HLD Analysis, Review Queue, Audit Trail
  common.py          application shell, sidebar, shared result components
  theme.py           design system: palette, stylesheet, presentational helpers
  api_client.py      typed HTTP client for the backend
data/samples/        a synthetic Body Control Module HLD in two revisions
tests/               ingestion, chunking, citation, extraction and UI render tests
scripts/
  smoke_test.py      end-to-end check against a running backend
  screenshot.py      captures each page for a report or review
```

## Usage

1. **Select a workspace** in the sidebar. A `demo-ecu` project is seeded on first start; create
   others from the sidebar.
2. **Index a document** on the *Documents* page — upload your own, or use *Bundled samples* to load
   the two revisions of the synthetic Body Control Module design.
3. **Extract the architecture** on *HLD Analysis*: choose the document in the toolbar and run
   **Extract**. The readout strip shows the element, link and finding counts; the tabs below hold
   the inventory, dependencies, findings and the dependency map.
4. **Ask questions** on the *Ask* tab and check each claim against its cited passage.
5. **Compare revisions** on the *Revisions* tab when a new issue of the design arrives.
6. **Record a decision** in the *Review Queue* before any output is used.
7. **Export** the inventory as CSV or JSON, and download the audit log from *Audit Trail*.

## Testing

```powershell
.\run.ps1 -Test     # unit suite
.\run.ps1 -Smoke    # end-to-end checks through the HTTP API, backend must be running
```

Or directly:

```bash
python -m pytest tests -q
python scripts/smoke_test.py
```

The unit suite covers heading detection and section-aware chunking, the citation round trip through
ingest and retrieval, stripping of invented citation markers, project-scoped collection isolation,
AUTOSAR entity and dependency extraction, and the revision diff. The Streamlit page tests run only
when the backend is up and are skipped otherwise. The smoke test drives the full workflow against
a live API, including the role-based access checks.

## Configuration

All settings come from `.env`; see `.env.example` for the full list. Every value has a working
default, so the file can be copied unchanged.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | `ollama`, or `none` to force retrieval-only mode |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where the local model is served |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Model tag used for generation |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature |
| `LLM_TIMEOUT_SECONDS` | `180` | Generation timeout |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | sentence-transformers embedding model |
| `DATABASE_URL` | `sqlite:///./data/hld.db` | Swap for PostgreSQL in a larger deployment |
| `VECTORSTORE_DIR` | `./data/vectorstore` | ChromaDB persistence directory |
| `UPLOAD_DIR` | `./data/uploads` | Where ingested source files are stored |
| `RETRIEVAL_TOP_K` | `6` | Passages retrieved per query |
| `CHUNK_TARGET_CHARS` | `1200` | Target chunk size, split on section boundaries |
| `CHUNK_OVERLAP_CHARS` | `150` | Overlap between adjacent chunks |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Backend address used by the UI |
| `ENABLE_OCR` | `true` | Run Tesseract on pages with no extractable text |
| `TESSERACT_CMD` | *(empty)* | Explicit Tesseract path if it is not on `PATH` |
| `DEFAULT_USER` | `engineer@local` | Identity sent as the `X-User` header by the UI |
| `DEFAULT_ROLE` | `engineer` | Role assumed when a user has no explicit project membership |

## Security and privacy

- **Local by default.** Documents, embeddings, the vector store, prompts and responses stay on the
  machine. The only network calls are to the Ollama endpoint you configure, which is local. Nothing
  is sent to a hosted model provider.
- **Project isolation.** Each project has its own ChromaDB collection and every API call is scoped
  to a project key, so content cannot be retrieved across programs.
- **Role-based access.** Roles form a hierarchy — `viewer < engineer < approver < admin`. Viewers
  read, engineers generate, approvers accept or reject artifacts, admins manage membership.
  Identity is carried in the `X-User` header. That is adequate for a pilot behind an organizational
  boundary and is the intended integration point for SSO before wider rollout; it is **not**
  authentication on its own, so do not expose the API to an untrusted network as-is.
- **Prompt injection.** Retrieved document text is fenced as untrusted data and the system prompt
  instructs the model to report, not obey, instruction-like content.
- **Nothing secret is committed.** `.env` is ignored; `.env.example` contains only defaults, local
  paths and model names. The uploads directory, the database and the vector store are ignored, so
  no engineering content reaches the repository. The bundled samples under `data/samples/` are
  synthetic and contain no real project data.
- **Output is a draft.** Nothing produced here may be used for compliance evidence, design
  approval, software release or vehicle validation until a qualified engineer has reviewed and
  approved it against the cited source material.
