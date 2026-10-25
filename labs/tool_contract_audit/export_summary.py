"""Write the compact audit summary after all local checks pass."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.tool_contract_audit.summary import export_summary  # noqa: E402

LAB = Path(__file__).resolve().parent


def main() -> int:
    try:
        export_summary(LAB, LAB.parent, LAB / "summary.json")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print("Wrote summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
