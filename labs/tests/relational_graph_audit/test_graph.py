"""Constructed records test direction and unresolved targets."""

import pytest
from aidd_commons.relational_graph_audit.graph import GraphError, build_graph


def record(identifier: str, kind: str = "model") -> dict[str, object]:
    return {
        "id": identifier,
        "kind": kind,
        "tasks": ["prediction"],
        "stages": ["evaluation"],
        "relations": [],
        "evidence": [],
    }


def test_declared_direction_and_source_provenance() -> None:
    left, right = record("model-left"), record("tool-right", "software")
    left["relations"] = [{"type": "uses", "target": "tool-right"}]
    left["evidence"] = [{"id": "source-page", "supports": ["relations"]}]
    graph = build_graph([left, right], ("model", "software"), ("uses",))
    assert list(graph.nodes) == ["model-left", "tool-right"]
    assert [(edge.source, edge.type, edge.target) for edge in graph.edges] == [
        ("model-left", "uses", "tool-right")
    ]
    assert graph.edges[0].evidence_ids == ("source-page",)
    assert graph.nodes["tool-right"].declares_relation is False


def test_missing_target_is_defect() -> None:
    left = record("model-left")
    left["relations"] = [{"type": "uses", "target": "missing-target"}]
    with pytest.raises(GraphError, match="target missing"):
        build_graph([left], ("model",), ("uses",))
