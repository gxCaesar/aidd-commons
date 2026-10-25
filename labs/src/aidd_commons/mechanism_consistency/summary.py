"""Build and check a small summary of the L1000 mechanism contrast."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib import metadata
from pathlib import Path
from typing import Any

from aidd_commons.l1000_perturbation_context.data import load_cached_cell_lines

from .analysis import analyse, counterevidence_counts, counts
from .protocol import PROTOCOL_ID, SUMMARY_SCHEMA, load_protocol

PACKAGE_NAME = "aidd-commons-labs"
DECLARED_PACKAGE_VERSION = "0.2.0rc1"
BOUNDARY = (
    "A vehicle-corrected signature contrast in MCF7 and PC3 at 10.0 um and 24.0 h "
    "can challenge a target-specific pattern, but a mismatched compound is not a "
    "matched stress perturbation. Correlation does not identify the intended target, "
    "establish a disease mechanism or show that a compound is worth making."
)


def installed_version(name: str, fallback: str | None = None) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        if fallback is None:
            raise
        return fallback


def build_summary(
    lab_dir: Path, cache_dir: Path, *, computed_on: str | None = None
) -> dict[str, Any]:
    protocol = load_protocol(lab_dir / "protocol.json")
    verdicts, cohort = analyse(load_cached_cell_lines(cache_dir))
    side_counts = counts(verdicts)
    counterevidence = counterevidence_counts(verdicts)
    if cohort["shared_testable"] != len(verdicts):
        raise ValueError("not every shared compound was tested")
    if cohort["admitted_union"] != (
        cohort["shared_testable"] + cohort["mcf7_only"] + cohort["pc3_only"]
    ):
        raise ValueError("admission counts do not partition the union")
    if sum(side_counts[key] for key in ("mediator_specific", "generic_stress", "undecided")) != len(
        verdicts
    ):
        raise ValueError("verdict counts do not partition the tested cohort")
    if side_counts["undecided"] != (
        side_counts["low_matched_correlation"] + side_counts["informative_mismatched_control"]
    ):
        raise ValueError("undecided reasons do not partition undecided verdicts")
    if counterevidence["mismatch_exceeds_match_informative"] != side_counts["generic_stress"]:
        raise ValueError("informative counterevidence differs from the generic-stress side")
    return {
        "schema_version": SUMMARY_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {
            "python": platform.python_version(),
            "aidd_commons_labs": installed_version(PACKAGE_NAME, DECLARED_PACKAGE_VERSION),
            "h5py": installed_version("h5py"),
            "numpy": installed_version("numpy"),
            "rdkit": installed_version("rdkit"),
            "scipy": installed_version("scipy"),
        },
        "explanations": protocol["explanations"],
        "informative_rho_minimum": protocol["comparison"]["informative_rho_minimum"],
        "cohort": cohort,
        "side_counts": side_counts,
        "counterevidence_counts": counterevidence,
        "falsifying_observation": {
            "quantity": "generic_stress_count",
            "definition": (
                "Number of shared compounds with matched rho at least 0.1 and "
                "mismatched rho strictly greater than matched rho."
            ),
            "observed": side_counts["generic_stress"],
        },
        "boundary": BOUNDARY,
        "enforced_rules": {
            "low_correlation_undecided": protocol["comparison"]["threshold_rule"],
            "informative_control_undecided": protocol["comparison"]["shared_control"],
            "undecided_not_support": protocol["comparison"]["undecided_rule"],
        },
    }


def validate_summary(summary: dict[str, Any]) -> list[str]:
    failures = []
    required = {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "explanations",
        "informative_rho_minimum",
        "cohort",
        "side_counts",
        "counterevidence_counts",
        "falsifying_observation",
        "boundary",
        "enforced_rules",
    }
    if set(summary) != required:
        failures.append("summary field set")
    if summary.get("schema_version") != SUMMARY_SCHEMA:
        failures.append("summary schema")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("protocol identifier")
    try:
        date.fromisoformat(summary["computed_on"])
    except (KeyError, TypeError, ValueError):
        failures.append("computation date")
    software = summary.get("software")
    if not isinstance(software, dict) or not all(
        isinstance(software.get(key), str) and software[key]
        for key in ("python", "aidd_commons_labs", "h5py", "numpy", "rdkit", "scipy")
    ):
        failures.append("software versions")
    cohort = summary.get("cohort")
    sides = summary.get("side_counts")
    counterevidence = summary.get("counterevidence_counts")
    if (
        not isinstance(cohort, dict)
        or not isinstance(sides, dict)
        or not isinstance(counterevidence, dict)
    ):
        failures.append("cohort or comparison counts")
    else:
        try:
            if cohort["admitted_union"] != (
                cohort["shared_testable"] + cohort["mcf7_only"] + cohort["pc3_only"]
            ):
                failures.append("union partition")
            if cohort["admitted_mcf7"] != cohort["shared_testable"] + cohort["mcf7_only"]:
                failures.append("MCF7 admission")
            if cohort["admitted_pc3"] != cohort["shared_testable"] + cohort["pc3_only"]:
                failures.append("PC3 admission")
            if cohort["shared_testable"] != sum(
                sides[key] for key in ("mediator_specific", "generic_stress", "undecided")
            ):
                failures.append("verdict partition")
            if sides["undecided"] != (
                sides["low_matched_correlation"] + sides["informative_mismatched_control"]
            ):
                failures.append("undecided partition")
            if summary["falsifying_observation"]["observed"] != sides["generic_stress"]:
                failures.append("falsifying count")
            if counterevidence["mismatch_exceeds_match_total"] != (
                counterevidence["mismatch_exceeds_match_low_matched"]
                + counterevidence["mismatch_exceeds_match_informative"]
            ):
                failures.append("counterevidence partition")
            if counterevidence["mismatch_exceeds_match_informative"] != sides["generic_stress"]:
                failures.append("informative counterevidence")
            if (
                counterevidence["mismatch_exceeds_match_low_matched"]
                > sides["low_matched_correlation"]
            ):
                failures.append("low matched counterevidence")
            if any(
                type(value) is not int or value < 0
                for value in (*cohort.values(), *sides.values(), *counterevidence.values())
            ):
                failures.append("count values")
        except (KeyError, TypeError, ValueError):
            failures.append("invalid count structure")
    return failures


def check_summary(lab_dir: Path, cache_dir: Path, output: Path) -> list[str]:
    try:
        artifact = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return [f"summary cannot be read: {error}"]
    if not isinstance(artifact, dict):
        return ["summary must be an object"]
    failures = validate_summary(artifact)
    fresh = build_summary(lab_dir, cache_dir, computed_on=artifact.get("computed_on"))
    for key in (
        "explanations",
        "informative_rho_minimum",
        "cohort",
        "side_counts",
        "counterevidence_counts",
        "falsifying_observation",
        "boundary",
        "enforced_rules",
    ):
        if artifact.get(key) != fresh[key]:
            failures.append(f"summary differs from snapshot or protocol: {key}")
    return failures


def export_summary(lab_dir: Path, cache_dir: Path, output: Path) -> dict[str, Any]:
    """Never write a summary if protocol or computed invariants fail."""
    result = build_summary(lab_dir, cache_dir)
    failures = validate_summary(result)
    if failures:
        raise ValueError("; ".join(failures))
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
