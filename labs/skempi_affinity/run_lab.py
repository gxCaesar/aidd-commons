"""Download and cache the frozen SKEMPI mirror snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.skempi_affinity.data import download_and_cache  # noqa: E402
from aidd_commons.skempi_affinity.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/skempi_affinity"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("download")
    args = parser.parse_args()
    if args.action != "download":
        return 2
    try:
        load_protocol(LAB / "protocol.json")
        path = download_and_cache(DEFAULT_CACHE)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"cached_bytes={path.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
