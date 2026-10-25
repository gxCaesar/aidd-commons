"""Download the frozen ChEMBL 37 snapshot into this laboratory's own cache."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
)
from aidd_commons.multi_endpoint_tradeoff.protocol import (  # noqa: E402
    ProtocolContractError,
    load_protocol_document,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download"])
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/multi_endpoint_tradeoff")
    args = parser.parse_args()
    try:
        load_protocol_document(LAB / "protocol.json")
        report = download_and_cache_snapshot(args.cache_dir)
    except (ProtocolContractError, DataContractError, DataDownloadError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(report.describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
