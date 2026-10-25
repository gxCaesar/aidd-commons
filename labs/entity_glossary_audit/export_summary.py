"""Export a compact summary after all frozen contracts and counts pass."""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import DataContractError  # noqa: E402
from aidd_commons.entity_glossary_audit.analysis import AuditError  # noqa: E402
from aidd_commons.entity_glossary_audit.protocol import ProtocolError  # noqa: E402
from aidd_commons.entity_glossary_audit.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/entity_glossary_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def main() -> int:
    cache = DEFAULT_CACHE if DEFAULT_CACHE.is_dir() else SIBLING_CACHE
    try:
        result = build_summary(LAB, cache, output=LAB / "summary.json")
    except (DataContractError, ProtocolError, AuditError, OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"admitted_measurements={result['admitted_measurement_count']}")
    print(f"summary_bytes={(LAB / 'summary.json').stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
