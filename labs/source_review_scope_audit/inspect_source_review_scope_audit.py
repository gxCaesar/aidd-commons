"""Show source bindings or check the frozen audit invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.source_review_scope_audit.analysis import (  # noqa: E402
    analyze,
    check_invariants,
)
from aidd_commons.source_review_scope_audit.protocol import (  # noqa: E402
    EXAMINED_IDS,
    load_protocol,
)
from aidd_commons.source_review_scope_audit.records import (  # noqa: E402
    load_catalogue,
    load_reading,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        protocol = load_protocol(LAB / "protocol.json")
        reading = load_reading(ROOT, protocol)
        result = analyze(load_catalogue(ROOT / "catalog/resources", EXAMINED_IDS), EXAMINED_IDS)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    failures = check_invariants(result, EXAMINED_IDS)
    if action == "show":
        print(json.dumps({"independent_reading": reading}, ensure_ascii=False))
        for row in result["records"]:
            print(json.dumps(row, ensure_ascii=False))
        print(json.dumps({"totals": result["totals"]}, ensure_ascii=False))
        print(
            json.dumps({"unmeasurable_routes": protocol["unmeasurable_routes"]}, ensure_ascii=False)
        )
        print(
            "The audit does not open linked pages or establish what they say. "
            "An entry without a date is not thereby unreliable."
        )
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"invariants={len(failures)} failure(s)")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
