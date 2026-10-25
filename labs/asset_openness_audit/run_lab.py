"""Check declared record membership and review dates without writing output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.asset_openness_audit.protocol import EXAMINED_IDS, load_protocol  # noqa: E402
from aidd_commons.asset_openness_audit.records import load_catalogue  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check",))
    parser.parse_args()
    try:
        load_protocol(LAB / "protocol.json")
        catalogue = load_catalogue(ROOT / "catalog/resources", EXAMINED_IDS)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(EXAMINED_IDS)} declared records found in {len(catalogue)} catalogue records")
    print("PASS: every examined last_verified is a calendar date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
