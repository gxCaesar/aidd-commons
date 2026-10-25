"""Fetch and validate the eight frozen OpenFE archives."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.free_energy_network_audit.summary import download_snapshots  # noqa: E402

LAB = Path(__file__).resolve().parent
DEFAULT_CACHE = LAB.parents[1] / ".cache/free_energy_network_audit"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        reports = download_snapshots(LAB / "protocol.json", args.cache_dir)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    for report in reports:
        print(f"{report['system']}\t{report['origin']}\t{report['bytes']} bytes\t{report['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
