"""AUTOSAR architecture entity extraction from High-Level Design content.

Deterministic pattern matching, not model inference: an architecture inventory
has to be reproducible and every entry has to point back at a page.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from app.core.ingest import Block, Chunk

# AUTOSAR identifier conventions seen in OEM and Tier-1 HLDs.
_SWC = re.compile(
    r"\b(?:SWC[_ ]?(?P<a>[A-Z][A-Za-z0-9]{2,40})"
    r"|(?P<b>[A-Z][A-Za-z0-9]{2,40})[_ ]SWC"
    r"|(?P<c>Swc[A-Z][A-Za-z0-9]{2,40})"
    r"|(?P<d>Cdd[A-Z][A-Za-z0-9]{2,40}))\b"
)
_BSW = re.compile(
    r"\b(Com|PduR|CanIf|CanTp|CanSM|CanNm|Dcm|Dem|Det|Fee|Ea|NvM|EcuM|BswM|Os|RTE|Rte"
    r"|IoHwAb|Dio|Adc|Pwm|Spi|Wdg|WdgM|CryIf|Csm|SecOC|FrIf|EthIf|EthSM|SoAd|DoIP)\b"
)
_PORT = re.compile(
    r"\b(?P<kind>PPort|RPort|P-Port|R-Port|ProvidePort|RequirePort)[_ :]*"
    r"(?P<name>[A-Za-z][A-Za-z0-9_]{2,48})?",
    re.IGNORECASE,
)
_INTERFACE = re.compile(
    r"\b(?:IF[_ ](?P<a>[A-Za-z][A-Za-z0-9_]{2,48})"
    r"|(?P<b>[A-Za-z][A-Za-z0-9_]{2,48})[_ ]?(?:Interface|_IF)\b)"
)
_INTERFACE_KIND = re.compile(
    r"\b(SenderReceiver|Sender-Receiver|ClientServer|Client-Server|ModeSwitch|NvData|Trigger|Parameter)\b",
    re.IGNORECASE,
)
_SIGNAL = re.compile(
    r"\b(?:Sig[_ ](?P<a>[A-Za-z][A-Za-z0-9_]{2,48})"
    r"|(?P<b>[A-Z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\s*(?:signal|Signal)\b)"
)
_RUNNABLE = re.compile(r"\b(?:Re[_ ]|Runnable[_ :]*)(?P<name>[A-Za-z][A-Za-z0-9_]{2,48})\b")
_DATA_ELEMENT = re.compile(r"\bDE[_ ](?P<name>[A-Za-z][A-Za-z0-9_]{2,48})\b")
_PDU = re.compile(r"\b(?P<name>[A-Za-z][A-Za-z0-9_]{2,40})[_ ]?(?:PDU|Pdu|IPdu)\b")
_CAN_ID = re.compile(r"\b0x[0-9A-Fa-f]{3,8}\b")

# Dependency phrasing: "A sends X to B", "A requires Y from B", "A -> B".
_ARROW = re.compile(
    r"(?P<src>[A-Za-z][A-Za-z0-9_]{2,48})\s*(?:->|-->|→)\s*(?P<dst>[A-Za-z][A-Za-z0-9_]{2,48})"
)
_VERB_DEP = re.compile(
    r"\b(?P<src>[A-Z][A-Za-z0-9_]{2,48})\s+"
    r"(?P<verb>sends|provides|publishes|requires|consumes|receives|calls|invokes|subscribes to)\s+"
    r"(?P<what>[A-Za-z][A-Za-z0-9_]{2,48})"
    r"(?:\s+(?:to|from|of|on)\s+(?P<dst>[A-Z][A-Za-z0-9_]{2,48}))?",
    re.IGNORECASE,
)

_NOISE = {
    "The", "This", "That", "These", "Those", "Table", "Figure", "Section", "Note",
    "Document", "Overview", "Description", "Name", "Type", "Value", "Chapter",
    "Introduction", "Reference", "Version", "Page", "And", "For", "With", "All",
}

ENTITY_KINDS = ("component", "bsw_module", "port", "interface", "signal", "runnable", "pdu")


@dataclass
class Entity:
    name: str
    kind: str
    detail: str = ""
    pages: set[int] = field(default_factory=set)
    sections: set[str] = field(default_factory=set)
    occurrences: int = 0
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "detail": self.detail,
            "pages": sorted(self.pages),
            "sections": sorted(s for s in self.sections if s)[:4],
            "occurrences": self.occurrences,
            "evidence": self.evidence,
        }


@dataclass
class Dependency:
    source: str
    target: str
    relation: str
    page: int
    evidence: str

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "page": self.page,
            "evidence": self.evidence,
        }


def _clean(name: str | None) -> str | None:
    if not name:
        return None
    name = name.strip(" .,:;|()[]{}\"'")
    if len(name) < 3 or len(name) > 60:
        return None
    if name in _NOISE or name.lower() in {n.lower() for n in _NOISE}:
        return None
    if name.isdigit():
        return None
    return name


class EntityCollector:
    def __init__(self) -> None:
        self._entities: dict[tuple[str, str], Entity] = {}

    def add(
        self,
        name: str | None,
        kind: str,
        page: int,
        section: str,
        evidence: str,
        detail: str = "",
    ) -> None:
        cleaned = _clean(name)
        if cleaned is None:
            return
        key = (kind, cleaned)
        entity = self._entities.get(key)
        if entity is None:
            entity = Entity(name=cleaned, kind=kind, detail=detail, evidence=evidence.strip()[:300])
            self._entities[key] = entity
        entity.pages.add(page)
        if section:
            entity.sections.add(section)
        entity.occurrences += 1
        if detail and not entity.detail:
            entity.detail = detail

    def results(self) -> list[Entity]:
        return sorted(
            self._entities.values(),
            key=lambda e: (ENTITY_KINDS.index(e.kind) if e.kind in ENTITY_KINDS else 9, e.name),
        )


def extract_from_text(text: str, page: int, section: str, collector: EntityCollector) -> None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        for match in _SWC.finditer(stripped):
            name = match.group("a") or match.group("b") or match.group("c") or match.group("d")
            collector.add(name, "component", page, section, stripped)

        for match in _BSW.finditer(stripped):
            collector.add(match.group(1), "bsw_module", page, section, stripped,
                          detail="AUTOSAR basic software module")

        for match in _PORT.finditer(stripped):
            kind_text = match.group("kind")
            name = match.group("name") or kind_text
            direction = "provided" if kind_text.lower().startswith(("pport", "p-port", "provide")) else "required"
            collector.add(name, "port", page, section, stripped, detail=f"{direction} port")

        for match in _INTERFACE.finditer(stripped):
            name = match.group("a") or match.group("b")
            kind_match = _INTERFACE_KIND.search(stripped)
            collector.add(
                name,
                "interface",
                page,
                section,
                stripped,
                detail=kind_match.group(1) if kind_match else "",
            )

        for match in _SIGNAL.finditer(stripped):
            name = match.group("a") or match.group("b")
            can_id = _CAN_ID.search(stripped)
            collector.add(
                name,
                "signal",
                page,
                section,
                stripped,
                detail=f"CAN ID {can_id.group(0)}" if can_id else "",
            )

        for match in _RUNNABLE.finditer(stripped):
            collector.add(match.group("name"), "runnable", page, section, stripped)

        for match in _DATA_ELEMENT.finditer(stripped):
            collector.add(match.group("name"), "signal", page, section, stripped,
                          detail="data element")

        for match in _PDU.finditer(stripped):
            collector.add(match.group("name"), "pdu", page, section, stripped)


def _normalize(name: str) -> str:
    """Collapse the naming variants used for one element across a document."""
    key = name.lower().replace("-", "_")
    for prefix in ("swc_", "cdd_", "if_", "sig_", "de_", "re_"):
        if key.startswith(prefix):
            key = key[len(prefix) :]
    for suffix in ("_swc", "_if", "_pdu"):
        if key.endswith(suffix):
            key = key[: -len(suffix)]
    return key.replace("_", "")


def build_alias_index(entities: Sequence[Entity]) -> dict[str, str]:
    """Map every naming variant onto the canonical extracted entity name."""
    index: dict[str, str] = {}
    for entity in entities:
        index.setdefault(entity.name, entity.name)
        index.setdefault(_normalize(entity.name), entity.name)
    return index


def extract_dependencies(
    text: str, page: int, aliases: dict[str, str] | None = None
) -> list[Dependency]:
    """Find directed relationships, resolving endpoints to canonical entity names."""
    aliases = aliases or {}

    def resolve(name: str) -> tuple[str, bool]:
        if name in aliases:
            return aliases[name], True
        normalized = _normalize(name)
        if normalized in aliases:
            return aliases[normalized], True
        return name, False

    dependencies: list[Dependency] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        candidates: list[tuple[str, str, str]] = []
        for match in _ARROW.finditer(stripped):
            source = _clean(match.group("src"))
            target = _clean(match.group("dst"))
            if source and target:
                candidates.append((source, target, "flows_to"))

        for match in _VERB_DEP.finditer(stripped):
            source = _clean(match.group("src"))
            target = _clean(match.group("dst")) or _clean(match.group("what"))
            if not source or not target:
                continue
            verb = match.group("verb").lower()
            relation = {
                "sends": "sends_to",
                "provides": "provides_to",
                "publishes": "publishes_to",
                "requires": "requires_from",
                "consumes": "consumes_from",
                "receives": "receives_from",
                "calls": "calls",
                "invokes": "calls",
                "subscribes to": "subscribes_to",
            }.get(verb, "related_to")
            candidates.append((source, target, relation))

        for raw_source, raw_target, relation in candidates:
            source, source_known = resolve(raw_source)
            target, target_known = resolve(raw_target)
            if source == target:
                continue
            # Keep an edge only when at least one end is a recognised entity,
            # otherwise ordinary prose produces spurious relationships.
            if aliases and not (source_known or target_known):
                continue
            dependencies.append(Dependency(source, target, relation, page, stripped[:220]))

    return dependencies


def analyze_blocks(blocks: Sequence[Block]) -> tuple[list[Entity], list[Dependency]]:
    collector = EntityCollector()
    section = ""
    for block in blocks:
        extract_from_text(block.text, block.page, section, collector)
    entities = collector.results()
    aliases = build_alias_index(entities)

    dependencies: list[Dependency] = []
    seen: set[tuple[str, str, str]] = set()
    for block in blocks:
        for dependency in extract_dependencies(block.text, block.page, aliases):
            key = (dependency.source, dependency.target, dependency.relation)
            if key not in seen:
                seen.add(key)
                dependencies.append(dependency)
    return entities, dependencies


def analyze_chunks(chunks: Sequence[Chunk]) -> tuple[list[Entity], list[Dependency]]:
    collector = EntityCollector()
    for chunk in chunks:
        extract_from_text(chunk.text, chunk.page_start, chunk.heading_path, collector)
    entities = collector.results()
    aliases = build_alias_index(entities)

    dependencies: list[Dependency] = []
    seen: set[tuple[str, str, str]] = set()
    for chunk in chunks:
        for dependency in extract_dependencies(chunk.text, chunk.page_start, aliases):
            key = (dependency.source, dependency.target, dependency.relation)
            if key not in seen:
                seen.add(key)
                dependencies.append(dependency)
    return entities, dependencies


# --------------------------------------------------------------------------
# Completeness and consistency checks
# --------------------------------------------------------------------------


def consistency_findings(
    entities: Sequence[Entity], dependencies: Sequence[Dependency]
) -> list[dict]:
    """Flag the mismatches the document asks for: orphans, dangling edges, casing drift."""
    findings: list[dict] = []
    by_name = {entity.name: entity for entity in entities}
    components = [e for e in entities if e.kind in {"component", "bsw_module"}]
    connected: set[str] = set()
    for dependency in dependencies:
        connected.add(dependency.source)
        connected.add(dependency.target)

    for component in components:
        if component.name not in connected:
            findings.append(
                {
                    "severity": "medium",
                    "category": "isolated_component",
                    "entity": component.name,
                    "message": f"Component '{component.name}' has no documented interaction "
                    "with any other component.",
                    "pages": sorted(component.pages),
                    "evidence": component.evidence,
                }
            )

    for dependency in dependencies:
        for role, name in (("source", dependency.source), ("target", dependency.target)):
            if name not in by_name:
                findings.append(
                    {
                        "severity": "high",
                        "category": "undefined_endpoint",
                        "entity": name,
                        "message": f"Dependency {role} '{name}' is referenced but never "
                        "defined as an architecture entity.",
                        "pages": [dependency.page],
                        "evidence": dependency.evidence,
                    }
                )

    # Terminology drift: identifiers that differ only by case or separators.
    normalized: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        normalized[entity.name.lower().replace("_", "").replace("-", "")].append(entity.name)
    for variants in normalized.values():
        unique = sorted(set(variants))
        if len(unique) > 1:
            findings.append(
                {
                    "severity": "low",
                    "category": "naming_inconsistency",
                    "entity": unique[0],
                    "message": "Inconsistent naming for what appears to be one element: "
                    + ", ".join(unique),
                    "pages": sorted(by_name[unique[0]].pages),
                    "evidence": "",
                }
            )

    # Signals and interfaces mentioned exactly once are usually incomplete specs.
    for entity in entities:
        if entity.kind in {"signal", "interface"} and entity.occurrences == 1:
            findings.append(
                {
                    "severity": "low",
                    "category": "single_mention",
                    "entity": entity.name,
                    "message": f"{entity.kind.capitalize()} '{entity.name}' is mentioned only "
                    "once; producer or consumer may be undocumented.",
                    "pages": sorted(entity.pages),
                    "evidence": entity.evidence,
                }
            )

    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 3))
    return findings


def compare_revisions(
    baseline: Sequence[Entity], revision: Sequence[Entity]
) -> dict[str, list[dict]]:
    """Diff two indexed revisions of the same HLD."""
    base_index = {(e.kind, e.name): e for e in baseline}
    rev_index = {(e.kind, e.name): e for e in revision}

    added = [rev_index[k].to_dict() for k in rev_index.keys() - base_index.keys()]
    removed = [base_index[k].to_dict() for k in base_index.keys() - rev_index.keys()]
    changed = []
    for key in base_index.keys() & rev_index.keys():
        before, after = base_index[key], rev_index[key]
        if before.detail != after.detail and (before.detail or after.detail):
            changed.append(
                {
                    "name": after.name,
                    "kind": after.kind,
                    "before": before.detail,
                    "after": after.detail,
                    "pages": sorted(after.pages),
                }
            )
    return {
        "added": sorted(added, key=lambda d: (d["kind"], d["name"])),
        "removed": sorted(removed, key=lambda d: (d["kind"], d["name"])),
        "changed": sorted(changed, key=lambda d: (d["kind"], d["name"])),
    }


# Fill, border and label colour per entity kind, tuned for the dark canvas the
# map is drawn on.
_NODE_STYLE = {
    "component": ("#15294A", "#3B82F6", "#CFE0FF"),
    "bsw_module": ("#18212F", "#4A5C77", "#C2CEE0"),
    "signal": ("#2B2413", "#B5891F", "#F5D88A"),
    "pdu": ("#2B2413", "#B5891F", "#F5D88A"),
    "interface": ("#241E3D", "#7C6BD1", "#D6CCFA"),
    "runnable": ("#102A22", "#2F8F6D", "#9BE7C8"),
    "port": ("#141D2D", "#3A4A66", "#A9B8CE"),
}
_DEFAULT_NODE_STYLE = ("#141D2D", "#3A4A66", "#C2CEE0")


def to_dot(entities: Sequence[Entity], dependencies: Sequence[Dependency]) -> str:
    """Graphviz source for the dependency map."""
    lines = [
        "digraph architecture {",
        '  graph [rankdir=LR, bgcolor="transparent", splines=spline, '
        "nodesep=0.45, ranksep=0.85, pad=0.3];",
        '  node [shape=box, style="filled", fontname="Segoe UI,Helvetica,Arial", '
        "fontsize=10, penwidth=1.1, margin=\"0.18,0.11\"];",
        '  edge [fontname="Segoe UI,Helvetica,Arial", fontsize=8, color="#5A7091", '
        'fontcolor="#93A6C2", arrowsize=0.7, penwidth=1.0];',
    ]
    shown = {d.source for d in dependencies} | {d.target for d in dependencies}
    kinds = {e.name: e.kind for e in entities}
    for name in sorted(shown):
        kind = kinds.get(name, "unknown")
        fill, border, text = _NODE_STYLE.get(kind, _DEFAULT_NODE_STYLE)
        shape = "box" if kind in {"component", "bsw_module"} else "ellipse"
        lines.append(
            f'  "{name}" [shape={shape}, label="{name}\\n({kind})", '
            f'fillcolor="{fill}", color="{border}", fontcolor="{text}"];'
        )
    for dependency in dependencies:
        lines.append(
            f'  "{dependency.source}" -> "{dependency.target}" '
            f'[label="{dependency.relation}"];'
        )
    lines.append("}")
    return "\n".join(lines)
