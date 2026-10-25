"""Fetch and cache the ROSETTA cross-modality objects this lab reads.

    python labs/rosetta_cross_modality/run_lab.py download

Writes two files under `.cache/rosetta_cross_modality/`: the replicate-level
L1000 transcriptomic release and the replicate-level Cell Painting imaging
release of the LUAD batch of the ROSETTA study. This is a real download of
about 26 MiB. Re-running is safe: a cache that already has the right size is
left alone, and a download that was interrupted resumes from the bytes
already on disk.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.rosetta_cross_modality.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
)
from aidd_commons.rosetta_cross_modality.protocol import (  # noqa: E402
    ContractError,
    load_contract,
)

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = Path(".cache/rosetta_cross_modality")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and cache the published ROSETTA cross-modality objects."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    download = subparsers.add_parser(
        "download", help="fetch and validate the two published objects"
    )
    download.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    return parser.parse_args(argv)


def _resolve_repository_path(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cache_dir = _resolve_repository_path(args.cache_dir)
    try:
        contract = load_contract(LAB / "protocol.json")
        paths = download_and_cache_snapshot(cache_dir, contract)
    except (ContractError, DataContractError, DataDownloadError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    total = 0
    print(f"Cached {len(paths)} files under {cache_dir}")
    for path in paths:
        source = next(item for item in contract.files if item.filename == path.name)
        size = path.stat().st_size
        total += size
        print(f"  {path.name}: {size} bytes (the contract declares {source.byte_length})")
    print(f"Total bytes read: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
