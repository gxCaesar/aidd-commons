"""Show the link chains or recompute and enforce their claim boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.claim_chain_audit.analysis import (  # noqa: E402
    analyze,
    check_invariants,
    load_records,
)
from aidd_commons.claim_chain_audit.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        protocol = load_protocol(LAB / "protocol.json")
        result = analyze(load_records(ROOT, protocol), protocol, ROOT)
        failures = check_invariants(result, protocol)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if action == "show":
        for chain in result["chains"]:
            print(json.dumps({key: value for key, value in chain.items() if key != "links"}))
            for link in chain["links"]:
                print(json.dumps(link))
        print(result["boundary_statement"])
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"invariants={len(failures)} failure(s)")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
