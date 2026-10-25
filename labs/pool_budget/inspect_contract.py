"""Read the frozen pool-budget contract and recompute the reported campaign numbers.

This command needs no network, no download and no third-party package. It reads
only the JSON committed beside it. It answers what a budgeted acquisition study
has to declare before it runs: how the budget is derived, what the policies are
allowed to see, when a prediction is locked relative to the labels, and how the
headline recovery number is computed from the raw series.

    python labs/pool_budget/inspect_contract.py show
    python labs/pool_budget/inspect_contract.py check

`show` prints the contract and the completed campaign. `check` recomputes the
budget arithmetic and the reported recovery AUC from the per-checkpoint series,
and exits non-zero if any relationship fails.
"""

import argparse
import json
import math
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((LAB / name).read_text(encoding="utf-8"))


def recovery_auc(recovery: list[float]) -> float:
    """Trapezoidal area over checkpoint index, divided by the interval count."""
    pairs = zip(recovery, recovery[1:], strict=False)
    return sum((first + second) / 2 for first, second in pairs) / (len(recovery) - 1)


def show_policy_access(protocol: dict) -> None:
    """What each policy is allowed to see, and what a seed is not."""
    acquisition = protocol["acquisition_contract"]
    policies = acquisition["policies"]
    print("POLICY ACCESS AND WHAT A SEED IS")
    print(f"  batch size rule   {acquisition['batch_size']}")
    print(f"  rounds            {acquisition['round_count']}")
    print(f"  checkpoints       {acquisition['checkpoint_acquired_counts']}")
    print(f"  random seeds      {policies['random']['seeds']}")
    print(f"  seed meaning      {policies['random']['interpretation']}")
    print(f"  maxmin access     {policies['maxmin']['label_access']}")
    print("  The five seeds are five fixed policy instances. Their spread is not a")
    print("  confidence interval, because they resample the policy and not the assay.")
    print()


def show_locking(protocol: dict) -> None:
    """The order of fitting, locking and scoring is the whole anti-feedback rule."""
    prediction = protocol["prediction_contract"]
    model = prediction["model"]
    print("FIT, LOCK, THEN SCORE")
    print(f"  purpose   {prediction['purpose']}")
    print(f"  model     {model['family']} alpha {model['alpha']}, tuning {model['tuning']}")
    for step, sentence in enumerate(prediction["fit_and_lock_sequence"], start=1):
        print(f"  step {step}    {sentence}")
    print()


def show_campaign(summary: dict) -> None:
    """The completed retrospective replay, including the result that went against us."""
    print("COMPLETED CAMPAIGN")
    for assay, block in sorted(summary["assays"].items()):
        budget = block["budget"]
        parts = block["partitions"]
        print(f"  {assay}")
        print(
            f"    partitions      initial {parts['initial']['parents']}, "
            f"pool {parts['pool']['parents']}, evaluation {parts['evaluation']['parents']}"
        )
        print(
            f"    budget          batch {budget['batch_size']}, acquired "
            f"{budget['acquired_count']} of {budget['original_pool_parent_count']} "
            f"({budget['actual_budget_fraction']:.6f})"
        )
        print(f"    target count    {budget['top_decile_size']}")
        for policy in block["policies"]:
            print(
                f"    {policy['name']:<10} recovery AUC {policy['normalized_auc']:.9f}  "
                f"final recovery {policy['recovery'][-1]:.6f}  "
                f"final eval MAE {policy['evaluation_mae'][-1]:.6f}"
            )
        maxmin = next(p for p in block["policies"] if p["name"] == "maxmin")
        randoms = [p for p in block["policies"] if p["name"].startswith("random")]
        beaten = sum(1 for r in randoms if r["normalized_auc"] > maxmin["normalized_auc"])
        print(
            f"    The diversity policy is below {beaten} of {len(randoms)} fixed random "
            "instances here. That result is retained, not reframed."
        )
    print()


def check(protocol: dict, summary: dict) -> list[str]:
    """Recompute the budget arithmetic and the headline numbers. Returns failures."""
    failures: list[str] = []

    def record(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    record(
        protocol["protocol_id"] == summary["protocol_id"],
        f"both artifacts declare protocol {protocol['protocol_id']}",
    )

    replays = protocol["frozen_t05_reference"]["assay_replays"]
    for assay, block in sorted(summary["assays"].items()):
        budget = block["budget"]
        pool = budget["original_pool_parent_count"]
        batch = pool // 20

        record(
            budget["batch_size"] == batch,
            f"{assay} batch size is floor({pool} / 20) = {batch}",
        )
        record(
            budget["checkpoints"] == [index * batch for index in range(5)],
            f"{assay} checkpoints are the four rounds of {batch}",
        )
        record(
            budget["acquired_count"] == 4 * batch,
            f"{assay} acquired count is four batches = {4 * batch}",
        )
        record(
            budget["top_decile_size"] == math.ceil(pool / 10),
            f"{assay} target count is ceil({pool} / 10) = {math.ceil(pool / 10)}",
        )
        record(
            abs(budget["actual_budget_fraction"] - budget["acquired_count"] / pool) < 1e-12,
            f"{assay} reported budget fraction equals acquired over pool,"
            " not the nominal 20 percent",
        )

        parents = sum(part["parents"] for part in block["partitions"].values())
        expected = replays[assay]["expected_parent_count"]
        record(
            parents == expected,
            f"{assay} partitions sum to the {expected} parents inherited from the frozen contract",
        )

        first_predictions = {policy["evaluation_mae"][0] for policy in block["policies"]}
        record(
            len(first_predictions) == 1,
            f"{assay} every policy shares the checkpoint-zero error, so the initial set is common",
        )

        for policy in block["policies"]:
            series = (policy["recovery"], policy["evaluation_mae"], policy["scaffold_fraction"])
            record(
                all(len(item) == len(budget["checkpoints"]) for item in series),
                f"{assay} {policy['name']} reports every series at all"
                f" {len(budget['checkpoints'])} checkpoints",
            )
            record(
                all(
                    earlier <= later
                    for earlier, later in zip(
                        policy["recovery"], policy["recovery"][1:], strict=False
                    )
                ),
                f"{assay} {policy['name']} recovery never decreases,"
                " so selection is without replacement",
            )
            record(
                abs(policy["normalized_auc"] - recovery_auc(policy["recovery"])) < 1e-12,
                f"{assay} {policy['name']} recovery AUC recomputes from its own checkpoint series",
            )

        seeds = protocol["acquisition_contract"]["policies"]["random"]["seeds"]
        named = {policy["name"] for policy in block["policies"]}
        record(
            named == {"maxmin"} | {f"random-{seed}" for seed in seeds},
            f"{assay} reports the diversity policy against all {len(seeds)} declared seeds",
        )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action

    protocol = load("real-protocol.json")
    summary = load("real-summary.json")

    print(f"Frozen contract {protocol['protocol_id']} issued {protocol['issued_on']}")
    print(f"campaign completed {summary['completed_on']} as {summary['data_kind']}")
    print()
    if action == "show":
        show_policy_access(protocol)
        show_locking(protocol)
        show_campaign(summary)
        print("Run 'check' to recompute the budget arithmetic and the reported AUC.")
        return

    print("CONTRACT CHECKS")
    failures = check(protocol, summary)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies internal agreement, not scientific validity.")


if __name__ == "__main__":
    main()
