"""Copy the two locally validated source snapshots into this lab's cache."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.assay_endpoint_controls.data import (  # noqa: E402
    DataContractError as AssayDataError,
)
from aidd_commons.assay_endpoint_controls.data import load_cached_assays  # noqa: E402
from aidd_commons.assay_endpoint_controls.protocol import DECLARED_ASSAYS  # noqa: E402
from aidd_commons.decision_unit_scope.data import (  # noqa: E402
    DataContractError as ChemblDataError,
)
from aidd_commons.decision_unit_scope.data import load_cached_cohort  # noqa: E402
from aidd_commons.decision_unit_scope.protocol import expected_artifacts  # noqa: E402
from aidd_commons.functional_validation_audit.protocol import load_protocol  # noqa: E402
from aidd_commons.functional_validation_audit.records import load_tables  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/functional_validation_audit"
CHEMBL_SOURCE = ROOT / ".cache/decision_unit_scope"
PUBCHEM_SOURCE = ROOT / ".cache/assay_endpoint_controls"


def download(cache_dir: Path) -> str:
    """Reuse local validated bytes only; this action never makes a network request."""
    load_protocol(LAB / "protocol.json")
    load_cached_cohort(CHEMBL_SOURCE)
    load_cached_assays(PUBCHEM_SOURCE)
    destinations = (
        (
            CHEMBL_SOURCE,
            cache_dir / "chembl37",
            [item["path"] for item in expected_artifacts()],
        ),
        (
            PUBCHEM_SOURCE,
            cache_dir / "pubchem_bioassay",
            [name for aid in DECLARED_ASSAYS for name in (f"aid{aid}.csv", f"aid{aid}.descr.xml")],
        ),
    )
    for source, target_dir, names in destinations:
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            source_path = source / name
            target = target_dir / name
            if not target.is_file() or not filecmp.cmp(source_path, target, shallow=False):
                shutil.copyfile(source_path, target)
    load_tables(cache_dir / "chembl37", cache_dir / "pubchem_bioassay")
    return "reused both validated local snapshots; no network request"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        print(download(args.cache_dir))
    except (AssayDataError, ChemblDataError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
