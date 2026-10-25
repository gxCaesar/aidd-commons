"""Show and recompute real intrinsic-clearance agreement across three cached
ChEMBL assay systems.

Reads the three named-assay activity snapshots already cached by
`run_lab.py download` and asks whether an intrinsic-clearance value from one
real assay system predicts the value from another, for real compounds with
an admitted record in both. No model is fitted; every number here is a
count, a median, or a rank correlation over already-published measurements.

    python labs/az_clearance_system/inspect_az_clearance_system.py show
    python labs/az_clearance_system/inspect_az_clearance_system.py check

Needs the cache already present at `.cache/az_clearance_system/`. If it is
not, first run:

    python labs/az_clearance_system/run_lab.py download

Python 3.11 or newer, NumPy, SciPy and RDKit. No network access once the
cache is present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.az_clearance_system.analysis import (  # noqa: E402
    SYSTEM_PAIRS,
    AnalysisContractError,
    correlation_summary,
    most_divergent,
    overlap_records,
    system_label,
)
from aidd_commons.az_clearance_system.data import (  # noqa: E402
    DataContractError,
    SystemDataset,
    load_cached_systems,
)
from aidd_commons.az_clearance_system.protocol import PROTOCOL_ID, SYSTEMS  # noqa: E402

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / ".cache/az_clearance_system"
DIVERGENT_EXAMPLE_COUNT = 3


def load_protocol() -> dict:
    return json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))


def load_datasets(cache_dir: Path) -> dict[str, SystemDataset]:
    if not (cache_dir / "status.json").is_file():
        print(
            f"ERROR: {cache_dir} is not present. Run "
            "'python labs/az_clearance_system/run_lab.py download' first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return load_cached_systems(cache_dir)


def show(protocol: dict, datasets: dict[str, SystemDataset]) -> None:
    print(f"Declared question: {protocol['declared_question']}")
    print()
    for assay_id in sorted(SYSTEMS):
        dataset = datasets[assay_id]
        audit = dataset.audit
        name, species, matrix = SYSTEMS[assay_id]
        print(f"{assay_id} ({name}; species={species}, matrix={matrix}):")
        print(f"  input activity rows: {audit.input_rows}")
        print(f"  retained after the admission rule: {audit.retained_rows}")
        print(f"  admitted parent molecules: {audit.parent_count}")
        print(
            f"  parents with more than one admitted activity: {audit.duplicate_parent_count} "
            f"(median value range {audit.median_duplicate_range}, "
            f"maximum {audit.maximum_duplicate_range})"
        )
        print("  excluded, by reason:")
        for reason, count in audit.exclusion_counts.items():
            print(f"    {reason}: {count}")
        print()

    for primary_id, secondary_id, varies in SYSTEM_PAIRS:
        primary_dataset, secondary_dataset = datasets[primary_id], datasets[secondary_id]
        overlap = overlap_records(primary_dataset, secondary_dataset)
        clean = tuple(r for r in overlap if r.is_clean_single_pair)
        primary_name, secondary_name = system_label(primary_id), system_label(secondary_id)
        primary_units = (
            primary_dataset.records[0].standard_units if primary_dataset.records else "?"
        )
        secondary_units = (
            secondary_dataset.records[0].standard_units if secondary_dataset.records else "?"
        )
        print(f"{primary_name} vs. {secondary_name} ({varies}):")
        print(f"  overlap: {len(overlap)} parents; clean single-pair subset: {len(clean)}")
        if primary_units != secondary_units:
            print(
                f"  NOTE: units differ ({primary_units} vs. {secondary_units}); the correlation "
                "below is unaffected by that (both are rank/linear measures invariant to a fixed "
                "rescaling of either side), but the log10 ratio in the divergent examples below "
                "is not a literal fold-change here, only a same-direction size signal."
            )
        full_correlation = correlation_summary(overlap)
        clean_correlation = correlation_summary(clean)
        print(
            f"  full overlap (n={full_correlation.count}): "
            f"Pearson r={full_correlation.pearson_r:.4f}, "
            f"Spearman rho={full_correlation.spearman_rho:.4f} "
            f"(p={full_correlation.spearman_p_value:.3e})"
        )
        print(
            f"  clean subset (n={clean_correlation.count}): "
            f"Pearson r={clean_correlation.pearson_r:.4f}, "
            f"Spearman rho={clean_correlation.spearman_rho:.4f} "
            f"(p={clean_correlation.spearman_p_value:.3e})"
        )
        print(f"  most {primary_name}-selective clean pairs (highest primary/secondary ratio):")
        for example in most_divergent(clean, count=DIVERGENT_EXAMPLE_COUNT, favouring="primary"):
            print(
                f"    {example.parent_molecule_chembl_id}: "
                f"primary={example.primary_clearance:.3g}, "
                f"secondary={example.secondary_clearance:.3g}, "
                f"log10 ratio={example.log_ratio:+.2f}"
            )
        print(f"  most {secondary_name}-selective clean pairs (lowest primary/secondary ratio):")
        for example in most_divergent(clean, count=DIVERGENT_EXAMPLE_COUNT, favouring="secondary"):
            print(
                f"    {example.parent_molecule_chembl_id}: "
                f"primary={example.primary_clearance:.3g}, "
                f"secondary={example.secondary_clearance:.3g}, "
                f"log10 ratio={example.log_ratio:+.2f}"
            )
        print()

    print("What this does not show, by the frozen protocol's own declaration:")
    for item in protocol["excluded_by_design"]:
        print(f"  - {item}")


def check(datasets: dict[str, SystemDataset]) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {message}")
        if not condition:
            failures.append(message)

    for assay_id in sorted(SYSTEMS):
        dataset = datasets[assay_id]
        audit = dataset.audit
        require(
            audit.retained_rows <= audit.input_rows,
            f"{assay_id}: retained rows do not exceed input rows",
        )
        require(
            sum(audit.exclusion_counts.values()) == audit.input_rows - audit.retained_rows,
            f"{assay_id}: exclusion counts and retained rows account for every input row",
        )
        require(
            len(dataset.records) == audit.parent_count,
            f"{assay_id}: emitted parent record count matches the audit's parent count",
        )

    for primary_id, secondary_id, _varies in SYSTEM_PAIRS:
        primary, secondary = datasets[primary_id], datasets[secondary_id]
        overlap = overlap_records(primary, secondary)
        clean = tuple(r for r in overlap if r.is_clean_single_pair)
        primary_ids = {r.parent_molecule_chembl_id for r in primary.records}
        secondary_ids = {r.parent_molecule_chembl_id for r in secondary.records}
        overlap_ids = {r.parent_molecule_chembl_id for r in overlap}
        require(
            overlap_ids == primary_ids & secondary_ids,
            f"{primary_id} vs {secondary_id}: overlap is exactly the set intersection",
        )
        require(
            {r.parent_molecule_chembl_id for r in clean} <= overlap_ids,
            f"{primary_id} vs {secondary_id}: every clean single-pair record is also an overlap "
            "record",
        )
        full_correlation = correlation_summary(overlap)
        require(
            full_correlation.count == len(overlap),
            f"{primary_id} vs {secondary_id}: correlation count matches overlap record count",
        )
        if clean:
            clean_correlation = correlation_summary(clean)
            require(
                clean_correlation.count == len(clean),
                f"{primary_id} vs {secondary_id}: clean correlation count matches "
                "clean record count",
            )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args()
    protocol = load_protocol()
    assert protocol["protocol_id"] == PROTOCOL_ID
    try:
        datasets = load_datasets(args.cache_dir)
    except DataContractError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    if args.action == "show":
        try:
            show(protocol, datasets)
        except AnalysisContractError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            sys.exit(1)
        print()
        print("Run 'check' to recompute these relationships.")
        return
    print("AZ CLEARANCE-SYSTEM CHECKS")
    try:
        failures = check(datasets)
    except AnalysisContractError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print(
        "All checks passed. This verifies the admission rule and overlap arithmetic on the "
        "cached snapshot, not that in vitro intrinsic clearance implies any human dose or "
        "clinical exposure outcome."
    )


if __name__ == "__main__":
    main()
