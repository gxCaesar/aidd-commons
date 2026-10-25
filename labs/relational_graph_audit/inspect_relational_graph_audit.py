"""Show graph shape or check every relation and candidate-edge invariant."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.relational_graph_audit.analysis import (  # noqa: E402
    analyze,
    check_invariants,
    edge_row,
)
from aidd_commons.relational_graph_audit.graph import build_graph, load_catalogue  # noqa: E402
from aidd_commons.relational_graph_audit.protocol import (  # noqa: E402
    EDGE_TYPES,
    EXPECTED_NODE_COUNT,
    NODE_TYPES,
    load_protocol,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        load_protocol(LAB / "protocol.json")
        graph = build_graph(load_catalogue(ROOT / "catalog/resources"), NODE_TYPES, EDGE_TYPES)
        result = analyze(graph)
        failures = check_invariants(
            graph, result, expected_nodes=EXPECTED_NODE_COUNT, edge_types=EDGE_TYPES
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if action == "show":
        print(
            json.dumps(
                {
                    "node_count": result["node_count"],
                    "edge_count": result["edge_count"],
                    "node_counts_by_kind": result["node_counts_by_kind"],
                    "edge_counts_by_type": result["edge_counts_by_type"],
                    "isolated_nodes": result["isolated_nodes"],
                    "evidenced_edge_count": len(result["evidenced_edges"]),
                    "unevidenced_edge_count": len(result["unevidenced_edges"]),
                    "evidenced_edges": [edge_row(edge) for edge in result["evidenced_edges"]],
                    "unevidenced_edges": [edge_row(edge) for edge in result["unevidenced_edges"]],
                    "candidate_edge_count": result["candidate_edge_count"],
                    "highest_candidate_nodes": result["highest_candidate_nodes"],
                    "highest_degree_nodes": result["highest_degree_nodes"],
                },
                ensure_ascii=False,
            )
        )
        for node in graph.nodes.values():
            print(
                json.dumps(
                    {"node": node.id, "kind": node.kind, "degree": result["degree"][node.id]}
                )
            )
        print("Candidate pairs are undeclared, not predicted relations.")
        print("Graph paths are not mechanisms.")
    for failure in failures:
        print(f"FAIL: {failure}")
    if action == "check":
        print(f"invariants={len(failures)} failure(s)")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
