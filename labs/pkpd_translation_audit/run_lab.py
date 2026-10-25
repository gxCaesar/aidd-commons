"""Validate and reuse the existing ChEMBL clearance cache without writing it."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.az_clearance_system.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
)
from aidd_commons.pkpd_translation_audit.analysis import (  # noqa: E402
    AnalysisError,
    load_from_cache,
)
from aidd_commons.pkpd_translation_audit.protocol import (  # noqa: E402
    ProtocolError,
    load_protocol,
)

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download"])
    args = parser.parse_args()
    assert args.action == "download"
    try:
        protocol = load_protocol(LAB / "protocol.json")
        datasets = load_from_cache(ROOT / ".cache/az_clearance_system", protocol["source"])
    except (ProtocolError, AnalysisError, DataContractError, DataDownloadError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print("Reused and validated cached ChEMBL 37 clearance snapshot, no files written")
    for assay_id, dataset in sorted(datasets.items()):
        print(f"{assay_id}: {len(dataset.records)} admitted parents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
