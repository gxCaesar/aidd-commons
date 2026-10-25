"""Inventory the counterevidence this repository preserved about its own results.

A nomination dossier is judged by what it kept, not by what it claimed. Six kinds
of counterevidence are routinely collapsed into one "limitations" paragraph and
then dropped: an evaluation declared and deliberately not run, a method that ran
and lost, a metric refused rather than filled in, a disclosure that narrows a
claim, an admitted gap in one's own records, and measurement spread retained
instead of averaged away. This command reads the completed lab artifacts
committed in this repository and separates them.

    python labs/counterevidence/inspect_dossier.py show
    python labs/counterevidence/inspect_dossier.py check

No network, no download, no third-party package, no fitting. `show` prints the
inventory and the three places where deleting one line would flip a reader's
conclusion. `check` recomputes the relationships from the committed numbers and
exits non-zero if any of them fails.
"""

import argparse
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]

# Completed lab artifacts. Every one is a reviewed summary, not a raw run log.
ARTIFACTS = {
    "chembl-locked": "labs/chembl_egfr/locked-summary.json",
    "chembl-development": "labs/chembl_egfr/development-summary.json",
    "chembl-amendment": "labs/chembl_egfr/execution-amendment.json",
    "rmd17-locked": "labs/rmd17_system_state/locked-summary.json",
    "rmd17-development": "labs/rmd17_system_state/development-summary.json",
    "pool-budget-real": "labs/pool_budget/real-summary.json",
    "pool-budget-demo": "labs/pool_budget/demo-summary.json",
    "freesolv": "labs/freesolv/reviewed-results.json",
}
DISCLOSURE_KEYS = ("interpretation", "limitations", "caveats")

CLASSES = {
    "not-run": "an evaluation declared in a protocol and deliberately not executed",
    "negative-result": "the method ran and lost to its own baseline",
    "undefined-metric": "a metric that could not be computed and was recorded as undefined",
    "scope-limit": "a disclosure that narrows what the completed result may be used for",
    "missing-record": "an admitted gap in this project's own evidence",
    "retained-noise": "measurement spread kept in the record rather than averaged away",
}


def load() -> dict[str, dict]:
    loaded = {}
    for name, relative in ARTIFACTS.items():
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"missing committed artifact: {relative}")
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def disclosures(record: dict) -> list[str]:
    return [line for key in DISCLOSURE_KEYS for line in record.get(key, [])]


def not_run_states(records: dict[str, dict]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def walk(name: str, node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(name, value, f"{path}/{key}")
        elif node == "not_run":
            found.append((name, path.lstrip("/")))

    for name, record in records.items():
        walk(name, record, "")
    return sorted(found)


def undefined_metrics(records: dict[str, dict]) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []

    def walk(name: str, node: object, path: str) -> None:
        if isinstance(node, dict):
            status = node.get("spearman_status")
            if status is not None and status != "defined":
                found.append((name, path.lstrip("/"), status))
            for key, value in node.items():
                walk(name, value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(name, value, f"{path}[{index}]")

    for name, record in records.items():
        walk(name, record, "")
    return sorted(found)


def transfer_failure(records: dict[str, dict]) -> dict:
    """The winner on one comparison, recomputed against the other."""
    results = records["chembl-locked"]["results"]
    rows = {}
    for comparison, block in results.items():
        metrics = block["metrics"]
        ranked = sorted(metrics.items(), key=lambda item: item[1]["mae"])
        rows[comparison] = {
            "count": block["count"],
            "best": ranked[0][0],
            "worst": ranked[-1][0],
            "mae": {name: values["mae"] for name, values in metrics.items()},
            "spearman": {name: values["spearman"] for name, values in metrics.items()},
        }
    return rows


def lost_policies(records: dict[str, dict]) -> dict[str, dict]:
    """Assays where the designed policy scored below every random instance."""
    lost = {}
    for assay, block in records["pool-budget-real"]["assays"].items():
        scores = {row["name"]: row["normalized_auc"] for row in block["policies"]}
        designed = scores["maxmin"]
        randoms = {name: value for name, value in scores.items() if name.startswith("random-")}
        if designed < min(randoms.values()):
            lost[assay] = {"designed": designed, "randoms": randoms}
    return lost


def two_sided(records: dict[str, dict], phrase: str) -> list[str]:
    """Artifacts disclosing the same exposure, including the one that caused it."""
    return sorted(
        name
        for name, record in records.items()
        if any(phrase in line for line in disclosures(record))
    )


def show_inventory(records: dict[str, dict]) -> None:
    print(f"PRESERVED COUNTEREVIDENCE ACROSS {len(records)} COMMITTED ARTIFACTS")
    for label, definition in CLASSES.items():
        print(f"  {label}: {definition}")
    print()

    states = not_run_states(records)
    print(f"  not-run ({len(states)})")
    for name, path in states:
        print(f"    {name:<20} {path}")

    lost = lost_policies(records)
    print(f"  negative-result ({len(lost)})")
    for assay, block in sorted(lost.items()):
        worst_random = min(block["randoms"].values())
        print(f"    {assay}  designed policy {block['designed']} below every random instance")
        print(f"      lowest random instance {worst_random}")

    undefined = undefined_metrics(records)
    print(f"  undefined-metric ({len(undefined)})")
    for name, path, status in undefined:
        print(f"    {name:<20} {path}: {status}")

    counted = sum(len(disclosures(record)) for record in records.values())
    print(f"  scope-limit, missing-record and retained-noise ({counted} disclosure lines)")
    for name in sorted(records):
        lines = disclosures(records[name])
        if lines:
            print(f"    {name} ({len(lines)})")
            for line in lines:
                print(f"      - {line}")
    print()


def show_deletions(records: dict[str, dict]) -> None:
    """The three places where deleting one line would flip a reader's conclusion."""
    print("WHAT A CLEAN SUMMARY WOULD HAVE DELETED")

    rows = transfer_failure(records)
    primary, replication = rows["primary_test"], rows["assay_replication"]
    print("  1. The winner that fails on transfer.")
    print(
        f"     On the primary test ({primary['count']} parents) the best model is {primary['best']}"
    )
    best, base = primary["mae"]["morgan_ridge"], primary["mae"]["train_mean"]
    print(f"       morgan_ridge {best} against train_mean {base}")
    print(f"     On assay replication ({replication['count']} parents) it is the worst")
    moved, baseline = replication["mae"]["morgan_ridge"], replication["mae"]["train_mean"]
    print(f"       morgan_ridge {moved} against train_mean {baseline}")
    print(
        f"       and its rank correlation turns negative: {replication['spearman']['morgan_ridge']}"
    )
    print("     Reporting the primary test alone would have been true and misleading.")

    exposure = "T15 accessed labels shared with T05"
    both = two_sided(records, exposure)
    print("  2. The disclosure that appears on both sides of the exposure.")
    print(f"     artifacts recording it: {both}")
    print("     The lab that was exposed and the lab that did the exposing both carry it.")
    print("     A one-sided disclosure would leave the second lab looking independent.")

    undefined = undefined_metrics(records)
    print("  3. The metric that was refused rather than filled in.")
    print(f"     {len(undefined)} baseline correlations are recorded as undefined, not as zero.")
    print("     A constant prediction has no rank correlation. Writing 0 there would have")
    print("     invented a comparison that the baseline cannot enter.")
    print()


def check(records: dict[str, dict]) -> list[str]:
    """Recompute the relationships from the committed numbers. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    record_result(
        len(records) == len(ARTIFACTS),
        f"all {len(ARTIFACTS)} committed lab artifacts are present and parse",
    )
    carrying = [name for name, record in records.items() if disclosures(record)]
    record_result(
        len(carrying) >= 6,
        f"{len(carrying)} of {len(records)} artifacts carry at least one disclosure line",
    )

    rows = transfer_failure(records)
    primary, replication = rows["primary_test"], rows["assay_replication"]
    record_result(
        primary["best"] == "morgan_ridge" and replication["worst"] == "morgan_ridge",
        "the model with the lowest primary-test error has the highest replication error",
    )
    ratio = replication["mae"]["morgan_ridge"] / replication["mae"]["train_mean"]
    record_result(
        ratio > 3,
        f"on replication that model is {ratio:.2f} times the train-mean error, not merely close",
    )
    record_result(
        primary["spearman"]["morgan_ridge"] > 0 > replication["spearman"]["morgan_ridge"],
        "its rank correlation is positive on the primary test and negative on replication",
    )
    record_result(
        any(
            "success on one does not erase failure on the other" in line
            for line in disclosures(records["chembl-locked"])
        ),
        "the artifact states in words that one comparison does not erase the other",
    )

    lost = lost_policies(records)
    record_result(
        len(lost) >= 1,
        f"{len(lost)} assay replays record a designed policy below every random instance",
    )
    zero = [assay for assay, block in lost.items() if block["designed"] == 0.0]
    record_result(
        len(zero) == 1,
        f"one replay records the designed policy recovering nothing at all: {zero}",
    )

    undefined = undefined_metrics(records)
    record_result(
        len(undefined) == 3
        and all(status == "undefined_constant_prediction" for _, _, status in undefined),
        f"{len(undefined)} baseline correlations are refused as undefined, not written as zero",
    )
    record_result(
        all(
            records["chembl-locked"]["results"][comparison]["metrics"]["train_mean"]["spearman"]
            is None
            for comparison in rows
        ),
        "the undefined correlations are stored as null, so no arithmetic can consume them",
    )

    both = two_sided(records, "T15 accessed labels shared with T05")
    record_result(
        len(both) == 2,
        "the shared-label exposure is disclosed on both sides,"
        f" not only by the exposed lab: {both}",
    )

    states = not_run_states(records)
    record_result(
        len(states) >= 6,
        f"{len(states)} declared evaluations are recorded as not run rather than omitted",
    )
    inferential = [
        line
        for record in records.values()
        for line in disclosures(record)
        if any(word in line.lower() for word in ("p value", "p-value", "confidence interval"))
    ]
    record_result(
        len(inferential) >= 3 and all(line.startswith("No ") for line in inferential),
        f"all {len(inferential)} lines naming p values or confidence intervals"
        " refuse them outright",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    records = load()

    print(f"Reading {len(records)} completed lab artifacts committed in this repository")
    print()
    if action == "show":
        show_inventory(records)
        show_deletions(records)
        print("Run 'check' to recompute these relationships from the committed numbers.")
        return

    print("COUNTEREVIDENCE CHECKS")
    failures = check(records)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies that the counterevidence is still present")
    print("and still says what the lessons quote, not that any result is correct.")


if __name__ == "__main__":
    main()
