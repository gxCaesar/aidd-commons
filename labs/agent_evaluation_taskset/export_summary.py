"""Export the small result only after all source and task checks pass."""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.agent_evaluation_taskset.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    try:
        result = build_summary(ROOT, LAB / "protocol.json", output=LAB / "summary.json")
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"tasks={result['task_count']} passing={result['passing_task_count']}")
    print(f"summary_bytes={(LAB / 'summary.json').stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
