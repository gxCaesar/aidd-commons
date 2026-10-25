"""Fetch and cache the real ChEMBL 37 snapshot this lab counts.

    python labs/decision_unit_scope/run_lab.py download

Writes the ChEMBL status payload, the fifteen declared seed molecule records,
the activity rows of the ten parent molecules they resolve to, and the assay
records behind every admitted row, under `.cache/decision_unit_scope/`. The
download is resumable: an artefact whose cached byte length still matches the
frozen value is kept and not fetched again. The ChEMBL status endpoint is
always contacted, because the live release assertion is the point of the
check. This script aggregates and analyses nothing; use
`inspect_decision_unit_scope.py` for that.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
)
from aidd_commons.decision_unit_scope.protocol import (  # noqa: E402
    ProtocolContractError,
    load_protocol_document,
)

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = Path(".cache/decision_unit_scope")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and cache the real ChEMBL 37 snapshot this lab counts."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    download = subparsers.add_parser(
        "download", help="fetch and validate the declared ChEMBL 37 cohort"
    )
    download.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    return parser.parse_args(argv)


def _resolve_repository_path(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cache_dir = _resolve_repository_path(args.cache_dir)
    try:
        load_protocol_document(LAB / "protocol.json")
    except ProtocolContractError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    try:
        report = download_and_cache_snapshot(cache_dir)
    except (DataContractError, DataDownloadError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"Cache under {cache_dir}: {report.describe()}")
    for path in report.paths:
        state = "fetched" if path.name in report.fetched else "reused"
        print(f"  {path.name}: {path.stat().st_size} bytes ({state})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
