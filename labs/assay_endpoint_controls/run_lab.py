"""Fetch and cache the declared PubChem BioAssay records.

    python labs/assay_endpoint_controls/run_lab.py download

Writes one archived result CSV and one archived description XML per declared
assay under `.cache/assay_endpoint_controls/`. Each file is a single gzip
member inside a ranged container zip on the PubChem FTP site; the reader
locates the container's central directory with HTTP byte-range requests and
reads only the declared member, so the 1,313,522,439-byte container that
holds assay 1277 is never downloaded in full.

The download is resumable. A cache file that already holds exactly the frozen
byte length is left alone and is not fetched again, and a file being written
is written through a `.part` name, so an interrupted run leaves either the
previous file or the new one and never a truncated file. Every run re-reads
the cached bytes and re-checks their length against the frozen protocol.

This does not analyse anything. Use `inspect_assay_endpoint_controls.py` for
that.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.assay_endpoint_controls.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
    download_and_cache_assays,
)
from aidd_commons.assay_endpoint_controls.protocol import ASSAYS, DECLARED_ASSAYS  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = Path(".cache/assay_endpoint_controls")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and cache the declared PubChem BioAssay assay records."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    download = subparsers.add_parser(
        "download", help="read the declared members out of the ranged container zips"
    )
    download.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    return parser.parse_args(argv)


def _resolve_repository_path(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cache_dir = _resolve_repository_path(args.cache_dir)
    try:
        paths = download_and_cache_assays(cache_dir)
    except (DataContractError, DataDownloadError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    total = 0
    for aid in DECLARED_ASSAYS:
        spec = ASSAYS[aid]
        print(
            f"assay {aid}: {spec.source_data.member} "
            f"({spec.source_data.record_bytes} bytes) and "
            f"{spec.source_description.member} "
            f"({spec.source_description.record_bytes} bytes)"
        )
        total += spec.source_data.record_bytes + spec.source_description.record_bytes
    print(f"Cached {len(paths)} files under {cache_dir}")
    print(f"Total archived bytes cached: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
