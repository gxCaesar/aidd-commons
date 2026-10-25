"""Show parent-level profile outcomes or audit the committed result."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.target_product_profile.protocol import load_protocol_document  # noqa: E402
from aidd_commons.target_product_profile.summary import check_summary, compute  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def show(summary: dict[str, Any], evaluations: list[dict[str, Any]]) -> None:
    print("Profile declared before the measurements were read")
    print(json.dumps(summary["profile"], indent=2, ensure_ascii=False))
    print("Per-parent mandatory gate and preference outcomes")
    for row in evaluations:
        print(json.dumps(row, ensure_ascii=False))
    print("Counts and contradictions")
    print(json.dumps(summary["counts"], indent=2))
    print(json.dumps(summary["per_gate"], indent=2))
    print(json.dumps(summary["per_preference"], indent=2))
    print("Unmeasured requirements:", ", ".join(summary["unmeasured_requirements"]))
    if summary["no_contradictions_note"]:
        print(summary["no_contradictions_note"])
    print(summary["boundary_statement"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    try:
        load_protocol_document(LAB / "protocol.json")
        summary, evaluations = compute(args.cache_root)
        if args.action == "check":
            committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
            check_summary(committed, summary)
            print("PASS: frozen profile, cached measurements and committed summary agree")
        else:
            show(summary, evaluations)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
