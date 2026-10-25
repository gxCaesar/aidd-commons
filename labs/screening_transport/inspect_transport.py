"""Ask whether a screening result transports, and whether either context could see it.

A policy that loses in two assays looks twice as convincingly beaten as a policy
that loses in one. That inference needs two things the headline never carries:
that the contexts are independent enough for the repeat to mean anything, and
that each context has the measurement resolution to see the effect being claimed.
This command reads the completed pool-budget replay committed in this repository
and checks both.

    python labs/screening_transport/inspect_transport.py show
    python labs/screening_transport/inspect_transport.py check

No network, no download, no third-party package, no fitting. `show` prints the
two contexts side by side in units of recovered targets. `check` recomputes every
relationship from the committed numbers and exits non-zero if any of them fails.
"""

import argparse
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
REPLAY = ROOT / "labs/pool_budget/real-summary.json"
CHEMBL = ROOT / "labs/chembl_egfr/development-summary.json"


def load() -> tuple[dict, dict]:
    return (
        json.loads(REPLAY.read_text(encoding="utf-8")),
        json.loads(CHEMBL.read_text(encoding="utf-8")),
    )


def contexts(replay: dict) -> list[dict]:
    """Each assay replay, with its scores expressed in recovered-target units."""
    rows = []
    for assay, block in sorted(replay["assays"].items()):
        budget = block["budget"]
        targets = budget["top_decile_size"]
        resolution = 1 / targets
        scores = {row["name"]: row["normalized_auc"] for row in block["policies"]}
        randoms = {name: value for name, value in scores.items() if name.startswith("random-")}
        spread = max(randoms.values()) - min(randoms.values())
        rows.append(
            {
                "assay": assay,
                "pool": budget["original_pool_parent_count"],
                "targets": targets,
                "batch": budget["batch_size"],
                "acquired": budget["acquired_count"],
                "fraction": budget["actual_budget_fraction"],
                "resolution": resolution,
                "designed": scores["maxmin"],
                "randoms": randoms,
                "random_spread": spread,
                "spread_in_targets": spread / resolution,
                "designed_lost": scores["maxmin"] < min(randoms.values()),
                "gap_in_targets": (min(randoms.values()) - scores["maxmin"]) / resolution,
            }
        )
    return rows


def independence(chembl: dict) -> dict:
    """What the two contexts share, which is what decides whether a repeat counts."""
    data = chembl["data"]
    return {
        "parent_overlap": data["parent_overlap"],
        "primary_assay": data["primary"]["assay_chembl_id"],
        "replication_assay": data["replication"]["assay_chembl_id"],
    }


def show_contexts(rows: list[dict], shared: dict) -> None:
    """The two contexts in the only unit that makes them comparable."""
    print("TWO SCREENING CONTEXTS, SAME PROTOCOL")
    for row in rows:
        print(f"  {row['assay']}")
        print(
            f"    pool {row['pool']} parents, {row['targets']} targets,"
            f" batch {row['batch']}, acquired {row['acquired']}"
        )
        print(f"    realised budget fraction {row['fraction']}")
        print(
            f"    one recovered target moves the score by {row['resolution']:.6f},"
            f" which is this context's resolution"
        )
        print(f"    designed policy {row['designed']}")
        randoms = ", ".join(f"{value}" for _, value in sorted(row["randoms"].items()))
        print(f"    random instances {randoms}")
    print()

    print("ENRICHMENT WITHOUT ITS DENOMINATOR IS UNREADABLE")
    coarse, fine = (
        max(rows, key=lambda r: r["resolution"]),
        min(rows, key=lambda r: r["resolution"]),
    )
    ratio = coarse["resolution"] / fine["resolution"]
    print(
        f"  {fine['assay']} carries {fine['targets']} targets,"
        f" {coarse['assay']} carries {coarse['targets']}."
    )
    print(f"  The coarser context measures recovery in steps {ratio:.2f} times larger.")
    print("  The same reported number therefore means a different amount of evidence in each,")
    print("  and neither is readable without the target count printed beside it.")
    print()

    print("THE BASELINE RANGE IS ABOUT ONE TARGET WIDE, IN BOTH")
    for row in rows:
        print(
            f"  {row['assay']}: five random instances span {row['random_spread']:.6f},"
            f" which is {row['spread_in_targets']:.2f} recovered targets"
        )
    print("  A range that narrow is describing the arithmetic of a small target set, not")
    print("  the variability of a population. It cannot carry an error bar.")
    print()


def show_transport(rows: list[dict], shared: dict) -> None:
    """Repeating is not transporting."""
    print("DID THE RESULT TRANSPORT, OR ONLY REPEAT?")
    lost = [row["assay"] for row in rows if row["designed_lost"]]
    print(
        f"  The designed policy scored below every random instance in"
        f" {len(lost)} of {len(rows)} contexts."
    )
    for row in rows:
        print(
            f"    {row['assay']}: behind the worst random instance by"
            f" {row['gap_in_targets']:.2f} recovered targets"
        )
    dramatic = min(rows, key=lambda r: r["gap_in_targets"])
    print()
    print("  Read those two margins again before believing the headline.")
    print(
        f"    In {dramatic['assay']} the designed policy recovered nothing at all,"
        f" which sounds total."
    )
    print(
        f"    It lost to the worst random instance by {dramatic['gap_in_targets']:.2f}"
        " of a single target."
    )
    print("    The most dramatic-sounding outcome carries the least evidence here, because")
    print("    a context with few targets produces large-looking scores from small counts.")
    print()
    print("  What makes the repeat worth something:")
    print(f"    the two assays share {shared['parent_overlap']} parent compounds, so the")
    print("    chemistry is disjoint rather than the same molecules measured twice.")
    print()
    print("  What holds the repeat back, from the record's own disclosures:")
    print("    both replays are retrospective on the same target, under one frozen protocol,")
    print("    with one feature set and a penalty informed by an earlier lab. A repeat under")
    print("    a shared protocol tests the policy in a second chemistry, not in a second world.")
    print()
    print("  And the resolution question comes first. A context can only support a claim")
    print("  it can measure, so the gap above should be read in recovered targets rather")
    print("  than in score units, in both directions.")
    print()


def show_limits() -> None:
    print("WHAT THIS CANNOT ADDRESS")
    print("  Off-targets. Both replays are assays on the same target, so nothing here")
    print("  speaks to selectivity or to activity somewhere unintended. The topic names")
    print("  off-targets and this evidence does not reach them.")
    print("  Prospective follow-up. Both replays are retrospective on completed")
    print("  measurements. No compound was acquired, and no experiment was run.")
    print()


def check(replay: dict, chembl: dict) -> list[str]:
    """Recompute every relationship from the committed numbers. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    rows = contexts(replay)
    shared = independence(chembl)

    record_result(len(rows) == 2, f"the replay carries {len(rows)} assay contexts")
    record_result(
        all(row["resolution"] == 1 / row["targets"] for row in rows),
        "each context's resolution is one over its target count, not a chosen constant",
    )
    coarse = max(rows, key=lambda r: r["resolution"])
    fine = min(rows, key=lambda r: r["resolution"])
    ratio = coarse["resolution"] / fine["resolution"]
    record_result(
        ratio > 4,
        f"the two contexts differ in measurement resolution by {ratio:.2f} times,"
        f" {fine['targets']} targets against {coarse['targets']}",
    )
    record_result(
        all(row["spread_in_targets"] < 2 for row in rows),
        "in both contexts the whole five-instance spread is under two recovered targets: "
        + ", ".join(f"{row['spread_in_targets']:.2f}" for row in rows),
    )
    record_result(
        all(row["designed_lost"] for row in rows),
        f"the designed policy lost in every context: {[row['assay'] for row in rows]}",
    )
    zero = [row["assay"] for row in rows if row["designed"] == 0.0]
    record_result(
        len(zero) == 1,
        f"it recovered nothing at all in exactly one context: {zero}",
    )
    record_result(
        shared["parent_overlap"] == 0,
        f"the two contexts share {shared['parent_overlap']} parent compounds,"
        " so the repeat is over disjoint chemistry",
    )
    record_result(
        shared["primary_assay"] != shared["replication_assay"],
        "the two contexts are different assays,"
        f" {shared['primary_assay']} and {shared['replication_assay']}",
    )
    record_result(
        all(0 < row["fraction"] < 0.2 for row in rows),
        "neither realised budget reaches the nominal fifth, because batch sizes are floored: "
        + ", ".join(f"{row['fraction']:.6f}" for row in rows),
    )
    record_result(
        all(row["gap_in_targets"] < 2 for row in rows),
        "the losing margin is under two recovered targets in both contexts: "
        + ", ".join(f"{row['gap_in_targets']:.2f}" for row in rows),
    )
    record_result(
        all(len(row["randoms"]) == 5 for row in rows),
        "each context carries five fixed random instances, which are policy instances"
        " rather than replicates",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    replay, chembl = load()

    print(f"Replay {REPLAY.relative_to(ROOT)}")
    print(f"Context independence from {CHEMBL.relative_to(ROOT)}")
    print()
    if action == "show":
        rows, shared = contexts(replay), independence(chembl)
        show_contexts(rows, shared)
        show_transport(rows, shared)
        show_limits()
        print("Run 'check' to recompute these relationships from the committed numbers.")
        return

    print("TRANSPORT CHECKS")
    failures = check(replay, chembl)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies what the two contexts can and cannot support,")
    print("not that either result is correct and not that any policy is better.")


if __name__ == "__main__":
    main()
