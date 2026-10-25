"""Build a compact projection only after the graph contract passes."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .analysis import AuditError, analyze, check_invariants
from .graph import build_graph, load_catalogue
from .protocol import EDGE_TYPES, EXPECTED_NODE_COUNT, NODE_TYPES, load_protocol

SCHEMA_VERSION = "aidd-commons.relational-graph-audit-summary.v1"


def build_summary(
    protocol_path: Path,
    catalogue_dir: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    graph = build_graph(load_catalogue(catalogue_dir), NODE_TYPES, EDGE_TYPES)
    result = analyze(graph)
    failures = check_invariants(
        graph, result, expected_nodes=EXPECTED_NODE_COUNT, edge_types=EDGE_TYPES
    )
    if failures:
        raise AuditError("; ".join(failures))
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or {},
        "node_count": result["node_count"],
        "edge_count": result["edge_count"],
        "node_counts_by_kind": result["node_counts_by_kind"],
        "edge_counts_by_type": result["edge_counts_by_type"],
        "isolated_nodes": result["isolated_nodes"],
        "evidenced_edge_count": len(result["evidenced_edges"]),
        "unevidenced_edge_count": len(result["unevidenced_edges"]),
        "candidate_edge_count": result["candidate_edge_count"],
        "highest_candidate_nodes": [list(item) for item in result["highest_candidate_nodes"]],
        "highest_degree_nodes": [list(item) for item in result["highest_degree_nodes"]],
    }
    if output is not None:
        output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary
