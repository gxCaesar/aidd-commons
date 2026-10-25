"""Show and re-check the declared PubChem BioAssay assay records.

    python labs/assay_endpoint_controls/inspect_assay_endpoint_controls.py show
    python labs/assay_endpoint_controls/inspect_assay_endpoint_controls.py check

`show` prints the cheap baseline first, the control audit of every declared
assay, the concentration-response check and the statement of what each assay
licenses. `check` recomputes the invariants and exits non-zero on any
violation.

Needs the cache already present at `.cache/assay_endpoint_controls/`. If it is
not, first run:

    python labs/assay_endpoint_controls/run_lab.py download

Python 3.11 or newer, NumPy, SciPy and RDKit. No network access once the
cache is present.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.assay_endpoint_controls.analysis import (  # noqa: E402
    AnalysisContractError,
    assay_profile,
    readout_mix,
    relation_mix,
    score_summary,
    split_counts,
)
from aidd_commons.assay_endpoint_controls.data import (  # noqa: E402
    DataContractError,
    load_cached_assays,
)
from aidd_commons.assay_endpoint_controls.pipeline import (  # noqa: E402
    ProtocolContractError,
    load_protocol,
    validate_protocol_contract,
)
from aidd_commons.assay_endpoint_controls.protocol import (  # noqa: E402
    DECLARED_ASSAYS,
    SPLIT_SEED,
)

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / ".cache/assay_endpoint_controls"


def _mix_line(name: str, counts: dict[str, int], total: int) -> str:
    parts = [
        f"{key} {value} ({value / total:.3f})" if total else f"{key} {value}"
        for key, value in sorted(counts.items())
    ]
    return f"  {name} (n={total}): " + ", ".join(parts)


def show(protocol: dict, cache_dir: Path) -> int:
    datasets = load_cached_assays(cache_dir)
    print(protocol["declared_question"])
    print()
    print("CHEAP BASELINE: counts and distributions, before any curve is read")
    print()
    readouts = readout_mix(datasets)
    print(_mix_line("readout mix (endpoint label)", dict(readouts.counts), readouts.total))
    relations = relation_mix(datasets)
    print(_mix_line("relation mix (qualifier)", dict(relations.counts), relations.total))
    all_rows = [row for dataset in datasets.values() for row in dataset.rows]
    score = score_summary(all_rows)
    print(
        f"  confidence score (n={score.count}): minimum {score.minimum:g}, "
        f"median {score.median:g}, maximum {score.maximum:g}, "
        f"fraction at the maximum {score.fraction_at_maximum:.3f}, "
        f"fraction at zero {score.fraction_zero:.3f}"
    )
    counts = split_counts(datasets, seed=SPLIT_SEED)
    print(
        f"  compound split (seed {SPLIT_SEED}): development {counts['development']}, "
        f"held out {counts['held_out']}"
    )
    print()

    for aid in DECLARED_ASSAYS:
        profile = assay_profile(datasets[aid], seed=SPLIT_SEED)
        audit = profile.reference_audit
        check = profile.curve_check
        print(f"ASSAY {profile.aid}: {profile.name}")
        print(
            f"  endpoint: {profile.endpoint_label} in {profile.endpoint_unit}, "
            f"direction {profile.direction}"
        )
        print(
            f"  archived rows: {profile.input_rows}; admitted: {profile.retained_rows} "
            f"({profile.admitted_compounds} compounds)"
        )
        if profile.exclusion_counts:
            print(
                "  excluded, by reason: "
                + ", ".join(
                    f"{reason} {count}"
                    for reason, count in sorted(profile.exclusion_counts.items())
                )
            )
        print(
            _mix_line(
                "relation mix", dict(profile.relation_mix.counts), profile.relation_mix.total
            )
        )
        print(
            f"  replicate structure: the archived protocol declares "
            f"{profile.replicate_declaration}; the archive records "
            f"{profile.determination_column} as {profile.determination_kind}"
        )
        print(
            _mix_line(
                "recorded counts",
                dict(profile.replicate_counts.counts),
                profile.replicate_counts.total,
            )
        )
        print(f"  control regime declared: {audit.declared_regime}")
        print(
            f"  reference wells named in the archived protocol: {audit.references_declared} "
            f"({', '.join(audit.reference_keywords) if audit.reference_keywords else 'none'})"
        )
        print(f"  normalisation equation: {audit.normalisation_equation}")
        if audit.archived_equation_text:
            print(f"  archived equation: {audit.archived_equation_text}")
        if audit.equation_matches_archived_scale is not None:
            print(
                f"  the equation puts the positive reference at "
                f"{audit.equation_value_at_positive_control:g} and the negative reference at "
                f"{audit.equation_value_at_negative_control:g}, so the scale it describes is "
                f"{audit.equation_scale_verdict}"
            )
            print(
                f"  the archived values run from {audit.archived_response_min:g} to "
                f"{audit.archived_response_max:g} percent; "
                f"{audit.fraction_inside_equation_range:.3f} of them fall inside the range the "
                f"equation describes; the equation reproduces the archived scale: "
                f"{audit.equation_matches_archived_scale}"
            )
            print(
                f"  archived values above 100 percent: {audit.archived_values_above_hundred}; "
                f"below 0 percent: {audit.archived_values_below_zero}"
            )
        print(
            f"  concentration-response check: {check.mode} "
            f"(hill fit mode {profile.hill_fit_mode}); {check.recomputed_curves} curves "
            f"recomputed from the archived parameters, {check.refitted_curves} refitted from "
            f"the archived points, {check.skipped_rows} rows skipped"
        )
        for label, agreement in (("development", check.development), ("held out", check.heldout)):
            if agreement.curves == 0:
                print(f"    {label}: no curves")
                continue
            print(
                f"    {label}: {agreement.curves} curves, {agreement.points} points, "
                f"median deviation {agreement.median_absolute_deviation:g} points, "
                f"90th percentile {agreement.p90_absolute_deviation:g} points, "
                f"fraction within {check.tolerance_points:g} points "
                f"{agreement.fraction_within_tolerance:.3f}"
            )
            if agreement.median_endpoint_log10_error is not None:
                print(
                    f"      endpoint log10 error: median "
                    f"{agreement.median_endpoint_log10_error:.4f}, "
                    f"fraction within a factor of three "
                    f"{agreement.fraction_endpoint_within_factor_three:.3f}"
                )
        print("  licensed:")
        for claim in profile.licensed_claims:
            print(f"    - {claim}")
        print("  not licensed:")
        for claim in profile.unlicensed_claims:
            print(f"    - {claim}")
        print()

    print("What this does not show, by the frozen protocol's own declaration:")
    for item in protocol["excluded_by_design"]:
        print(f"  - {item}")
    return 0


def check(cache_dir: Path) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {message}")
        if not condition:
            failures.append(message)

    protocol = load_protocol(REPOSITORY_ROOT)
    try:
        validate_protocol_contract(protocol)
    except ProtocolContractError as error:
        print(f"  [FAIL] the frozen protocol does not match the frozen contract: {error}")
        failures.append("the frozen protocol does not match the frozen contract")
        return failures
    print("  [PASS] the frozen protocol matches the frozen contract")

    datasets = load_cached_assays(cache_dir)
    total_rows = 0
    for aid in DECLARED_ASSAYS:
        dataset = datasets[aid]
        profile = assay_profile(dataset, seed=SPLIT_SEED)
        audit = profile.reference_audit
        require(
            profile.retained_rows <= profile.input_rows,
            f"assay {aid}: retained rows do not exceed the archived rows",
        )
        require(
            sum(profile.exclusion_counts.values())
            == profile.input_rows - profile.retained_rows,
            f"assay {aid}: the exclusion counts account for every archived row",
        )
        require(
            profile.admitted_compounds
            == len({row.compound_id for row in dataset.rows}),
            f"assay {aid}: the admitted compound count matches the distinct compounds",
        )
        require(
            profile.relation_mix.total == profile.retained_rows,
            f"assay {aid}: every admitted row carries exactly one relation qualifier",
        )
        require(
            profile.readout_mix.total
            == sum(len(row.endpoints) for row in dataset.rows),
            f"assay {aid}: every admitted endpoint value is counted in the readout mix",
        )
        expected_references = {
            "positive_and_negative_reference": 2,
            "single_positive_reference": 1,
            "none_declared": 0,
        }[audit.declared_regime]
        require(
            audit.references_declared == expected_references,
            f"assay {aid}: the archived protocol names {audit.references_declared} reference "
            f"wells, the declared regime expects {expected_references}",
        )
        if audit.declared_regime == "none_declared":
            require(
                not audit.control_keywords and not audit.reference_keywords,
                f"assay {aid}: the archived protocol names no control, vehicle or reference well",
            )
        else:
            require(
                bool(audit.control_keywords or audit.reference_keywords),
                f"assay {aid}: the archived protocol does name a control, vehicle "
                "or reference well",
            )
        check = profile.curve_check
        require(
            check.development.curves + check.heldout.curves
            <= profile.retained_rows,
            f"assay {aid}: the curve check never counts more curves than admitted rows",
        )
        total_rows += profile.retained_rows

    counts = split_counts(datasets, seed=SPLIT_SEED)
    require(
        counts["development"] + counts["held_out"] == total_rows,
        "the compound split accounts for every admitted row",
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args()
    cache_dir = args.cache_dir
    protocol = load_protocol(REPOSITORY_ROOT)
    try:
        if args.action == "show":
            show(protocol, cache_dir)
            print()
            print("Run 'check' to recompute these relationships.")
            return 0
        print("ASSAY ENDPOINT AND CONTROL CHECKS")
        failures = check(cache_dir)
    except (DataContractError, AnalysisContractError, ProtocolContractError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print(
        "All checks passed. This verifies the admission rule, the control audit and the "
        "curve arithmetic on the cached archive. It does not verify that any assay's "
        "conclusion is correct, and it says nothing about the compounds themselves."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
