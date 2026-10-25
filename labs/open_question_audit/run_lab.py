"""Verify that the three committed audit inputs are present; no download occurs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.open_question_audit.protocol import load_protocol, load_sources  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        load_sources(ROOT, protocol)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "PASS: all three committed inputs are present and readable; nothing downloaded or written"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
