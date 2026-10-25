"""Count graph structure without promoting missing links to facts."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

from .graph import Edge, TypedGraph


class AuditError(ValueError):
    """The measured graph violates the declared audit contract."""


def analyze(graph: TypedGraph) -> dict[str, Any]:
    kinds = Counter(node.kind for node in graph.nodes.values())
    types = Counter(edge.type for edge in graph.edges)
    isolated: dict[str, list[str]] = {
        kind: sorted(
            node.id
            for node in graph.nodes.values()
            if node.kind == kind and not node.declares_relation
        )
        for kind in sorted(kinds)
    }
    evidenced = [edge for edge in graph.edges if edge.evidence_ids]
    unevidenced = [edge for edge in graph.edges if not edge.evidence_ids]
    degree: Counter[str] = Counter({identifier: 0 for identifier in graph.nodes})
    for edge in graph.edges:
        degree[edge.source] += 1
        degree[edge.target] += 1
    related_pairs = {frozenset((edge.source, edge.target)) for edge in graph.edges}
    candidates: list[tuple[str, str]] = []
    candidate_degree: Counter[str] = Counter()
    for left, right in combinations(sorted(graph.nodes), 2):
        first, second = graph.nodes[left], graph.nodes[right]
        if frozenset((left, right)) in related_pairs:
            continue
        if first.tasks & second.tasks or first.stages & second.stages:
            candidates.append((left, right))
            candidate_degree[left] += 1
            candidate_degree[right] += 1
    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "node_counts_by_kind": {kind: kinds[kind] for kind in sorted(kinds)},
        "edge_counts_by_type": {edge_type: types[edge_type] for edge_type in sorted(types)},
        "isolated_nodes": isolated,
        "evidenced_edges": evidenced,
        "unevidenced_edges": unevidenced,
        "candidate_edges": candidates,
        "candidate_edge_count": len(candidates),
        "highest_candidate_nodes": sorted(
            candidate_degree.items(), key=lambda item: (-item[1], item[0])
        )[:10],
        "degree": dict(sorted(degree.items())),
        "highest_degree_nodes": sorted(degree.items(), key=lambda item: (-item[1], item[0]))[:10],
    }


def edge_row(edge: Edge) -> dict[str, Any]:
    return {
        "source": edge.source,
        "type": edge.type,
        "target": edge.target,
        "evidence_ids": list(edge.evidence_ids),
    }


def check_invariants(
    graph: TypedGraph, result: dict[str, Any], *, expected_nodes: int, edge_types: tuple[str, ...]
) -> list[str]:
    failures: list[str] = []
    if result["node_count"] != expected_nodes:
        failures.append(f"node count is {result['node_count']}, expected {expected_nodes}")
    if set(result["edge_counts_by_type"]) != set(edge_types):
        failures.append("catalogue edge types differ from frozen protocol")
    if sum(result["node_counts_by_kind"].values()) != result["node_count"]:
        failures.append("node kind counts do not cover all nodes")
    if sum(result["edge_counts_by_type"].values()) != result["edge_count"]:
        failures.append("edge type counts do not cover all edges")
    if len(result["evidenced_edges"]) + len(result["unevidenced_edges"]) != result["edge_count"]:
        failures.append("provenance counts do not cover all edges")
    for edge in result["unevidenced_edges"]:
        failures.append(f"unevidenced edge: {edge.source} {edge.type} {edge.target}")
    if sum(result["degree"].values()) != 2 * result["edge_count"]:
        failures.append("total degree does not equal twice the edge count")
    if result["candidate_edge_count"] != len(result["candidate_edges"]):
        failures.append("candidate count differs from enumerated pairs")
    if len(set(result["candidate_edges"])) != result["candidate_edge_count"]:
        failures.append("candidate pairs repeat")
    if len(graph.nodes) != result["node_count"]:
        failures.append("analysis omits graph nodes")
    return failures
