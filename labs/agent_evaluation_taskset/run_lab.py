"""Verify that all frozen local inputs exist without downloading anything."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.agent_evaluation_taskset.analysis import used_sources  # noqa: E402
from aidd_commons.agent_evaluation_taskset.protocol import (  # noqa: E402
    load_protocol,
    local_path,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        for task in protocol["tasks"]:
            missing = [path for path in task["files"] if not local_path(ROOT, path).is_file()]
            if missing:
                raise ValueError(f"missing committed files for {task['id']}: {missing}")
            for path in task["files"]:
                local_path(ROOT, path).read_text(encoding="utf-8")
            if set(used_sources(ROOT, task)) != set(task["declared_sources"]):
                raise ValueError(f"source declaration differs from own laboratory: {task['id']}")
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(protocol['tasks'])} local tasks are present; nothing downloaded or written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
