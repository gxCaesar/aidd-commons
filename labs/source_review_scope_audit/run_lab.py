"""Verify frozen catalogue membership without writing output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.source_review_scope_audit.protocol import (  # noqa: E402
    EXAMINED_IDS,
    load_protocol,
)
from aidd_commons.source_review_scope_audit.records import load_catalogue  # noqa: E402

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
