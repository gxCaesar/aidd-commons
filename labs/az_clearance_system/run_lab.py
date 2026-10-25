"""Fetch and cache the real ChEMBL 37 AZ intrinsic-clearance snapshot.

    python labs/az_clearance_system/run_lab.py download

Writes `status.json` and one `activities-<assay>.json` per assay under
`.cache/az_clearance_system/`. Re-running is safe: it always re-fetches and
re-validates against the frozen ChEMBL release fields in `protocol.py`, so a
cache written under an older admission rule is re-checked, not silently
trusted. This does not aggregate or analyse anything; use
`inspect_az_clearance_system.py` for that.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.az_clearance_system.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = Path(".cache/az_clearance_system")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and cache the real ChEMBL 37 AZ intrinsic-clearance snapshot."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    download = subparsers.add_parser(
        "download", help="fetch and validate the official ChEMBL 37 activity pages"
    )
    download.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    return parser.parse_args(argv)


def _resolve_repository_path(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cache_dir = _resolve_repository_path(args.cache_dir)
    try:
        paths = download_and_cache_snapshot(cache_dir)
    except (DataContractError, DataDownloadError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"Cached {len(paths)} files under {cache_dir}")
    for path in paths:
        print(f"  {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
