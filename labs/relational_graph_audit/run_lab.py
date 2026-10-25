"""Check the frozen graph protocol against every committed catalogue record."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.relational_graph_audit.analysis import analyze, check_invariants  # noqa: E402
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
    parser.add_argument("action", choices=("check",))
    parser.parse_args()
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
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print(f"PASS: {result['node_count']} nodes and {result['edge_count']} directed edges")
    print(f"PASS: catalogue uses exactly {len(EDGE_TYPES)} declared edge types")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
