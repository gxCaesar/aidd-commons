"""Verify that the committed laboratory return records are present."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.tool_contract_audit.analysis import load_records  # noqa: E402
from aidd_commons.tool_contract_audit.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
LABS = LAB.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        records = load_records(
            LABS, protocol["source"], exclude=protocol["source"]["exclude_laboratory"]
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"verified_local_return_records={len(records)}; download=none; wrote=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
