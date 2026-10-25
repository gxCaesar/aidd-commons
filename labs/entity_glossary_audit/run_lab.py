"""Copy a validated ChEMBL 37 snapshot into this laboratory's cache."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import (  # noqa: E402
    DataContractError,
    load_cached_cohort,
)
from aidd_commons.entity_glossary_audit.protocol import (  # noqa: E402
    ProtocolError,
    expected_fields,
    load_protocol,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/entity_glossary_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def download(cache_dir: Path) -> str:
    """Validate the source before copying and validate the resulting copy."""
    load_protocol(LAB / "protocol.json")
    load_cached_cohort(SIBLING_CACHE)
    if cache_dir == SIBLING_CACHE:
        return "validated the existing ChEMBL 37 snapshot"
    cache_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for artifact in expected_fields()["artifacts"]:
        name = artifact["path"]
        source = SIBLING_CACHE / name
        target = cache_dir / name
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            shutil.copyfile(source, target)
            copied += 1
    load_cached_cohort(cache_dir)
    return f"validated and reused ChEMBL 37 snapshot; copied {copied} artefacts"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        print(download(args.cache_dir))
    except (DataContractError, ProtocolError, OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
