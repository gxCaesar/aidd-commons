"""Show and recompute the real CYP3A4-versus-CYP2D6 overlap from cached ChEMBL data.

Reads the two full-target activity snapshots already cached by `run_lab.py
download` and asks whether measured IC50 potency against one CYP enzyme
predicts potency against the other, for real compounds with an admitted
record against both. No model is fitted; every number here is a count, a
median, or a rank correlation over already-published measurements.

    python labs/cyp_assay_system/inspect_cyp_assay_system.py show
    python labs/cyp_assay_system/inspect_cyp_assay_system.py check

Needs the cache already present at `.cache/cyp_assay_system/`. If it is not,
first run:

    python labs/cyp_assay_system/run_lab.py download

Python 3.11 or newer, NumPy, SciPy and RDKit. No network access once the
cache is present.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.cyp_assay_system.analysis import (  # noqa: E402
    AnalysisContractError,
    correlation_summary,
    most_divergent,
    overlap_records,
)
from aidd_commons.cyp_assay_system.data import (  # noqa: E402
    DataContractError,
    TargetDataset,
    load_cached_targets,
)
from aidd_commons.cyp_assay_system.protocol import PROTOCOL_ID, TARGETS  # noqa: E402

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / ".cache/cyp_assay_system"
DIVERGENT_EXAMPLE_COUNT = 3


def load_protocol() -> dict:
    import json

    return json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))


def load_datasets(cache_dir: Path) -> dict[str, TargetDataset]:
    if not (cache_dir / "status.json").is_file():
        print(
            f"ERROR: {cache_dir} is not present. Run "
            "'python labs/cyp_assay_system/run_lab.py download' first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return load_cached_targets(cache_dir)


def show(protocol: dict, datasets: dict[str, TargetDataset]) -> None:
    print(f"Declared question: {protocol['declared_question']}")
    print()
    primary_id, secondary_id = TARGETS
    primary, secondary = datasets[primary_id], datasets[secondary_id]
    for target_id, dataset in ((primary_id, primary), (secondary_id, secondary)):
        audit = dataset.audit
        print(f"{target_id} ({TARGETS[target_id]}):")
        print(f"  input activity rows: {audit.input_rows}")
        print(f"  retained after the admission rule: {audit.retained_rows}")
        print(f"  admitted parent molecules: {audit.parent_count}")
        print(
            f"  parents with more than one admitted activity: {audit.duplicate_parent_count} "
            f"(median pChEMBL range {audit.median_duplicate_range}, "
            f"maximum {audit.maximum_duplicate_range})"
        )
        print("  excluded, by reason:")
        for reason, count in audit.exclusion_counts.items():
            print(f"    {reason}: {count}")
        print()

    overlap = overlap_records(primary, secondary)
    clean = tuple(r for r in overlap if r.is_clean_single_pair)
    shares_document = tuple(r for r in overlap if r.shares_a_document)
    print(f"Parents admitted under both targets: {len(overlap)}")
    print(f"  sharing at least one document across the two targets: {len(shares_document)}")
    print(f"  clean single-pair (exactly one activity per side, same document): {len(clean)}")
    print()

    full_correlation = correlation_summary(overlap)
    clean_correlation = correlation_summary(clean)
    print(
        f"Correlation over the full overlap (n={full_correlation.count}): "
        f"Pearson r={full_correlation.pearson_r:.4f}, "
        f"Spearman rho={full_correlation.spearman_rho:.4f} "
        f"(p={full_correlation.spearman_p_value:.3e})"
    )
    print(
        f"Correlation over the clean single-pair subset (n={clean_correlation.count}): "
        f"Pearson r={clean_correlation.pearson_r:.4f}, "
        f"Spearman rho={clean_correlation.spearman_rho:.4f} "
        f"(p={clean_correlation.spearman_p_value:.3e})"
    )
    print()

    print(f"Most {TARGETS[primary_id]}-selective clean pairs (highest primary minus secondary):")
    for example in most_divergent(clean, count=DIVERGENT_EXAMPLE_COUNT, favouring="primary"):
        print(
            f"  {example.parent_molecule_chembl_id}: "
            f"{TARGETS[primary_id]} pIC50={example.primary_pchembl:.2f}, "
            f"{TARGETS[secondary_id]} pIC50={example.secondary_pchembl:.2f}, "
            f"difference={example.difference:+.2f}"
        )
    print(f"Most {TARGETS[secondary_id]}-selective clean pairs (highest secondary minus primary):")
    for example in most_divergent(clean, count=DIVERGENT_EXAMPLE_COUNT, favouring="secondary"):
        print(
            f"  {example.parent_molecule_chembl_id}: "
            f"{TARGETS[primary_id]} pIC50={example.primary_pchembl:.2f}, "
            f"{TARGETS[secondary_id]} pIC50={example.secondary_pchembl:.2f}, "
            f"difference={example.difference:+.2f}"
        )
    print()
    print("What this does not show, by the frozen protocol's own declaration:")
    for item in protocol["excluded_by_design"]:
        print(f"  - {item}")


def check(datasets: dict[str, TargetDataset]) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {message}")
        if not condition:
            failures.append(message)

    primary_id, secondary_id = TARGETS
    primary, secondary = datasets[primary_id], datasets[secondary_id]
    for target_id, dataset in ((primary_id, primary), (secondary_id, secondary)):
        audit = dataset.audit
        require(
            audit.retained_rows <= audit.input_rows,
            f"{target_id}: retained rows do not exceed input rows",
        )
        require(
            sum(audit.exclusion_counts.values()) == audit.input_rows - audit.retained_rows,
            f"{target_id}: exclusion counts and retained rows account for every input row",
        )
        require(
            len(dataset.records) == audit.parent_count,
            f"{target_id}: emitted parent record count matches the audit's parent count",
        )

    overlap = overlap_records(primary, secondary)
    clean = tuple(r for r in overlap if r.is_clean_single_pair)
    primary_ids = {r.parent_molecule_chembl_id for r in primary.records}
    secondary_ids = {r.parent_molecule_chembl_id for r in secondary.records}
    overlap_ids = {r.parent_molecule_chembl_id for r in overlap}
    require(
        overlap_ids == primary_ids & secondary_ids,
        "overlap is exactly the set intersection of the two targets' admitted parents",
    )
    require(
        {r.parent_molecule_chembl_id for r in clean} <= overlap_ids,
        "every clean single-pair record is also a full-overlap record",
    )
    require(
        all(r.shares_a_document for r in clean),
        "every clean single-pair record shares a document across the two targets",
    )

    full_correlation = correlation_summary(overlap)
    require(
        full_correlation.count == len(overlap),
        "the full-overlap correlation count matches the number of overlap records",
    )
    if clean:
        clean_correlation = correlation_summary(clean)
        require(
            clean_correlation.count == len(clean),
            "the clean-subset correlation count matches the number of clean records",
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
    print("CYP ASSAY-SYSTEM CHECKS")
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
        "cached snapshot, not that in vitro IC50 potency implies any clinical interaction risk."
    )


if __name__ == "__main__":
    main()
