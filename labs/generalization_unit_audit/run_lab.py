"""Copy the validated local ChEMBL 37 snapshot into this laboratory's cache."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import load_cached_cohort  # noqa: E402
from aidd_commons.generalization_unit_audit.protocol import (  # noqa: E402
    expected_fields,
    load_protocol,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/generalization_unit_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def download(cache_dir: Path) -> str:
    """Validate source first, copy only frozen artifacts, then validate the copy."""
    load_protocol(LAB / "protocol.json")
    load_cached_cohort(SIBLING_CACHE)
    cache_dir.mkdir(parents=True, exist_ok=True)
    for artifact in expected_fields()["artifacts"]:
        name = artifact["path"]
        source = SIBLING_CACHE / name
        target = cache_dir / name
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            shutil.copyfile(source, target)
    load_cached_cohort(cache_dir)
    return "reused the validated local ChEMBL 37 snapshot"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        print(download(args.cache_dir))
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
