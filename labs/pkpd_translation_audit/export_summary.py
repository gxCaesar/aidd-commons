"""Recompute checked results and write the committed summary only on success."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.az_clearance_system.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
)
from aidd_commons.pkpd_translation_audit.analysis import AnalysisError  # noqa: E402
from aidd_commons.pkpd_translation_audit.model import ModelError  # noqa: E402
from aidd_commons.pkpd_translation_audit.protocol import ProtocolError  # noqa: E402
from aidd_commons.pkpd_translation_audit.summary import (  # noqa: E402
    SummaryError,
    build_summary,
)

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent


def export(protocol_path: Path, cache_dir: Path, output_path: Path) -> None:
    summary = build_summary(protocol_path, cache_dir)
    output_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        export(LAB / "protocol.json", ROOT / ".cache/az_clearance_system", LAB / "summary.json")
    except (
        ProtocolError,
        AnalysisError,
        SummaryError,
        ModelError,
        DataContractError,
        DataDownloadError,
        KeyError,
        TypeError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"Wrote {LAB / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
