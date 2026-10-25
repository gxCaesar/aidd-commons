"""Export the small summary only after all frozen-contract checks pass."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import DataContractError  # noqa: E402
from aidd_commons.multi_endpoint_tradeoff.protocol import ProtocolContractError  # noqa: E402
from aidd_commons.multi_endpoint_tradeoff.summary import (  # noqa: E402
    SummaryContractError,
    export_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/multi_endpoint_tradeoff")
    args = parser.parse_args()
    try:
        export_summary(LAB, args.cache_dir, LAB / "summary.json")
    except (ProtocolContractError, DataContractError, SummaryContractError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"Wrote {LAB / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
