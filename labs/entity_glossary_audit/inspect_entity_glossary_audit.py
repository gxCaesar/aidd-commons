"""Show entity counts or check the committed result against the cached rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import DataContractError  # noqa: E402
from aidd_commons.entity_glossary_audit.analysis import AuditError  # noqa: E402
from aidd_commons.entity_glossary_audit.protocol import ProtocolError  # noqa: E402
from aidd_commons.entity_glossary_audit.summary import (  # noqa: E402
    build_summary,
    validate_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/entity_glossary_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    cache = args.cache_dir or (DEFAULT_CACHE if DEFAULT_CACHE.is_dir() else SIBLING_CACHE)
    try:
        committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
        computed = build_summary(
            LAB,
            cache,
            computed_on=committed["computed_on"],
            software=committed["software"],
        )
        failures = validate_summary(committed)
        if committed != computed:
            failures.append("committed summary differs from cached-row recount")
    except (DataContractError, ProtocolError, AuditError, OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if args.action == "show":
        for kind, row in computed["per_kind"].items():
            print(json.dumps({"kind": kind, **row}, sort_keys=True))
        print(json.dumps({"unnamed_kinds": computed["unnamed_kinds"]}, sort_keys=True))
        print(json.dumps({"totals": computed["totals"]}, sort_keys=True))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
