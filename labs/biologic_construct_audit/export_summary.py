"""Export the compact summary after source and definition checks pass."""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.biologic_construct_audit.summary import export_summary  # noqa: E402

LAB = Path(__file__).resolve().parent


def main() -> int:
    try:
        result = export_summary(LAB, LAB / "summary.json")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"Wrote summary.json for {result['entity_count']} therapeutic entities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
