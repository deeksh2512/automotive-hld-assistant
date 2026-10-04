"""Chunking, citation round trip and HLD extraction."""

from __future__ import annotations

from app.core.ingest import Block, chunk_blocks, chunk_code, detect_heading
from app.core.rag import build_evidence_block, validate_citations
from app.core.vectorstore import RetrievedChunk, collection_name, slugify
from app.modules.hld.extractor import (
    analyze_blocks,
    compare_revisions,
    consistency_findings,
    to_dot,
)

SAMPLE = """1 Introduction
This document describes the architecture of the body control module.

1.1 Scope
The scope covers the application layer only.

2 Components
SWC_DoorControl manages the central locking function for all doors.
SWC_DoorControl sends Sig_DoorLockState to SWC_Gateway.
"""


def test_heading_detection():
    assert detect_heading("1 Introduction") == (1, "1 Introduction")
    assert detect_heading("1.1 Scope") == (2, "1.1 Scope")
    assert detect_heading("## Markdown Heading") == (2, "Markdown Heading")
    assert detect_heading("This is an ordinary sentence of prose text.") is None


def test_chunking_preserves_heading_path_and_pages():
    chunks = chunk_blocks([Block(text=SAMPLE, page=7)], document_id="doc1")
    assert chunks
    assert all(chunk.page_start == 7 for chunk in chunks)
    assert any("1.1 Scope" in chunk.heading_path for chunk in chunks)
    assert all(chunk.chunk_id.startswith("doc1-") for chunk in chunks)


def test_chunk_ids_are_unique():
    blocks = [Block(text=SAMPLE, page=page) for page in range(1, 6)]
    chunks = chunk_blocks(blocks, document_id="doc2")
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_tables_stay_whole():
    blocks = [
        Block(text="2 Signals", page=3),
        Block(text="[TABLE]\nSignal | ID\nSig_A | 0x100", page=3, kind="table"),
    ]
    chunks = chunk_blocks(blocks, document_id="doc3")
    table_chunks = [chunk for chunk in chunks if chunk.kind == "table"]
    assert len(table_chunks) == 1
    assert "Sig_A" in table_chunks[0].text


def test_citation_label_formats_page_ranges():
    chunks = chunk_blocks([Block(text=SAMPLE, page=4)], document_id="doc4")
    assert "p.4" in chunks[0].citation_label()


def test_code_chunking_tracks_line_numbers():
    code = "\n".join(
        [
            "#include <stdio.h>",
            "",
            "void first(void)",
            "{",
            "    int a = 1;",
            "    (void)a;",
            "}",
            "",
            "void second(int b)",
            "{",
            "    b = b + 1;",
            "}",
        ]
    )
    chunks = chunk_code(code, "doc5", "c")
    assert chunks
    assert all(chunk.kind == "code" for chunk in chunks)
    assert all(chunk.page_start >= 1 for chunk in chunks)
    assert any("second" in chunk.text for chunk in chunks)


# --- Citation validation ---------------------------------------------------


def _chunk(index: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"c{index}",
        text=f"evidence {index}",
        score=0.8,
        metadata={"document_name": "HLD.pdf", "page_start": index, "page_end": index},
    )


def test_evidence_block_numbers_from_one():
    block = build_evidence_block([_chunk(1), _chunk(2)])
    assert "[S1]" in block and "[S2]" in block
    assert "---begin passage---" in block


def test_valid_citations_round_trip_to_chunks():
    chunks = [_chunk(1), _chunk(2), _chunk(3)]
    answer, citations, warnings = validate_citations(
        "The gateway routes signals [S1] and the door module locks [S3].", chunks
    )
    assert [c.chunk_id for c in citations] == ["c1", "c3"]
    assert not warnings
    assert "[S1]" in answer


def test_invented_markers_are_stripped_and_warned():
    chunks = [_chunk(1)]
    answer, citations, warnings = validate_citations(
        "This is supported [S1] and this is invented [S9].", chunks
    )
    assert "[S9]" not in answer
    assert [c.chunk_id for c in citations] == ["c1"]
    assert any("non-existent" in warning for warning in warnings)


def test_uncited_answer_is_flagged_as_ungrounded():
    _, citations, warnings = validate_citations("The ECU has four doors.", [_chunk(1)])
    assert citations == []
    assert any("ungrounded" in warning for warning in warnings)


def test_citation_label_includes_document_and_page():
    label = _chunk(5).citation_label()
    assert "HLD.pdf" in label and "p.5" in label


# --- Project isolation -----------------------------------------------------


def test_collection_names_are_project_scoped():
    assert collection_name("Program A", "hld") != collection_name("Program B", "hld")
    assert collection_name("prog", "hld") != collection_name("prog", "notes")
    assert len(collection_name("a" * 200, "hld")) <= 63


def test_slugify():
    assert slugify("Program X200 / Body") == "program-x200-body"
    assert slugify("") == "default"


# --- HLD extraction --------------------------------------------------------


def test_hld_entity_extraction():
    entities, dependencies = analyze_blocks([Block(text=SAMPLE, page=1)])
    names = {entity.name for entity in entities}
    assert "DoorControl" in names or "SWC_DoorControl" in names
    assert any(dependency.relation == "sends_to" for dependency in dependencies)


def test_hld_findings_and_dot_output():
    entities, dependencies = analyze_blocks([Block(text=SAMPLE, page=1)])
    findings = consistency_findings(entities, dependencies)
    assert isinstance(findings, list)
    dot = to_dot(entities, dependencies)
    assert dot.startswith("digraph architecture {")
    assert dot.rstrip().endswith("}")


def test_hld_entities_carry_page_evidence():
    entities, _ = analyze_blocks([Block(text=SAMPLE, page=11)])
    assert entities
    assert all(11 in entity.pages for entity in entities)
    assert all(entity.evidence for entity in entities)


# --- Revision comparison ---------------------------------------------------

REVISION_B = """2 Components
SWC_DoorControl manages the central locking function for all doors.
SWC_DoorControl sends Sig_DoorLockState to SWC_Gateway.
SWC_MirrorFold folds the mirrors when the vehicle is locked.
"""


def test_revision_diff_reports_added_elements():
    baseline, _ = analyze_blocks([Block(text=SAMPLE, page=1)])
    revision, _ = analyze_blocks([Block(text=REVISION_B, page=1)])
    diff = compare_revisions(baseline, revision)
    added = {entry["name"] for entry in diff["added"]}
    assert any("MirrorFold" in name for name in added)
    assert not any("MirrorFold" in entry["name"] for entry in diff["removed"])


def test_revision_diff_is_empty_for_identical_documents():
    entities, _ = analyze_blocks([Block(text=SAMPLE, page=1)])
    diff = compare_revisions(entities, entities)
    assert diff["added"] == [] and diff["removed"] == []
