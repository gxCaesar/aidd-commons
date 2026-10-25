"""Load catalogue YAML and retain directed edge declarations and their provenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class GraphError(ValueError):
    """A graph input has a malformed or unresolved declaration."""


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    tasks: frozenset[str]
    stages: frozenset[str]
    declares_relation: bool


@dataclass(frozen=True)
class Edge:
    source: str
    type: str
    target: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class TypedGraph:
    nodes: dict[str, Node]
    edges: tuple[Edge, ...]


def load_catalogue(directory: Path) -> list[dict[str, Any]]:
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise GraphError("catalogue holds no YAML records")
    records: list[dict[str, Any]] = []
    for path in paths:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise GraphError(f"cannot read record: {path.name}") from error
        if not isinstance(value, dict):
            raise GraphError(f"record is not an object: {path.name}")
        records.append(value)
    return records


def _text_set(value: Any, identifier: str, field: str) -> frozenset[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise GraphError(f"{identifier}: {field} must be a list of non-empty strings")
    return frozenset(value)


def build_graph(
    records: list[dict[str, Any]], node_types: tuple[str, ...], edge_types: tuple[str, ...]
) -> TypedGraph:
    nodes: dict[str, Node] = {}
    for record in records:
        identifier = record.get("id")
        kind = record.get("kind")
        if not isinstance(identifier, str) or not identifier:
            raise GraphError("record has no id")
        if identifier in nodes:
            raise GraphError(f"duplicate catalogue id: {identifier}")
        if kind not in node_types:
            raise GraphError(f"{identifier}: undeclared node type: {kind}")
        relations = record.get("relations")
        if not isinstance(relations, list):
            raise GraphError(f"{identifier}: relations must be a list")
        nodes[identifier] = Node(
            identifier,
            kind,
            _text_set(record.get("tasks"), identifier, "tasks"),
            _text_set(record.get("stages"), identifier, "stages"),
            bool(relations),
        )

    edges: list[Edge] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        identifier = record["id"]
        evidence = record.get("evidence")
        if not isinstance(evidence, list):
            raise GraphError(f"{identifier}: evidence must be a list")
        evidence_ids: set[str] = set()
        relation_evidence: list[str] = []
        for entry in evidence:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                raise GraphError(f"{identifier}: evidence entry has no id")
            entry_id = entry["id"]
            if entry_id in evidence_ids:
                raise GraphError(f"{identifier}: duplicate evidence id: {entry_id}")
            evidence_ids.add(entry_id)
            supports = entry.get("supports")
            if not isinstance(supports, list) or any(not isinstance(x, str) for x in supports):
                raise GraphError(f"{identifier}: evidence supports must be a text list")
            if "relations" in supports:
                relation_evidence.append(entry_id)
        for declaration in record["relations"]:
            if not isinstance(declaration, dict):
                raise GraphError(f"{identifier}: relation must be an object")
            edge_type, target = declaration.get("type"), declaration.get("target")
            if edge_type not in edge_types:
                raise GraphError(f"{identifier}: undeclared edge type: {edge_type}")
            if not isinstance(target, str) or target not in nodes:
                raise GraphError(f"{identifier}: relation target missing from catalogue: {target}")
            triple = (identifier, edge_type, target)
            if triple in seen:
                raise GraphError(f"duplicate declared edge: {triple}")
            seen.add(triple)
            edges.append(Edge(identifier, edge_type, target, tuple(relation_evidence)))
    return TypedGraph(
        nodes, tuple(sorted(edges, key=lambda edge: (edge.source, edge.type, edge.target)))
    )
