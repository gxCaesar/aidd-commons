"""Recompute the compact summary from validated committed sources."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.source_review_scope_audit.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    try:
        summary = build_summary(
            ROOT,
            LAB / "protocol.json",
            software={"python": platform.python_version(), "pyyaml": yaml.__version__},
            output=LAB / "summary.json",
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"summary_bytes={(LAB / 'summary.json').stat().st_size}")
    print(f"examined_records={len(summary['examined_record_ids'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
