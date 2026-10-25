"""Write the small, committed public summary from the cached, validated data.

    python labs/rosetta_cross_modality/export_summary.py

Reads `.cache/rosetta_cross_modality/` (see `run_lab.py download`) and writes
two files. `labs/rosetta_cross_modality/results/computed-summary.json` is the
full run artefact, including the agreement value of every individual
perturbation; it is git-ignored and is not part of the committed record.
`labs/rosetta_cross_modality/summary.json` is the small committed projection:
counts, the variance attribution of plate and batch, the frozen evaluation
set, the survival ratios and a fixed number of named examples, with no raw
well rows, no per-perturbation values and no bulk lists of perturbation
identifiers.
"""

from __future__ import annotations

import platform
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np  # noqa: E402
from aidd_commons.rosetta_cross_modality.data import DataContractError  # noqa: E402
from aidd_commons.rosetta_cross_modality.protocol import (  # noqa: E402
    ContractError,
    load_contract,
)
from aidd_commons.rosetta_cross_modality.summary import export_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = LAB.parents[1] / ".cache/rosetta_cross_modality"
RESULTS_DIR = LAB / "results"
COMMITTED_PATH = LAB / "summary.json"


def main() -> int:
    try:
        contract = load_contract(LAB / "protocol.json")
        export_summary(
            contract,
            DEFAULT_CACHE_DIR,
            RESULTS_DIR,
            COMMITTED_PATH,
            computed_on=date.today().isoformat(),
            software={
                "python": platform.python_version(),
                "numpy": np.__version__,
            },
        )
    except (ContractError, DataContractError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"Wrote {RESULTS_DIR / 'computed-summary.json'}")
    print(f"Wrote {COMMITTED_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
