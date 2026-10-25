"""Reuse and validate the three existing snapshots without fetching or writing data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.multi_endpoint_integration.protocol import load_protocol_document  # noqa: E402
from aidd_commons.multi_endpoint_integration.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download"])
    parser.add_argument("--cache-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    try:
        load_protocol_document(LAB / "protocol.json")
        summary = build_summary(args.cache_root)
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        "Validated the existing ChEMBL 37 snapshots without network or writes. "
        f"Measured-family compounds: {summary['counts']['cohort_compound_count']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
