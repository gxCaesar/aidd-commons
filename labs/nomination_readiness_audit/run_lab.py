"""Copy the validated ChEMBL 37 snapshot into this laboratory's cache."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
    load_cached_cohort,
)
from aidd_commons.nomination_readiness_audit.protocol import (  # noqa: E402
    ProtocolError,
    expected_fields,
    load_protocol,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/nomination_readiness_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def download(cache_dir: Path) -> str:
    load_protocol(LAB / "protocol.json")
    if SIBLING_CACHE.is_dir() and cache_dir != SIBLING_CACHE:
        load_cached_cohort(SIBLING_CACHE)
        cache_dir.mkdir(parents=True, exist_ok=True)
        for artifact in expected_fields()["artifacts"]:
            name = artifact["path"]
            source = SIBLING_CACHE / name
            target = cache_dir / name
            if not target.is_file() or target.stat().st_size != artifact["byte_length"]:
                shutil.copyfile(source, target)
        load_cached_cohort(cache_dir)
        return "reused the validated local ChEMBL 37 snapshot"
    report = download_and_cache_snapshot(cache_dir)
    load_cached_cohort(cache_dir)
    return report.describe()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        message = download(args.cache_dir)
    except (DataContractError, DataDownloadError, ProtocolError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
