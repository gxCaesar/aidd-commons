"""Candidate pairs, evidence, outgoing isolation and counts follow the protocol."""

from pathlib import Path

from aidd_commons.relational_graph_audit.analysis import analyze, check_invariants
from aidd_commons.relational_graph_audit.graph import build_graph, load_catalogue
from aidd_commons.relational_graph_audit.protocol import EDGE_TYPES, NODE_TYPES

ROOT = Path(__file__).resolve().parents[3]


def test_constructed_graph_candidate_and_provenance_rules() -> None:
    records = [
        {
            "id": "a",
            "kind": "model",
            "tasks": ["one"],
            "stages": [],
            "relations": [{"type": "uses", "target": "b"}],
            "evidence": [{"id": "page", "supports": ["relations"]}],
        },
        {
            "id": "b",
            "kind": "software",
            "tasks": ["one"],
            "stages": ["design"],
            "relations": [],
            "evidence": [],
        },
        {
            "id": "c",
            "kind": "model",
            "tasks": ["two"],
            "stages": ["design"],
            "relations": [],
            "evidence": [],
        },
        {
            "id": "d",
            "kind": "model",
            "tasks": ["other"],
            "stages": [],
            "relations": [],
            "evidence": [],
        },
    ]
    graph = build_graph(records, ("model", "software"), ("uses",))
    result = analyze(graph)
    assert result["candidate_edges"] == [("b", "c")]
    assert result["candidate_edge_count"] == 1
    assert result["isolated_nodes"] == {"model": ["c", "d"], "software": ["b"]}
    assert result["node_counts_by_kind"] == {"model": 3, "software": 1}
    assert result["edge_counts_by_type"] == {"uses": 1}
    assert result["degree"] == {"a": 1, "b": 1, "c": 0, "d": 0}
    assert len(result["evidenced_edges"]) == 1
    assert result["unevidenced_edges"] == []
    assert check_invariants(graph, result, expected_nodes=4, edge_types=("uses",)) == []


def test_current_catalogue_aggregates() -> None:
    graph = build_graph(load_catalogue(ROOT / "catalog/resources"), NODE_TYPES, EDGE_TYPES)
    result = analyze(graph)
    assert result["node_count"] == 228
    assert result["edge_count"] == 39
    assert result["candidate_edge_count"] == 10100
    assert len(result["evidenced_edges"]) == 39
    assert len(result["unevidenced_edges"]) == 0
    assert sum(map(len, result["isolated_nodes"].values())) == 192
    assert check_invariants(graph, result, expected_nodes=228, edge_types=EDGE_TYPES) == []
