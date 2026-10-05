# AUTOSAR HLD Analysis Assistant

A fully local, retrieval-grounded AI assistant for reading AUTOSAR High-Level Design documents.
It extracts the architecture inventory, draws the dependency map, answers questions with page-level
citations, flags consistency problems, and diffs two revisions of a design.

Nothing leaves the machine. Documents, embeddings, prompts, and responses stay inside the local
data directory and a locally hosted model.

## Why it is built this way

The architecture inventory, the dependency graph, and the consistency findings are produced by
deterministic extraction rules, not by the language model. The model is used only to explain and
to answer questions, and every answer it produces must cite retrieved evidence or it is flagged as
ungrounded.

| Concern | How it is handled |
| --- | --- |
| Hallucinated sources | Citation markers that do not match a retrieved chunk are stripped and reported |
| Cross-program leakage | One vector collection per project, plus role-based access checks |
| Prompt injection | Document text is fenced as untrusted data the model must not obey |
| Traceability | Every artifact records its source citations, author, and review state |
| Human authority | Artifacts enter a review queue and need an approver before use |

## Architecture

```
Streamlit UI (8501)  ──HTTP──>  FastAPI backend (8000)
                                   ├─ ingestion: PDF / DOCX / XLSX / ARXML / text, OCR fallback
                                   ├─ embeddings: BAAI/bge-small-en-v1.5
                                   ├─ vector store: ChromaDB (persistent, per-project)
                                   ├─ LLM: Ollama  (falls back to retrieval-only)
                                   ├─ extractor: AUTOSAR entity and dependency rules
                                   └─ SQLite: projects, documents, artifacts, reviews, audit log
```

```
app/
  api/            FastAPI routers, schemas, auth dependencies
  core/           ingestion, embeddings, vector store, LLM providers, RAG, database
  modules/hld/    AUTOSAR entity extraction, consistency checks, revision diff, DOT output
ui/               Streamlit entrypoint, HLD workspace, review queue, audit trail
data/samples/     a synthetic Body Control Module HLD in two revisions
tests/            extraction, chunking, citation, and UI render tests
scripts/          end-to-end smoke test
```

## What it does

- **Architecture extraction** — inventories software components, BSW modules, ports, interfaces,
  signals, runnables and PDUs, each traced back to the page and section it came from.
- **Dependency map** — renders the communication graph between components as Graphviz DOT.
- **Cited question answering** — plain-language questions answered with `[S1]`-style markers that
  resolve to a specific page of a specific document.
- **Consistency checks** — flags isolated components, undefined endpoints, naming inconsistencies,
  and elements mentioned only once.
- **Revision comparison** — diffs two revisions and reports which entities and dependencies were
  added, removed, or changed.
- **Export** — the inventory as CSV or JSON for downstream tooling.

## Interface

A dark navy workstation with five views: **Overview**, **Documents**, **HLD Analysis**, and the
two governance views, **Review Queue** and **Audit Trail**. Overview is a dashboard of the
workspace's current state. HLD Analysis is the engineering surface: a persistent document toolbar,
a readout strip of entity, link and finding counts, then tabs for the inventory, dependencies,
findings, dependency map, question answering, revision comparison and exports.

The visual layer lives in `ui/theme.py` — a small design system of palette tokens, a stylesheet,
and presentational helpers (page headers, readout strips, panels, dense tables, chips, callouts,
evidence blocks, empty states). Surfaces are flat and separated by hairline rules rather than
stacked cards, so the data stays the loudest thing on the page. It deliberately uses the operating
system's native font stack and inline SVG rather than a web font or icon pack, because anything
fetched from a CDN would fail on an air-gapped machine and render as raw text.

Two Streamlit behaviours are worth knowing before editing the UI. Imported modules are cached, so
changes to `ui/theme.py` or `ui/common.py` need a server restart rather than a browser refresh.
And `stMarkdownContainer` carries a `-1rem` bottom margin to cancel a trailing paragraph margin;
custom markup has no such margin, so the stylesheet resets it — without that, anything rendered
after a custom block overlaps it.

Read-only tables are rendered as HTML by `theme.table` rather than `st.dataframe`. Streamlit's
grid draws to a canvas, so neither its row height nor its type scale can be adjusted, and a dense
table is the point of an inventory view. Long free text is clamped to two lines with the full
value kept as the cell tooltip.

Every answer is shown the same way: the response, a confidence chip, a provenance chip saying
whether it was model-generated or retrieval-only, then each supporting passage with its marker,
source document, page and relevance score.

To capture the interface for a report or review:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts\screenshot.py http://localhost:8501 shots
```

## Quick start (Windows)

```powershell
cd C:\Users\deeksham\automotive-hld-assistant
.\run.ps1
```

The first run creates `.venv`, installs dependencies (several minutes — `torch` is large), copies
`.env.example` to `.env`, starts the backend, waits for it to become healthy, then opens the UI at
<http://localhost:8501>. Press `Ctrl+C` to stop both processes.

Other modes:

```powershell
.\run.ps1 -Setup   # install dependencies only
.\run.ps1 -Test    # run the unit suite
.\run.ps1 -Smoke   # end-to-end check against an already running backend
```

In the UI, pick the seeded `demo-ecu` project and use **Documents → Load bundled samples** to index
the two revisions of the sample design, then open **HLD Analysis**.

## Ollama setup

The assistant expects a locally hosted model served by [Ollama](https://ollama.com/download).

```powershell
ollama pull qwen2.5:7b-instruct
ollama serve          # usually already running as a service after install
```

That model name matches the default in `.env.example`. To use a different one, pull it and set
`OLLAMA_MODEL` in `.env`, for example:

```
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M
```

**If Ollama is not installed or the model is not pulled, the assistant still runs.** It degrades to
*retrieval-only mode*: entity extraction, the dependency map, consistency checks, revision
comparison, search and export all keep working, and questions return the retrieved passages with
their citations instead of generated prose. The model status is shown in the sidebar of every page.

## Docker

```bash
docker compose up --build
```

This starts the API on 8000 and the UI on 8501, with persistent volumes for the database, vector
store, uploads, and the downloaded embedding model. Ollama is expected on the host and is reached
through `host.docker.internal`; keep it running outside the containers so the model files are not
duplicated.

## Configuration

Everything is set through `.env` (see `.env.example` for the full list and defaults).

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | `ollama` or `none` to force retrieval-only mode |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Model tag to generate with |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Sentence-transformers embedding model |
| `RETRIEVAL_TOP_K` | `6` | Chunks retrieved per query |
| `CHUNK_TARGET_CHARS` | `1200` | Target chunk size, split on section boundaries |
| `DATABASE_URL` | `sqlite:///./data/hld.db` | Swap for PostgreSQL in a larger deployment |
| `ENABLE_OCR` | `true` | Use Tesseract on pages with no extractable text |
| `DEFAULT_USER` | `engineer@local` | Identity sent as the `X-User` header by the UI |

## Testing

```powershell
.\run.ps1 -Test     # unit suite
.\run.ps1 -Smoke    # end-to-end checks through the HTTP API
```

The unit suite covers heading detection and section-aware chunking, the citation round trip through
ingest and retrieval, stripping of invented citation markers, project-scoped collection isolation,
AUTOSAR entity and dependency extraction, and the revision diff. Streamlit page tests run only when
the backend is up and are skipped otherwise.

## Governance model

Roles form a hierarchy: `viewer < engineer < approver < admin`. Viewers read, engineers generate,
approvers accept or reject artifacts, admins manage project membership. Identity is carried in the
`X-User` header — adequate for a pilot behind an organizational boundary, and the point to replace
with SSO before wider rollout.

Every generation, review decision, upload, and deletion is written to the audit log with the user,
project, action, and target, visible on the Audit Trail page.

AI output is a draft. Nothing produced here may be used for compliance evidence, design approval,
software release, or vehicle validation until an authorized engineering specialist has reviewed and
approved it against the cited source material.

## Relationship to the full platform

This project is the standalone version of Case Study 1 from the Automotive Engineering AI Platform.
The sibling project at `../automotive-engineering-ai` contains the same HLD assistant alongside four
more: ISO 26262 HARA, ISO/SAE 21434 TARA, secure code review, and ISO 14229 UDS diagnostics. The
shared ingestion, retrieval, governance, and audit layers are identical in both.
