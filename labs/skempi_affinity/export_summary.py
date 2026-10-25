"""Recompute the small public summary from the validated local snapshot."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.skempi_affinity.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/skempi_affinity"


def main() -> int:
    try:
        summary = build_summary(
            LAB / "protocol.json",
            DEFAULT_CACHE,
            software={"python": platform.python_version()},
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    path = LAB / "summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"summary_bytes={path.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
