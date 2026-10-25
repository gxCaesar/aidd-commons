"""Write the small, committed public summary from the cached, validated data.

    python labs/cyp_assay_system/export_summary.py

Reads `.cache/cyp_assay_system/` (see `run_lab.py download`) and writes
`labs/cyp_assay_system/summary.json`. Contains only counts, audits, the two
correlation summaries and a fixed number of named divergent examples; no raw
activity rows or bulk compound lists.
"""

from __future__ import annotations

import platform
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy  # noqa: E402
import rdkit  # noqa: E402
import scipy  # noqa: E402
from aidd_commons.cyp_assay_system.data import DataContractError  # noqa: E402
from aidd_commons.cyp_assay_system.summary import build_summary_from_cache  # noqa: E402

LAB = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = LAB.parents[1] / ".cache/cyp_assay_system"
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
            },
        )
    except DataContractError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    import json

    OUTPUT_PATH.write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
