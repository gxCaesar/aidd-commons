"""Show and recompute real cross-cell-line signature agreement from a cached
LINCS L1000 snapshot.

Reads the GSE70138 files already cached by `run_lab.py download` and asks
whether a real compound's transcriptional signature in one cell line
predicts its signature in another, real, different cell line. No model is
fitted; every number here is a count, a median, a rank correlation or a
rank-sum test over already-published measurements.

    python labs/l1000_perturbation_context/inspect_l1000_perturbation_context.py show
    python labs/l1000_perturbation_context/inspect_l1000_perturbation_context.py check

Needs the cache already present at `.cache/l1000_perturbation_context/`. If
it is not, first run:

    python labs/l1000_perturbation_context/run_lab.py download

Python 3.11 or newer, NumPy, SciPy, RDKit and h5py. No network access once
the cache is present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.l1000_perturbation_context.analysis import (  # noqa: E402
    AnalysisContractError,
    compare_matched_to_null,
    matched_pairs,
    most_divergent,
    null_pairs,
    shared_compounds,
    summarize,
)
from aidd_commons.l1000_perturbation_context.data import (  # noqa: E402
    CellLineDataset,
    DataContractError,
    load_cached_cell_lines,
)
from aidd_commons.l1000_perturbation_context.protocol import (  # noqa: E402
    CELL_LINE_A,
    CELL_LINE_B,
    PROTOCOL_ID,
)

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / ".cache/l1000_perturbation_context"
DIVERGENT_EXAMPLE_COUNT = 3


def load_protocol() -> dict:
    return json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))


def load_datasets(cache_dir: Path) -> dict[str, CellLineDataset]:
    if not (cache_dir / "GSE70138_Broad_LINCS_inst_info_2017-03-06.txt.gz").is_file():
        print(
            f"ERROR: {cache_dir} is not present. Run "
            "'python labs/l1000_perturbation_context/run_lab.py download' first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return load_cached_cell_lines(cache_dir)


def show(protocol: dict, datasets: dict[str, CellLineDataset]) -> None:
    print(f"Declared question: {protocol['declared_question']}")
    print()
    a, b = datasets[CELL_LINE_A], datasets[CELL_LINE_B]
    for cell_id, dataset in ((CELL_LINE_A, a), (CELL_LINE_B, b)):
        audit = dataset.audit
        print(f"{cell_id}:")
        print(f"  input compound-treatment rows: {audit.input_rows}")
        print(f"  retained after the admission rule: {audit.retained_rows}")
        print(f"  admitted compounds: {audit.admitted_entity_count}")
        print(f"  compounds with more than one admitted replicate: {audit.duplicate_entity_count}")
        print("  excluded, by reason:")
        for reason, count in audit.exclusion_counts.items():
            print(f"    {reason}: {count}")
        print()

    matched = matched_pairs(a, b)
    null = null_pairs(a, b)
    print(f"Shared compounds: {len(shared_compounds(a, b))}")
    matched_summary = summarize(matched)
    null_summary = summarize(null)
    print(
        f"  matched (real, compound-matched) Spearman rho: median={matched_summary.median:.4f}, "
        f"mean={matched_summary.mean:.4f}, "
        f"fraction positive={matched_summary.fraction_positive:.3f}"
    )
    print(
        f"  null (deterministic mismatched) Spearman rho: median={null_summary.median:.4f}, "
        f"mean={null_summary.mean:.4f}, fraction positive={null_summary.fraction_positive:.3f}"
    )
    rank_sum = compare_matched_to_null(matched, null)
    print(
        f"  Mann-Whitney U test, matched vs. null: U={rank_sum.u_statistic:.1f}, "
        f"p={rank_sum.p_value:.3e}"
    )
    print()
    print("Most reproducible compounds (highest cross-cell-line Spearman rho):")
    for pair in most_divergent(matched, count=DIVERGENT_EXAMPLE_COUNT, favouring="reproducible"):
        print(f"  {pair.pert_id} ({pair.pert_iname}): rho={pair.spearman_rho:+.3f}")
    print("Most divergent compounds (lowest, most negative cross-cell-line Spearman rho):")
    for pair in most_divergent(matched, count=DIVERGENT_EXAMPLE_COUNT, favouring="divergent"):
        print(f"  {pair.pert_id} ({pair.pert_iname}): rho={pair.spearman_rho:+.3f}")
    print()
    print("What this does not show, by the frozen protocol's own declaration:")
    for item in protocol["excluded_by_design"]:
        print(f"  - {item}")


def check(datasets: dict[str, CellLineDataset]) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {message}")
        if not condition:
            failures.append(message)

    a, b = datasets[CELL_LINE_A], datasets[CELL_LINE_B]
    for cell_id, dataset in ((CELL_LINE_A, a), (CELL_LINE_B, b)):
        audit = dataset.audit
        require(
            audit.retained_rows <= audit.input_rows,
            f"{cell_id}: retained rows do not exceed input rows",
        )
        require(
            sum(audit.exclusion_counts.values()) == audit.input_rows - audit.retained_rows,
            f"{cell_id}: exclusion counts and retained rows account for every input row",
        )
        require(
            len(dataset.signatures) == audit.admitted_entity_count,
            f"{cell_id}: emitted signature count matches the audit's admitted-entity count",
        )

    shared = set(shared_compounds(a, b))
    require(
        shared == set(a.signatures) & set(b.signatures),
        "shared compounds are exactly the set intersection of both cell lines' admitted compounds",
    )

    matched = matched_pairs(a, b)
    require(
        len(matched) == len(shared),
        "one matched pair exists for every shared compound",
    )
    try:
        null = null_pairs(a, b)
        require(
            len(null) == len(matched),
            "the null background has exactly as many pairs as the matched comparison",
        )
        rank_sum = compare_matched_to_null(matched, null)
        require(
            rank_sum.matched_count == len(matched) and rank_sum.null_count == len(null),
            "the rank-sum test consumed exactly the matched and null pair counts computed above",
        )
    except AnalysisContractError as error:
        failures.append(str(error))
        print(f"  [FAIL] {error}")
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
    print("L1000 PERTURBATION-CONTEXT CHECKS")
    failures = check(datasets)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print(
        "All checks passed. This verifies the admission rule and comparison arithmetic on the "
        "cached snapshot, not that a cross-cell-line signature correlation predicts any "
        "clinical or in vivo outcome."
    )


if __name__ == "__main__":
    main()
