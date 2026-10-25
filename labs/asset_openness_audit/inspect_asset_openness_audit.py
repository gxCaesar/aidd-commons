"""Show source claims or check the seven-field evidence contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.asset_openness_audit.analysis import analyze, check_invariants  # noqa: E402
from aidd_commons.asset_openness_audit.protocol import EXAMINED_IDS, load_protocol  # noqa: E402
from aidd_commons.asset_openness_audit.records import load_catalogue  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        load_protocol(LAB / "protocol.json")
        result = analyze(load_catalogue(ROOT / "catalog/resources", EXAMINED_IDS), EXAMINED_IDS)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    failures = check_invariants(result, EXAMINED_IDS)
    if action == "show":
        print(
            "scope_limit_rule=case-insensitive whole words: "
            "only | not | no separate terms | does not"
        )
        print("scope_limit_rule_is_text_only=true")
        for row in result["records"]:
            print(json.dumps(row, ensure_ascii=False))
        print(
            json.dumps(
                {
                    "examined_counts": result["examined_counts"],
                    "whole_catalogue": result["whole_catalogue"],
                }
            )
        )
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"invariants={len(failures)} failure(s)")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
