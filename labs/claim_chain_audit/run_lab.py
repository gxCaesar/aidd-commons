"""Verify that the three committed audit inputs are present; no download occurs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.claim_chain_audit.analysis import load_records  # noqa: E402
from aidd_commons.claim_chain_audit.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        load_records(ROOT, protocol)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: three committed audit inputs are present; nothing downloaded or written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
