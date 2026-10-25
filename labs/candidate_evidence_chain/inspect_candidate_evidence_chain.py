"""Show candidate chains or check the committed summary against cached evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.candidate_evidence_chain.protocol import load_protocol_document  # noqa: E402
from aidd_commons.candidate_evidence_chain.summary import (  # noqa: E402
    build_summary,
    check_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def show(summary: dict[str, Any]) -> None:
    for chain in summary["chains"]:
        print(chain["parent_chembl_id"])
        for link in chain["links"]:
            print(f"  {link['name']}: {link['state']}")
            if link["measurements"]:
                print(f"    source: {link['source']}; scope: {link['scope']}")
                for measurement in link["measurements"]:
                    print(f"    {json.dumps(measurement, ensure_ascii=False)}")
        print(f"  counts: {json.dumps(chain['counts'])}")
        print(f"  first non-measured link: {chain['first_non_measured']}")
        print(
            f"  supports claim: {chain['supports_claim']}; bounded claim: {chain['bounded_claim']}"
        )
    print(f"First-stop distribution: {json.dumps(summary['first_non_measured_distribution'])}")
    print(summary["boundary_statement"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    try:
        load_protocol_document(LAB / "protocol.json")
        computed = build_summary(args.cache_root)
        if args.action == "show":
            show(computed)
        else:
            committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
            check_summary(committed, computed)
            print("PASS: protocol, cached compound chains and committed summary agree")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
