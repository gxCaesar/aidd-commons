"""Show parallel parent profiles or check the committed summary against the caches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.multi_endpoint_integration.protocol import load_protocol_document  # noqa: E402
from aidd_commons.multi_endpoint_integration.summary import (  # noqa: E402
    build_summary,
    check_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def show(summary: dict[str, Any]) -> None:
    print("Family coverage matrix, counted by ChEMBL parent molecule")
    for group, count in summary["family_coverage_matrix"].items():
        print(f"  {group}: {count}")
    print("Counts")
    print(json.dumps(summary["counts"], indent=2))
    print("Per-compound profiles with at least two measured families")
    for profile in summary["profiles"]:
        print(json.dumps(profile, ensure_ascii=False))
    print(summary["boundary_statement"])
    print(summary["rules"]["composite_score"])
    print(summary["rules"]["missing_family"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    try:
        load_protocol_document(LAB / "protocol.json")
        computed = build_summary(args.cache_root)
        if args.action == "check":
            committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
            check_summary(committed, computed)
            print("PASS: frozen protocol, cached records and committed summary agree")
        else:
            show(computed)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
