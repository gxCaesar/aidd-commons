"""Recompute and write the compact summary only after checks pass."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

import numpy
import rdkit
import sklearn

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.applicability_domain_audit.protocol import load_protocol  # noqa: E402
from aidd_commons.applicability_domain_audit.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    try:
        protocol = load_protocol(LAB / "protocol.json")
        build_summary(
            LAB / "protocol.json",
            ROOT / protocol["source"]["path"],
            software={
                "python": platform.python_version(),
                "rdkit": rdkit.__version__,
                "numpy": numpy.__version__,
                "scikit_learn": sklearn.__version__,
            },
            output=LAB / "summary.json",
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"summary_bytes={(LAB / 'summary.json').stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
