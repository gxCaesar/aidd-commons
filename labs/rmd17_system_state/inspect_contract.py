"""Read the frozen rMD17 system-state contract and check the committed artifacts.

This command needs no network, no download and no third-party package. It reads
only the JSON files committed beside it. It answers the questions that come
before a model: what is the observable, which arrays may become features, how
were 1000 frames chosen out of 100000, and what is the error being compared
against.

    python labs/rmd17_system_state/inspect_contract.py show
    python labs/rmd17_system_state/inspect_contract.py check

`show` prints the contract. `check` recomputes the relationships that must hold
between the protocol, the development summary and the locked summary, and exits
non-zero if any of them fails.
"""

import argparse
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((LAB / name).read_text(encoding="utf-8"))


def show_observable(protocol: dict) -> None:
    """What is predicted, and which arrays are not allowed to help predict it."""
    units = protocol["units"]
    bounds = protocol["feature_and_target_boundaries"]
    print("OBSERVABLE AND FEATURE BOUNDARY")
    print(f"  target array        {bounds['target_array']}  ({units['energies']})")
    print(f"  coordinates         {units['coordinates']}")
    print(f"  forces              {units['forces']}")
    print(f"  allowed as features {', '.join(bounds['allowed_feature_arrays'])}")
    print(f"  prohibited          {', '.join(bounds['prohibited_arrays'])}")
    print("  The prohibition is the leakage rule. Every prohibited array is present")
    print("  in the source file, and two of them are the same quantity the model is")
    print("  asked to predict, recorded before the recomputation.")
    print()


def show_sampling(protocol: dict, development: dict) -> None:
    """1000 frames are a sample of a trajectory, and they are not independent."""
    sampling = protocol["sampling"]
    split = development["split"]
    frames = {system["system_id"]: system["expected_frames"] for system in protocol["systems"]}
    print("SAMPLING AND FRAME DEPENDENCE")
    print(f"  frames per system   {sorted(set(frames.values()))[0]}")
    print(f"  frames selected     {sampling['selected_frames']}")
    print(f"  rank expression     {sampling['rank_expression']}")
    print(f"  ordering            {sampling['sort']}")
    parts = split["partitions"]
    total = sum(parts.values())
    print(
        f"  partitions          train {parts['train']}, validation {parts['validation']}, "
        f"evaluation {parts['evaluation']}  (sum {total})"
    )
    for system, diagnostics in sorted(split["ordering_diagnostics_by_system"].items()):
        gap = diagnostics["adjacent_original_index_gap"]
        print(f"  {system}")
        print(
            f"    adjacent original-index gap  min {gap['minimum']}, "
            f"median {gap['median']}, max {gap['maximum']}"
        )
        print(f"    strictly increasing          {diagnostics['strictly_increasing']}")
    print("  No two selected frames are neighbours in the original trajectory, so the")
    print("  split is not trivially leaky. That is not the same as independence: the")
    print("  summary states that stable ordering does not remove time correlation.")
    print()


def show_metric_boundary(protocol: dict, development: dict, locked: dict) -> None:
    """An error is only readable next to the range it is an error over."""
    metrics = protocol["metrics"]
    print("METRIC BOUNDARY")
    print(f"  reported per system {', '.join(metrics['per_system'])}")
    print(f"  forbidden           {', '.join(metrics['forbidden'])}")
    print(f"  selection rule      {protocol['models']['selection']}")
    print(f"  selected alpha      {development['selection']['selected_alpha']}")
    print("  Development systems")
    for system, result in sorted(development["development_evaluation"].items()):
        ridge, control = result["ridge"], result["train_mean"]
        print(
            f"    {system:<15} ridge MAE {ridge['mae']:.4f}  control MAE {control['mae']:.4f}"
            f"  target range {ridge['target_range']:.4f}"
        )
    print("  Locked systems")
    for system, result in sorted(locked["results"].items()):
        ridge, control = result["ridge"], result["train_mean"]
        print(
            f"    {system:<15} ridge MAE {ridge['mae']:.4f}  control MAE {control['mae']:.4f}"
            f"  target range {ridge['target_range']:.4f}"
        )
    print("  Each error is printed beside the range it is an error over, because an")
    print("  MAE alone cannot say whether a model beat the constant it is compared to.")
    print()


def check(protocol: dict, development: dict, locked: dict) -> list[str]:
    """Recompute what must hold across the three artifacts. Returns failures."""
    failures: list[str] = []

    def record(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    version = protocol["protocol_id"]
    record(
        development["protocol_id"] == version and locked["protocol_id"] == version,
        f"all three artifacts declare protocol {version}",
    )

    bounds = protocol["feature_and_target_boundaries"]
    allowed = set(bounds["allowed_feature_arrays"])
    prohibited = set(bounds["prohibited_arrays"])
    record(
        not (allowed & prohibited) and bounds["target_array"] not in allowed,
        "allowed and prohibited arrays are disjoint and the target is not a feature",
    )
    record(
        prohibited <= set(protocol["required_npz_keys"]),
        "every prohibited array really exists in the source file rather than being hypothetical",
    )

    split = development["split"]
    record(
        sum(split["partitions"].values()) == split["selected_frames"],
        f"partitions sum to the selected frames: {sum(split['partitions'].values())}",
    )
    record(
        split["partitions"] == locked["partitions_per_system"],
        "the locked run used the development partition sizes",
    )

    bins = development["features"]["bins_per_channel"]
    for system, feature in sorted(development["features"]["by_system"].items()):
        record(
            feature["channel_count"] * bins == feature["feature_dimension"],
            f"{system} feature dimension is {feature['channel_count']} channels times "
            f"{bins} bins = {feature['feature_dimension']}",
        )

    selected = development["selection"]["selected_alpha"]
    record(
        selected in protocol["models"]["alphas"],
        "the selected alpha is a member of the frozen grid",
    )
    # The protocol rule is median validation MAE with exact ties choosing the larger alpha.
    best = min(
        development["selection"]["validation_grid"],
        key=lambda row: (row["median_validation_mae"], -row["alpha"]),
    )
    record(
        best["alpha"] == selected,
        f"selection replays to alpha {selected} from the stored validation grid",
    )
    record(
        locked["selected_alpha"] == selected,
        "the locked run reused the development alpha without reselecting",
    )
    record(
        all(
            development["software"][key] == locked["software"][key]
            for key in ("python", "numpy", "scikit_learn")
        ),
        "development and locked runs report the same python, numpy and scikit-learn",
    )

    reported = [
        (system, model)
        for system, result in locked["results"].items()
        for model, metrics in result.items()
        if "mae" not in metrics or "target_range" not in metrics
    ]
    record(
        not reported,
        "every locked result reports its error beside the target range it is measured over",
    )

    for system, diagnostics in sorted(split["ordering_diagnostics_by_system"].items()):
        record(
            diagnostics["strictly_increasing"]
            and diagnostics["adjacent_original_index_gap"]["minimum"] > 1,
            f"{system} frames are ordered and never consecutive in the original trajectory",
        )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action

    protocol = load("protocol.json")
    development = load("development-summary.json")
    locked = load("locked-summary.json")

    print(f"Frozen contract {protocol['protocol_id']}")
    print(f"source {protocol['source']['doi']} under {protocol['source']['licence']}")
    print()
    if action == "show":
        show_observable(protocol)
        show_sampling(protocol, development)
        show_metric_boundary(protocol, development, locked)
        for limitation in development["limitations"]:
            print(f"  limitation: {limitation}")
        print()
        print("Run 'check' to recompute the relationships between these artifacts.")
        return

    print("CONTRACT CHECKS")
    failures = check(protocol, development, locked)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies internal agreement, not scientific validity.")


if __name__ == "__main__":
    main()
