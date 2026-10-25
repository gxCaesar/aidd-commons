"""Validate the owning ChEMBL snapshots without downloading or writing data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.crossdomain_tradeoff.protocol import load_protocol_document  # noqa: E402
from aidd_commons.crossdomain_tradeoff.summary import build_summary  # noqa: E402

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
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    count = len(summary["decisions"])
    print(f"Validated cached evidence for {count} cross-domain decisions without writes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
