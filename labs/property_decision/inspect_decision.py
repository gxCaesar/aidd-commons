"""Turn calibrated property evidence into a threshold decision, including abstention.

A point prediction always yields a decision. An interval does not. This command
reads the completed FreeSolv baselines committed in this repository, applies a
frozen threshold rule that requires the interval to clear the threshold, and
reports the region where no decision is available.

    python labs/property_decision/inspect_decision.py evidence
    python labs/property_decision/inspect_decision.py decide
    python labs/property_decision/inspect_decision.py check

No network, no download, no third-party package, no fitting. `evidence` prints
the calibrated evidence beside the nominal coverage it was built to reach.
`decide` applies the frozen rule. `check` recomputes every relationship from the
committed numbers and exits non-zero if any of them fails.
"""

import argparse
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
RULE = LAB / "decision-rule.json"


def load() -> tuple[dict, dict, float]:
    rule = json.loads(RULE.read_text(encoding="utf-8"))
    source = rule["evidence_source"]
    results = json.loads((ROOT / source["reviewed_results"]).read_text(encoding="utf-8"))
    metrics = json.loads((ROOT / source["protocol_metrics"]).read_text(encoding="utf-8"))
    nominal = metrics["protocol"]["conformal_coverage"]
    return rule, results, nominal


def combinations(results: dict, nominal: float) -> list[dict]:
    """Every split and model that carries both a point metric and an interval."""
    rows = []
    for split, block in results["splits"].items():
        for model, interval in block["interval_metrics"].items():
            rows.append(
                {
                    "split": split,
                    "model": model,
                    "mae": block["point_metrics"][model]["mae"],
                    "radius": interval["radius"],
                    "band": 2 * interval["radius"],
                    "coverage": interval["coverage"],
                    "shortfall": nominal - interval["coverage"],
                    "meets_nominal": interval["coverage"] >= nominal,
                }
            )
    return sorted(rows, key=lambda row: (row["split"], row["model"]))


def grid_points(rule: dict) -> list[float]:
    spec = rule["prediction_grid"]
    count = round((spec["maximum"] - spec["minimum"]) / spec["step"]) + 1
    return [round(spec["minimum"] + index * spec["step"], 10) for index in range(count)]


def decide_one(prediction: float, threshold: float, radius: float) -> str:
    if prediction + radius < threshold:
        return "advance"
    if prediction - radius > threshold:
        return "reject"
    return "abstain"


def decisions(rule: dict, row: dict) -> dict:
    threshold = rule["threshold"]["value"]
    counts = {"advance": 0, "reject": 0, "abstain": 0}
    point_counts = {"advance": 0, "reject": 0, "abstain": 0}
    for prediction in grid_points(rule):
        counts[decide_one(prediction, threshold, row["radius"])] += 1
        # The comparison arm: a point estimate never abstains.
        point_counts["advance" if prediction < threshold else "reject"] += 1
    total = sum(counts.values())
    return {
        "counts": counts,
        "point_counts": point_counts,
        "total": total,
        "decidable": total - counts["abstain"],
        "band_low": threshold - row["radius"],
        "band_high": threshold + row["radius"],
    }


def ranking_flip(rows: list[dict]) -> dict[str, dict]:
    """Where the point criterion and the interval criterion disagree."""
    flips = {}
    for split in sorted({row["split"] for row in rows}):
        members = [row for row in rows if row["split"] == split]
        by_point = min(members, key=lambda row: row["mae"])
        by_interval = max(members, key=lambda row: (row["meets_nominal"], -abs(row["shortfall"])))
        flips[split] = {
            "point_choice": by_point["model"],
            "interval_choice": by_interval["model"],
            "flipped": by_point["model"] != by_interval["model"],
        }
    return flips


def show_evidence(rule: dict, rows: list[dict], nominal: float) -> None:
    """The calibrated evidence, beside the coverage it was built to reach."""
    source = rule["evidence_source"]
    print(f"CALIBRATED EVIDENCE  endpoint: {source['endpoint']}")
    print(f"  intervals: {source['interval_construction']}, nominal coverage {nominal}")
    print()
    print(
        f"  {'split':<9} {'model':<22} {'MAE':>7} {'radius':>7} {'band':>7}"
        f" {'coverage':>9} {'shortfall':>13}"
    )
    for row in rows:
        mark = "meets" if row["meets_nominal"] else "short"
        print(
            f"  {row['split']:<9} {row['model']:<22} {row['mae']:7.4f} {row['radius']:7.4f}"
            f" {row['band']:7.4f} {row['coverage']:9.4f} {mark:>7} {row['shortfall']:+.4f}"
        )
    print()
    meeting = [row for row in rows if row["meets_nominal"]]
    print(
        f"  {len(meeting)} of {len(rows)} combinations reach the nominal coverage"
        " they were built for."
    )
    for row in meeting:
        print(
            f"    {row['split']} {row['model']}: coverage {row['coverage']}, band {row['band']:.4f}"
        )
    widest = max(rows, key=lambda row: row["band"])
    narrowest = min(rows, key=lambda row: row["band"])
    print(
        f"  The widest band belongs to {widest['split']} {widest['model']} ({widest['band']:.4f}),"
    )
    print("  and it is the combination that meets nominal coverage.")
    print(
        f"  The narrowest belongs to {narrowest['split']} {narrowest['model']}"
        f" ({narrowest['band']:.4f}),"
    )
    print(
        f"  whose coverage falls short by {narrowest['shortfall']:.4f}. A tighter interval is not"
    )
    print("  a better interval unless it still covers.")
    print()


def show_decisions(rule: dict, rows: list[dict]) -> None:
    """Apply the frozen rule and show what a point estimate would have hidden."""
    threshold = rule["threshold"]["value"]
    grid = grid_points(rule)
    print(
        f"FROZEN RULE {rule['rule_id']}  threshold {threshold} kcal/mol,"
        f" {rule['threshold']['direction']}"
    )
    print(f"  {rule['threshold']['how_this_value_was_chosen']}")
    print(f"  grid: {len(grid)} points from {grid[0]} to {grid[-1]}")
    print(f"  {rule['prediction_grid']['what_this_grid_is']}")
    print()
    print(
        f"  {'split':<9} {'model':<22} {'advance':>8} {'reject':>7} {'abstain':>8}"
        f" {'decidable':>10}   abstention band"
    )
    for row in rows:
        outcome = decisions(rule, row)
        counts = outcome["counts"]
        band = f"[{outcome['band_low']:.4f}, {outcome['band_high']:.4f}]"
        print(
            f"  {row['split']:<9} {row['model']:<22} {counts['advance']:>8} {counts['reject']:>7}"
            f" {counts['abstain']:>8} {outcome['decidable']:>10}   {band}"
        )
    print()

    sample = decisions(rule, rows[0])
    print("WHAT A POINT ESTIMATE WOULD HAVE HIDDEN")
    print(
        f"  Applied to the point prediction alone, every one of the {sample['total']} grid points"
    )
    print("  receives a decision, because a number is always on one side of a threshold.")
    print("  Requiring the interval to clear the threshold removes that guarantee, and the")
    print("  removed region is exactly the abstention band, two radii wide.")
    print()

    print("MORE TRUSTWORTHY INTERVALS DECIDE LESS")
    ordered = sorted(rows, key=lambda row: row["band"])
    for row in ordered:
        outcome = decisions(rule, row)
        mark = "meets nominal" if row["meets_nominal"] else f"short by {row['shortfall']:.4f}"
        print(
            f"  {row['split']:<9} {row['model']:<22} abstains on {outcome['counts']['abstain']:>2}"
            f" of {outcome['total']}   coverage {mark}"
        )
    print("  The combination that reaches its nominal coverage abstains the most. That is")
    print("  the trade-off the threshold hides: deciding more is not the same as being right")
    print("  more often, and the split that looks easier buys its confidence on credit.")
    print()

    flips = ranking_flip(rows)
    print("THE TWO CRITERIA DISAGREE, ON BOTH SPLITS")
    for split, flip in flips.items():
        print(
            f"  {split}: lowest error picks {flip['point_choice']},"
            f" coverage picks {flip['interval_choice']}"
        )
    print(f"  {rule['selection_between_models']['why_both_are_declared']}")
    print()
    print(f"  {rule['what_a_decision_here_does_not_mean']}")
    print()


def show_limits() -> None:
    print("WHAT THIS CANNOT COMPUTE")
    print("  How many real compounds fall inside the abstention band. The completed lab")
    print("  committed aggregate metrics and split membership, not per-compound test")
    print("  predictions, so the band can be measured on the prediction axis but not")
    print("  populated. The grid counts are arithmetic over a declared range, not a")
    print("  sample of molecules, and must not be read as a yield.")
    print()


def check(rule: dict, results: dict, nominal: float) -> list[str]:
    """Recompute every relationship from the committed numbers. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    for field in ("threshold", "decision_rule", "prediction_grid", "selection_between_models"):
        record_result(bool(rule.get(field)), f"the frozen rule declares its {field}")
    record_result(
        bool(rule["threshold"].get("how_this_value_was_chosen")),
        "the rule states how the threshold value was chosen, so it is not presented as derived",
    )
    record_result(
        bool(rule["decision_rule"].get("abstain")),
        "the rule declares an abstention outcome rather than only advance and reject",
    )
    if failures:
        print("  ....  the rule is incomplete, so it is not applied to the evidence")
        return failures

    rows = combinations(results, nominal)
    record_result(
        len(rows) == 4, f"the committed results carry {len(rows)} split and model combinations"
    )
    record_result(
        all(row["band"] == 2 * row["radius"] for row in rows),
        "every abstention band is exactly two conformal radii wide",
    )
    meeting = [row for row in rows if row["meets_nominal"]]
    record_result(
        len(meeting) == 1,
        f"exactly one combination reaches nominal coverage {nominal}:"
        f" {[(row['split'], row['model']) for row in meeting]}",
    )
    widest = max(rows, key=lambda row: row["band"])
    record_result(
        meeting
        and widest["split"] == meeting[0]["split"]
        and widest["model"] == meeting[0]["model"],
        "the only combination that covers is also the one with the widest band",
    )
    narrowest = min(rows, key=lambda row: row["band"])
    record_result(
        narrowest["shortfall"] == max(row["shortfall"] for row in rows),
        f"the narrowest band has the largest coverage shortfall: {narrowest['shortfall']:.4f}",
    )

    grid = grid_points(rule)
    spec = rule["prediction_grid"]
    record_result(
        grid[0] == spec["minimum"] and grid[-1] == spec["maximum"],
        f"the declared grid spans its stated range with {len(grid)} points",
    )
    threshold = rule["threshold"]["value"]
    for row in rows:
        outcome = decisions(rule, row)
        if sum(outcome["counts"].values()) != len(grid):
            record_result(
                False, f"{row['split']} {row['model']} decisions do not partition the grid"
            )
            break
    else:
        record_result(True, "every grid point receives exactly one outcome under the interval rule")
    record_result(
        all(sum(decisions(rule, row)["point_counts"].values()) == len(grid) for row in rows)
        and all(decisions(rule, row)["point_counts"]["abstain"] == 0 for row in rows),
        "the point-estimate arm never abstains, which is what makes the band invisible",
    )
    record_result(
        all(
            decisions(rule, row)["counts"]["abstain"] > 1
            and decisions(rule, row)["decidable"] < len(grid)
            for row in rows
        ),
        "every combination has an abstention band wider than a single grid point,"
        " so a zero radius cannot pass as a decisive model",
    )
    covering = decisions(rule, meeting[0])["counts"]["abstain"]
    others = [decisions(rule, row)["counts"]["abstain"] for row in rows if row is not meeting[0]]
    record_result(
        covering >= max(others),
        "the combination that covers abstains at least as often as the rest:"
        f" {covering} against {sorted(others)}",
    )
    for row in rows:
        outcome = decisions(rule, row)
        low, high = outcome["band_low"], outcome["band_high"]
        if not all(
            decide_one(point, threshold, row["radius"]) == "abstain"
            for point in grid
            if low <= point <= high
        ):
            record_result(
                False, f"{row['split']} {row['model']} band bounds disagree with its outcomes"
            )
            break
    else:
        record_result(True, "the printed band bounds contain exactly the abstaining grid points")

    by_band = sorted(rows, key=lambda row: row["band"])
    shortfalls = [row["shortfall"] for row in by_band]
    record_result(
        all(later <= earlier for earlier, later in zip(shortfalls, shortfalls[1:], strict=False)),
        "coverage shortfall falls monotonically as the band widens:"
        f" {[round(v, 4) for v in shortfalls]}",
    )

    flips = ranking_flip(rows)
    record_result(
        all(flip["flipped"] for flip in flips.values()),
        f"the point and interval criteria disagree on every split: {sorted(flips)}",
    )
    record_result(
        len({flip["point_choice"] for flip in flips.values()}) == 1
        and len({flip["interval_choice"] for flip in flips.values()}) == 1,
        "the disagreement points the same way on both splits, so it is not a split artefact",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", nargs="?", default="evidence", choices=["evidence", "decide", "check"]
    )
    action = parser.parse_args().action
    rule, results, nominal = load()
    rows = combinations(results, nominal)

    print(f"Rule {RULE.relative_to(ROOT)} frozen {rule['frozen_on']}")
    print(f"Evidence {rule['evidence_source']['reviewed_results']}")
    print()
    if action == "evidence":
        show_evidence(rule, rows, nominal)
        print("Run 'decide' to apply the frozen threshold rule.")
        return
    if action == "decide":
        show_decisions(rule, rows)
        show_limits()
        print("Run 'check' to recompute these counts from the committed numbers.")
        return

    print("DECISION CHECKS")
    failures = check(rule, results, nominal)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies that the rule is complete and was applied as")
    print("frozen. It establishes nothing about the threshold or about any compound.")


if __name__ == "__main__":
    main()
