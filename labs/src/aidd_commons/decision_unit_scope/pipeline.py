"""The runnable task of this lab, in one callable place.

`run_census_export` is the order of operations the lab commits to: validate
the frozen contract first, then read the cached snapshot, then count, then
write. A contract that has been mutated is rejected before the cache is
touched and before any output file exists, which is what makes a known-bad
edit fail loudly instead of quietly changing what the lab measures.
"""

from __future__ import annotations

import json
import platform
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import numpy
import rdkit

from .analysis import census_cohort
from .data import load_cached_cohort
from .protocol import load_protocol_document
from .summary import build_summary


def default_software() -> dict[str, str]:
    """The software versions a published number was computed with."""
    return {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "rdkit": rdkit.__version__,
    }


def run_census_export(
    lab_dir: Path,
    cache_dir: Path,
    output_path: Path,
    *,
    computed_on: str | None = None,
    software: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Validate the contract, count the cohort and write the summary."""
    load_protocol_document(lab_dir / "protocol.json")
    cohort = load_cached_cohort(cache_dir)
    census = census_cohort(cohort)
    summary = build_summary(
        cohort,
        census,
        computed_on=computed_on or date.today().isoformat(),
        software=software or default_software(),
    )
    output_path.write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
