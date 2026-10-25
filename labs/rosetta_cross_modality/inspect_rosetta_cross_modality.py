"""Show the committed ROSETTA cross-modality result, or check it against the
cached data.

    python labs/rosetta_cross_modality/inspect_rosetta_cross_modality.py show
    python labs/rosetta_cross_modality/inspect_rosetta_cross_modality.py check

`show` prints the committed summary readably and needs no data. `check`
re-reads the cached objects, recomputes the whole frozen evaluation set and
exits non-zero if any invariant fails or if the committed summary no longer
matches what the cached data produce. It needs the cache already present at
`.cache/rosetta_cross_modality/`; if it is not, first run:

    python labs/rosetta_cross_modality/run_lab.py download

Python 3.11 or newer and NumPy. No network access once the cache is present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np  # noqa: E402
from aidd_commons.rosetta_cross_modality.analysis import (  # noqa: E402
    AnalysisContractError,
)
from aidd_commons.rosetta_cross_modality.data import (  # noqa: E402
    DataContractError,
    load_cached_dataset,
)
from aidd_commons.rosetta_cross_modality.protocol import (  # noqa: E402
    ContractError,
    load_contract,
)
from aidd_commons.rosetta_cross_modality.summary import (  # noqa: E402
    build_summary,
    project_summary,
)

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / ".cache/rosetta_cross_modality"
SUMMARY_PATH = LAB / "summary.json"
TOLERANCE = 1e-9


def load_summary() -> dict[str, Any]:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def show(summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    print(f"Protocol: {summary['protocol_id']}")
    print(
        f"Source: {summary['source']['study_id']} / {summary['source']['batch_id']} "
        f"({summary['source']['cell_line']})"
    )
    print(f"Computed on: {summary['computed_on']}")
    print()
    print("Counts:")
    for modality in ("transcriptome", "imaging"):
        block = counts[modality]
        print(
            f"  {modality}: {block['input_rows']} wells "
            f"({block['treated_rows']} treated, {block['control_rows']} control), "
            f"{block['perturbations']} perturbations, {block['plates']} plates"
        )
    print(
        f"  admitted in both readouts: {counts['admitted_perturbations']} "
        f"({counts['batch_pure_perturbations']} in one batch, "
        f"{counts['batch_mixed_perturbations']} spanning both)"
    )
    print(f"  excluded, by reason: {counts['exclusion_counts'] or 'none'}")
    print(
        f"  features: {summary['features']['transcriptome']} transcriptomic, "
        f"{summary['features']['imaging']} imaging"
    )
    print()
    print("What the plate and the batch do to the measured variance:")
    for name, block in summary["variance_attribution"].items():
        print(
            f"  {name}: {100 * block['between']:.2f}% between, "
            f"{100 * block['within']:.2f}% within"
        )
    print()
    print(
        "Cross-modality agreement (predicting the imaging readout from the "
        "transcriptomic readout):"
    )
    evaluations = summary["evaluations"]
    for name, block in evaluations.items():
        print(
            f"  {name}: perturbation r={block['perturbation_r']:+.4f}, "
            f"feature r={block['feature_r']:+.4f} "
            f"({block['folds']} folds, {block['tested_perturbations']} perturbations)"
        )
    print()
    print("How much of the above-null agreement survives:")
    survival = summary["survival"]
    for key, value in survival.items():
        if key == "definition":
            continue
        print(f"  {key}: {value:+.4f}")
    print()
    print("Model-free check (no model, no split):")
    free = summary["model_free_check"]
    print(f"  neighbourhood concordance: {free['neighbourhood_concordance']:+.4f}")
    print(f"  permuted null: {free['neighbourhood_concordance_permuted_null']:+.4f}")
    print()
    print("Named examples (highest and lowest agreement under the apparent split):")
    for label in ("most_agreeable", "least_agreeable"):
        for example in summary["examples"][label]:
            print(
                f"  {label}: {example['allele']} ({example['gene_symbol']}) "
                f"{example['perturbation']} r={example['perturbation_r']:+.4f}"
            )
    print()
    print("This lab does not show that a perturbation signature is a mechanism.")
    print("It shows how much of the agreement between two readouts of the same")
    print("perturbation survives an evaluation that keeps the experimental design")
    print("from leaking. See the README for the full statement of what it does")
    print("not show.")


def _compare(committed: Any, recomputed: Any, path: str, failures: list[str]) -> None:
    if isinstance(committed, dict) and isinstance(recomputed, dict):
        for key in sorted(set(committed) | set(recomputed)):
            if key not in committed or key not in recomputed:
                failures.append(f"{path}.{key}: present in only one of the two summaries")
                continue
            _compare(committed[key], recomputed[key], f"{path}.{key}", failures)
        return
    if isinstance(committed, list) and isinstance(recomputed, list):
        if len(committed) != len(recomputed):
            failures.append(f"{path}: length {len(committed)} vs {len(recomputed)}")
            return
        for index, (left, right) in enumerate(zip(committed, recomputed, strict=True)):
            _compare(left, right, f"{path}[{index}]", failures)
        return
    if isinstance(committed, bool) or isinstance(recomputed, bool):
        if committed != recomputed:
            failures.append(f"{path}: {committed!r} vs {recomputed!r}")
        return
    if isinstance(committed, (int, float)) and isinstance(recomputed, (int, float)):
        if abs(float(committed) - float(recomputed)) > TOLERANCE:
            failures.append(f"{path}: {committed!r} vs {recomputed!r}")
        return
    if committed != recomputed:
        failures.append(f"{path}: {committed!r} vs {recomputed!r}")


def check(cache_dir: Path, summary: dict[str, Any], contract: Any) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        print(f"  [{'PASS' if condition else 'FAIL'}] {message}")
        if not condition:
            failures.append(message)

    print("ROSETTA CROSS-MODALITY CHECKS")
    dataset = load_cached_dataset(cache_dir, contract)
    audit = dataset.audit
    print()
    print("Data contract:")
    for modality, total, control, treated in (
        (
            "transcriptome",
            audit.transcriptome_input_rows,
            audit.transcriptome_control_rows,
            audit.transcriptome_treated_rows,
        ),
        (
            "imaging",
            audit.imaging_input_rows,
            audit.imaging_control_rows,
            audit.imaging_treated_rows,
        ),
    ):
        require(
            control + treated == total,
            f"{modality}: control and treated wells account for every input row",
        )
    require(
        audit.admitted_perturbations
        == min(audit.transcriptome_perturbations, audit.imaging_perturbations)
        - audit.exclusion_counts.get("transcriptome_only_perturbation", 0),
        "the admitted perturbation count follows from the two readouts' own counts",
    )
    require(
        audit.batch_pure_perturbations + audit.batch_mixed_perturbations
        == audit.admitted_perturbations,
        "batch-pure and batch-mixed perturbations partition the admitted entities",
    )
    require(
        all(
            perturbation.transcriptome.shape == (len(dataset.transcriptome_features),)
            and perturbation.imaging.shape == (len(dataset.imaging_features),)
            for perturbation in dataset.perturbations
        ),
        "every admitted perturbation has one profile of the declared width in each readout",
    )
    require(
        all(
            np.isfinite(perturbation.transcriptome).all()
            and np.isfinite(perturbation.imaging).all()
            for perturbation in dataset.perturbations
        ),
        "every admitted profile is finite",
    )
    require(
        all(
            perturbation.transcriptome_replicates >= 1
            and perturbation.imaging_replicates >= 1
            for perturbation in dataset.perturbations
        ),
        "every admitted perturbation has at least one well in each readout",
    )
    print()
    print("Recomputation against the committed summary:")
    recomputed = project_summary(
        build_summary(
            dataset,
            contract,
            computed_on=summary["computed_on"],
            software=summary["software"],
        )
    )
    for key in sorted(summary):
        before = len(failures)
        _compare(summary[key], recomputed.get(key), key, failures)
        require(
            len(failures) == before,
            f"the committed '{key}' block matches what the cached data recompute",
        )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args(argv)
    summary = load_summary()
    try:
        contract = load_contract(LAB / "protocol.json")
    except ContractError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if summary["protocol_id"] != contract.protocol_id:
        print(
            f"ERROR: committed summary carries protocol {summary['protocol_id']}, "
            f"the contract declares {contract.protocol_id}",
            file=sys.stderr,
        )
        return 2
    if args.action == "show":
        show(summary)
        print()
        print("Run 'check' to recompute these numbers from the cached data.")
        return 0
    if not args.cache_dir.is_dir():
        print(
            f"ERROR: {args.cache_dir} is not present. Run "
            "'python labs/rosetta_cross_modality/run_lab.py download' first.",
            file=sys.stderr,
        )
        return 1
    try:
        failures = check(args.cache_dir, summary, contract)
    except (ContractError, DataContractError, AnalysisContractError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print(
        "All checks passed. This verifies the admission rule, the evaluation "
        "arithmetic and the committed summary against the cached snapshot; it "
        "does not show that a perturbation signature is a mechanism."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
