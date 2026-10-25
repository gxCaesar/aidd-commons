"""Write the small, committed public summary from the cached, validated data.

    python labs/assay_endpoint_controls/export_summary.py

Reads `.cache/assay_endpoint_controls/` (see `run_lab.py download`) and writes
`labs/assay_endpoint_controls/summary.json`. The summary holds counts,
distributions, the control audit of every declared assay, the
concentration-response check and a fixed number of named examples with their
raw per-concentration values. It holds no bulk compound list and no archived
row beyond those named examples.
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
from aidd_commons.assay_endpoint_controls.data import DataContractError  # noqa: E402
from aidd_commons.assay_endpoint_controls.summary import build_summary_from_cache  # noqa: E402

LAB = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = LAB.parents[1] / ".cache/assay_endpoint_controls"
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
