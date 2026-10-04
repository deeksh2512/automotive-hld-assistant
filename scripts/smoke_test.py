"""End-to-end smoke test against a running backend.

Exercises the full HLD analysis workflow through the HTTP API exactly as the
Streamlit UI does. Run with the backend listening on API_BASE_URL.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from app.config import settings  # noqa: E402

BASE = settings.api_base_url
PROJECT = "demo-ecu"
HEADERS = {"X-User": settings.default_user}
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" - {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def call(method: str, path: str, **kwargs):
    response = requests.request(
        method, f"{BASE}{path}", headers=HEADERS, timeout=600, **kwargs
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.content


def main() -> int:
    print("\n== System ==")
    health = call("GET", "/health")
    check("health endpoint", health["status"] == "ok")
    check("embeddings ready", health["embeddings_ready"])
    check("vector store ready", health["vectorstore_ready"])
    check("only the HLD module is registered", health["modules"] == ["hld"],
          str(health["modules"]))
    print(f"  LLM: {'available' if health['llm_available'] else 'retrieval-only'} "
          f"- {health['llm_detail'][:90]}")

    print("\n== Documents ==")
    call("POST", "/documents/load-samples", params={"project": PROJECT})
    documents = call("GET", "/documents", params={"project": PROJECT})
    indexed = [d for d in documents if d["status"] == "indexed"]
    check("samples indexed", len(indexed) >= 2, f"{len(indexed)} documents")
    check("no ingestion failures", not [d for d in documents if d["status"] == "failed"])
    check("chunks created", sum(d["chunk_count"] for d in indexed) > 10,
          f"{sum(d['chunk_count'] for d in indexed)} chunks")

    by_name = {d["name"]: d for d in indexed}

    print("\n== Architecture extraction ==")
    hld_a = by_name["sample_hld_body_control.md"]
    hld_b = by_name["sample_hld_body_control_rev_b.md"]
    extract = call("POST", "/hld/extract", params={"project": PROJECT},
                   json={"document_id": hld_a["id"]})
    check("entities extracted", len(extract["entities"]) > 15,
          f"{len(extract['entities'])} entities")
    check("dependencies extracted", len(extract["dependencies"]) > 3,
          f"{len(extract['dependencies'])} edges")
    check("components recognised", extract["counts"].get("component", 0) > 0)
    check("signals recognised", extract["counts"].get("signal", 0) > 0)
    check("graphviz source produced", extract["dot"].startswith("digraph"))
    check("every entity carries page evidence",
          all(entity["pages"] for entity in extract["entities"]))
    check("consistency findings returned", isinstance(extract["findings"], list),
          f"{len(extract['findings'])} findings")

    print("\n== Revision comparison ==")
    diff = call("POST", "/hld/compare", params={"project": PROJECT},
                json={"baseline_document_id": hld_a["id"],
                      "revision_document_id": hld_b["id"]})
    check("revision diff detects additions", diff["summary"]["added"] > 0,
          f"{diff['summary']['added']} added")
    check("revision diff detects removals", diff["summary"]["removed"] > 0,
          f"{diff['summary']['removed']} removed")
    check("dependency changes reported",
          "dependencies_added" in diff and "dependencies_removed" in diff)

    print("\n== Cited question answering ==")
    answer = call("POST", "/query", params={"project": PROJECT},
                  json={"question": "Which components consume Sig_VehicleSpeed?",
                        "module": "hld"})
    check("question returns evidence", len(answer["sources"]) > 0,
          f"{len(answer['sources'])} passages, {answer['confidence']} confidence")
    check("answer carries a confidence grade",
          answer["confidence"] in {"high", "medium", "low"})
    check("answer starts pending review", answer["review_status"] == "pending_review")

    print("\n== Export ==")
    csv_export = call("GET", "/hld/export",
                      params={"project": PROJECT, "artifact_id": extract["artifact_id"],
                              "fmt": "csv"})
    check("CSV export", b"name,kind" in csv_export)
    json_export = call("GET", "/hld/export",
                       params={"project": PROJECT, "artifact_id": extract["artifact_id"],
                               "fmt": "json"})
    check("JSON export", bool(json_export.get("entities")),
          f"{len(json_export.get('entities', []))} entities")
    inventories = call("GET", "/hld/inventories", params={"project": PROJECT})
    check("inventory listed", len(inventories) >= 1, f"{len(inventories)} inventories")

    print("\n== Governance ==")
    artifacts = call("GET", "/artifacts", params={"project": PROJECT})
    check("artifacts recorded", len(artifacts) >= 1, f"{len(artifacts)} artifacts")
    by_id = {a["id"]: a for a in artifacts}
    check("new artifacts start pending review",
          by_id[extract["artifact_id"]]["review_status"] == "pending_review")

    reviewed = call("POST", f"/artifacts/{extract['artifact_id']}/review",
                    params={"project": PROJECT},
                    json={"decision": "accepted",
                          "comment": "Checked against the released design."})
    check("review decision recorded", reviewed["review_status"] == "approved")
    history = call("GET", f"/artifacts/{extract['artifact_id']}/history",
                   params={"project": PROJECT})
    check("review history stored", len(history) == 1)

    audit = call("GET", "/audit", params={"limit": 500})
    actions = {entry["action"] for entry in audit}
    check("audit records ingestion", "document.ingested" in actions)
    check("audit records queries", "query.answered" in actions)
    check("audit records comparisons", "hld.compared" in actions)
    check("audit records reviews", "artifact.reviewed" in actions)
    check("audit volume", len(audit) >= 5, f"{len(audit)} entries")

    print("\n== Access control ==")
    viewer = requests.post(
        f"{BASE}/hld/extract", headers={"X-User": "viewer@local"},
        params={"project": PROJECT},
        json={"document_id": hld_a["id"]},
        timeout=120,
    )
    check("viewer cannot create artifacts", viewer.status_code == 403,
          f"HTTP {viewer.status_code}")

    unknown = requests.get(f"{BASE}/documents", headers=HEADERS,
                           params={"project": "does-not-exist"}, timeout=60)
    check("unknown project rejected", unknown.status_code == 404)

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
