"""Show five task dimensions or check the committed result against live records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.agent_evaluation_taskset.protocol import DIMENSIONS  # noqa: E402
from aidd_commons.agent_evaluation_taskset.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
        current = build_summary(
            ROOT,
            LAB / "protocol.json",
            computed_on=committed["computed_on"],
            software=committed["software"],
        )
        if current != committed:
            raise ValueError("committed summary differs from recomputed task results")
    except (OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if action == "show":
        for row in current["per_task"]:
            states = " ".join(f"{name}={row['dimensions'][name]}" for name in DIMENSIONS)
            print(f"{row['id']} {states} passing={row['passing']}")
        print(
            f"task_count={current['task_count']} passing_task_count={current['passing_task_count']}"
        )
    else:
        print(f"PASS: {current['task_count']} tasks and five dimensions match committed records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
