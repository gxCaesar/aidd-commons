"""Fetch and cache the real LINCS L1000 GSE70138 snapshot this lab reads.

    python labs/l1000_perturbation_context/run_lab.py download

Writes five files under `.cache/l1000_perturbation_context/`: instance,
cell, gene and perturbagen metadata, and the Level 2 (directly measured,
978-landmark-gene) expression matrix for GEO series GSE70138. This is a
real download of about 640 MiB; re-running is safe and re-validates every
file's size against the frozen protocol, so a cache written under an older
admission rule is re-checked, not silently trusted.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.l1000_perturbation_context.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = Path(".cache/l1000_perturbation_context")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and cache the real LINCS L1000 GSE70138 snapshot."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    download = subparsers.add_parser(
        "download", help="fetch and validate the official GEO GSE70138 files"
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
