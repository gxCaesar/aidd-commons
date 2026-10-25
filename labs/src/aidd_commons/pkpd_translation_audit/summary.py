"""Build and check the small, committed model output."""

from __future__ import annotations

import json
import platform
from collections.abc import Mapping
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import rdkit

from .analysis import analyse, check_analysis, load_from_cache
from .protocol import (
    BOUNDARY,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
    load_protocol,
)

PACKAGE_VERSION_FALLBACK = "0.2.0rc1"


class SummaryError(ValueError):
    """The result cannot be exported as a valid committed summary."""


def software_versions() -> dict[str, str]:
    try:
        package = version("aidd-commons-labs")
    except PackageNotFoundError:
        package = PACKAGE_VERSION_FALLBACK
    return {
        "python": platform.python_version(),
        "rdkit": rdkit.__version__,
        "aidd_commons_labs": package,
    }


def build_summary(
    protocol_path: Path,
    cache_dir: Path,
    *,
    computed_on: str | None = None,
    software: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    result = analyse(load_from_cache(cache_dir, protocol["source"]), protocol)
    failures = check_analysis(result)
    if failures:
        raise SummaryError("; ".join(failures))
    columns = [
        "parent_molecule_chembl_id",
        "human_hepatocyte_clearance",
        "rat_hepatocyte_clearance",
        "translation_factor",
        "translation_factor_lower",
        "translation_factor_upper",
        "concentration_0h_umol_l",
        "concentration_12h_umol_l",
        "concentration_24h_umol_l",
        "free_concentration_24h_umol_l",
        "occupancy_24h",
        "effect_24h",
        "effect_24h_lower",
        "effect_24h_upper",
    ]

    def compact(value: float | str) -> float | str:
        return float(f"{value:.6g}") if isinstance(value, float) else value

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": dict(software or software_versions()),
        "source": protocol["source"],
        "model": protocol["model"],
        "cohort": result.cohort,
        "uncarried_reasons": result.uncarried_reasons,
        "per_compound_columns": columns,
        "per_compound_results": [
            [compact(row.as_dict()[column]) for column in columns] for row in result.modelled
        ],
        "boundary": BOUNDARY,
    }


def check_summary(protocol_path: Path, cache_dir: Path, summary_path: Path) -> list[str]:
    try:
        saved = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"cannot read committed summary: {error}"]
    if not isinstance(saved, dict):
        return ["committed summary is not an object"]
    try:
        expected = build_summary(
            protocol_path,
            cache_dir,
            computed_on=saved.get("computed_on"),
            software=saved.get("software"),
        )
    except (ValueError, TypeError, KeyError) as error:
        return [f"cannot recompute summary: {error}"]
    return [] if saved == expected else ["committed summary differs from recomputed results"]
