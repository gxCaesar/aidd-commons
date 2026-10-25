"""Write the small, committed public summary from the cached, validated data.

    python labs/decision_unit_scope/export_summary.py

Reads `.cache/decision_unit_scope/` (see `run_lab.py download`) and writes
`labs/decision_unit_scope/summary.json`. Contains only counts, audits and a
fixed number of named examples; no raw activity rows, no structures and no
bulk compound list. The file is overwritten in place, and it is a derived
artefact: rerunning this script on the same cache reproduces it exactly.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import DataContractError  # noqa: E402
from aidd_commons.decision_unit_scope.pipeline import run_census_export  # noqa: E402
from aidd_commons.decision_unit_scope.protocol import ProtocolContractError  # noqa: E402

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / ".cache/decision_unit_scope"
OUTPUT_PATH = LAB / "summary.json"


def main() -> int:
    try:
        run_census_export(LAB, DEFAULT_CACHE_DIR, OUTPUT_PATH)
    except (DataContractError, ProtocolContractError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
