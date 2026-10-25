"""Compute the ladder from the cached records and write the committed summary.

    python labs/objective_ladder/export_summary.py

Reads only what the download step cached, so the summary describes the records
that were read on the recorded date and not whatever the archives hold now.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidd_commons.objective_ladder.data import DEFAULT_CACHE_DIR, read_date  # noqa: E402
from aidd_commons.objective_ladder.protocol import load_protocol  # noqa: E402
from aidd_commons.objective_ladder.runner import read_ladders  # noqa: E402
from aidd_commons.objective_ladder.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
OUTPUT_PATH = LAB / "summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    arguments = parser.parse_args()
    cache_dir = arguments.cache_dir

    protocol = load_protocol()
    ladders = read_ladders(protocol, cache_dir)

    try:
        import numpy
        import scipy

        software = {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
        }
    except ImportError:  # pragma: no cover - the environment always has them
        software = {"python": platform.python_version()}

    summary = build_summary(
        ladders,
        protocol_id=protocol.protocol_id,
        computed_on=read_date(cache_dir),
        software=software,
    )
    OUTPUT_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {OUTPUT_PATH.relative_to(LAB.parents[1])}: "
        f"{summary['counts']['filled_cells']} of {summary['counts']['cells']} cells carry a record"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
