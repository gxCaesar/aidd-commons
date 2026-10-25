"""Validate the frozen selection and the comparison record's declared counts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.claims_evidence_audit.analysis import analyze, check_invariants  # noqa: E402
from aidd_commons.claims_evidence_audit.protocol import load_protocol  # noqa: E402
from aidd_commons.claims_evidence_audit.records import load_sources  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check",))
    parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        result = analyze(load_sources(ROOT, protocol), protocol, ROOT)
        failures = check_invariants(result, protocol)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    counts = result["source_counts"]
    print(
        f"PASS: {counts['total_cells']} cells = {counts['direct_cells']} direct + "
        f"{counts['default_unverified_cells']} defaults"
    )
    print(
        f"PASS: {len(protocol['provider_ids'])} providers and "
        f"{len(protocol['track']['topic_ids'])} declared track topics"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
