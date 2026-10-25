"""Write the small, committed public summary from the cached, validated data.

    python labs/l1000_perturbation_context/export_summary.py

Reads `.cache/l1000_perturbation_context/` (see `run_lab.py download`) and
writes `labs/l1000_perturbation_context/summary.json`. Contains only counts,
audits, the matched-versus-null distribution summary, the rank-sum test and
a fixed number of named examples; no raw expression vectors, instance rows
or bulk compound lists.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import h5py  # noqa: E402
import numpy  # noqa: E402
import rdkit  # noqa: E402
import scipy  # noqa: E402
from aidd_commons.l1000_perturbation_context.data import DataContractError  # noqa: E402
from aidd_commons.l1000_perturbation_context.summary import build_summary_from_cache  # noqa: E402

LAB = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = LAB.parents[1] / ".cache/l1000_perturbation_context"
OUTPUT_PATH = LAB / "summary.json"


def main() -> int:
    try:
        summary = build_summary_from_cache(
            DEFAULT_CACHE_DIR,
            computed_on=date.today().isoformat(),
            software={
                "python": platform.python_version(),
                "numpy": numpy.__version__,
                "scipy": scipy.__version__,
                "rdkit": rdkit.__version__,
                "h5py": h5py.__version__,
            },
        )
    except DataContractError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    OUTPUT_PATH.write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
