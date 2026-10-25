"""Separate the five kinds of safety evidence that a tox profile prints in one column.

A structural alert, an assay outcome, an organ liability, a dose context and an
organism-level finding are five different claims obtained five different ways.
They arrive side by side on a profile page and are read as one gradient of
badness. This command reads a committed record that stores findings but never
stores an alert, computes the alerts from the structures, and reports where the
levels disagree.

    python labs/safety_evidence/inspect_safety.py show
    python labs/safety_evidence/inspect_safety.py check

Reads one committed JSON file and uses RDKit for substructure matching. No
outcome here is a real result and nothing is a safety assessment of any
substance.
"""

import argparse
import json
import sys
from pathlib import Path

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DATASET = LAB / "dataset.json"
MEASURED_LEVELS = ("assay-outcome", "organ-liability", "organism-level")


def load() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def alerts_for(data: dict, smiles: str) -> list[str]:
    """Computed, never read from the record."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"unparsable structure in the committed dataset: {smiles}")
    return sorted(
        name
        for name, pattern in data["alerts"]["patterns"].items()
        if mol.HasSubstructMatch(Chem.MolFromSmarts(pattern))
    )


def findings_at(compound: dict, level: str) -> list[dict]:
    return [row for row in compound["findings"] if row["level"] == level]


def profile(data: dict, compound: dict) -> dict:
    fired = alerts_for(data, compound["smiles"])
    measured = compound["findings"]
    positives = [row for row in measured if row["outcome"] == "positive"]
    return {
        "id": compound["id"],
        "alerts": fired,
        "alert_count": len(fired),
        "findings": len(measured),
        "positive_findings": len(positives),
        "levels": sorted({row["level"] for row in measured}),
        "has_organism_level": bool(findings_at(compound, "organism-level")),
        "without_concentration": [
            row
            for row in measured
            if row["level"] == "assay-outcome" and row["concentration_micromolar"] is None
        ],
    }


def disagreements(data: dict) -> dict[str, list[str]]:
    """The two directions in which an alert and a measurement fail to agree."""
    contradicted, untested, positive_no_alert = [], [], []
    for compound in data["compounds"]:
        row = profile(data, compound)
        if row["alerts"] and row["positive_findings"] == 0:
            # An alert contradicted by a measurement is not the same as an alert
            # nobody checked, and collapsing them is how an alert keeps its authority.
            (contradicted if row["findings"] else untested).append(row["id"])
        if not row["alerts"] and row["positive_findings"] > 0:
            positive_no_alert.append(row["id"])
    return {
        "alert_contradicted": contradicted,
        "alert_untested": untested,
        "positive_without_alert": positive_no_alert,
    }


def show(data: dict) -> None:
    rows = [profile(data, compound) for compound in data["compounds"]]
    print("FIVE LEVELS, AND HOW EACH ONE IS OBTAINED")
    for name, spec in data["levels"].items():
        mark = "computed here" if spec["computed_here"] else "requires an experiment"
        print(f"  {name:<17} {mark:<22} {spec['obtained_by']}")
    print()

    print(f"THE PROFILE PAGE  {len(rows)} compounds")
    print(f"  {'id':<5} {'alerts':>7} {'findings':>9} {'positive':>9}   levels present")
    for row in rows:
        print(
            f"  {row['id']:<5} {row['alert_count']:>7} {row['findings']:>9}"
            f" {row['positive_findings']:>9}   {', '.join(row['levels']) or '-'}"
        )
    print()

    alerting = [row for row in rows if row["alerts"]]
    silent = [row for row in alerting if row["findings"] == 0]
    print("AN ALERT IS NOT A FINDING")
    print(f"  {len(alerting)} of {len(rows)} compounds match at least one alert.")
    print(f"  {len(silent)} of those carry no measured finding at all: {[r['id'] for r in silent]}")
    print("  Their entire safety record is a pattern match. Nobody ran anything, and")
    print("  a profile column that prints an alert beside an assay result says otherwise.")
    multi = [row for row in rows if row["alert_count"] > 1]
    if multi:
        print(f"  {len(multi)} compound matches more than one alert: {[r['id'] for r in multi]}.")
        print("  The alert count went up. The evidence did not.")
    print()

    both = disagreements(data)
    print("THE LEVELS DISAGREE, IN BOTH DIRECTIONS")
    print(f"  alert fired and a measurement said negative: {both['alert_contradicted']}")
    print(f"  alert fired and nobody measured anything:    {both['alert_untested']}")
    print(f"  no alert and something measured positive:    {both['positive_without_alert']}")
    print("  The first two are different situations. An alert a measurement contradicted")
    print("  has been tested and lost. An alert nobody checked has not been tested at all,")
    print("  and printing them the same way is how an alert keeps authority it never earned.")
    print("  So an alert is not a prediction of a finding, and the absence of an alert")
    print("  is not a prediction of nothing. Neither direction survives contact with")
    print("  the measurements in this record.")
    print()


def show_dose(data: dict) -> None:
    rows = [profile(data, compound) for compound in data["compounds"]]
    assays = [
        row for compound in data["compounds"] for row in findings_at(compound, "assay-outcome")
    ]
    missing = [row for row in assays if row["concentration_micromolar"] is None]
    concentrations = sorted(
        row["concentration_micromolar"] for row in assays if row["concentration_micromolar"]
    )
    print("WITHOUT A DOSE CONTEXT NONE OF IT IS A RISK STATEMENT")
    print(f"  {len(assays)} assay outcomes recorded, {len(missing)} of them with no concentration.")
    if concentrations:
        print(
            f"  Recorded concentrations span {concentrations[0]} to {concentrations[-1]}"
            f" micromolar, a factor of {concentrations[-1] / concentrations[0]:.0f}."
        )
    print(f"  exposure declared anywhere in the record: {data['exposure']['declared']}")
    print(f"  {data['exposure']['why_it_matters']}")
    print()

    top = [row for row in rows if row["has_organism_level"]]
    print("THE LEVEL THAT WOULD SETTLE IT IS THE ONE ALMOST NOTHING HAS")
    print(
        f"  {len(top)} of {len(rows)} compounds carry any organism-level evidence: "
        f"{[r['id'] for r in top]}"
    )
    print("  That is the ordinary shape of a safety record and not a defect in this one.")
    print("  Alerts are free, assays are cheap, organisms are expensive, and the profile")
    print("  page gives all three the same amount of space.")
    print()


def show_limits() -> None:
    print("WHAT THIS DOES NOT DO")
    print("  It assesses nothing. No compound here was tested, no outcome is real, and")
    print("  no statement about any substance can be taken from this file.")
    print("  It also does not say alerts are useless. An alert is a cheap prompt to look,")
    print("  and looking is what the other four levels are. The failure is printing a")
    print("  prompt to look in the same column as the result of having looked.")
    print()


def check(data: dict) -> list[str]:
    """Recompute every relationship from the committed record. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    record_result(
        len(data["levels"]) == 4 and "molecular-alert" in data["levels"],
        f"the record names every level and how each is obtained: {sorted(data['levels'])}",
    )
    record_result(
        data["levels"]["molecular-alert"]["computed_here"] is True
        and all(data["levels"][level]["computed_here"] is False for level in MEASURED_LEVELS),
        "only the alert level is computed here, and the rest are marked as requiring an experiment",
    )
    alert_names = set(data["alerts"]["patterns"])
    compound_keys = {key for compound in data["compounds"] for key in compound}
    finding_systems = {
        row["system"] for compound in data["compounds"] for row in compound["findings"]
    }
    record_result(
        not (compound_keys & {"alert", "alerts"}) and not (finding_systems & alert_names),
        "no compound stores an alert and no finding is recorded against one, because"
        " storing an alert beside a measurement is the collapse this lab is about",
    )
    record_result(
        all(
            row["level"] in MEASURED_LEVELS
            for compound in data["compounds"]
            for row in compound["findings"]
        ),
        "every stored finding is at a level that required an experiment",
    )
    broken = [
        name
        for name, pattern in data["alerts"]["patterns"].items()
        if Chem.MolFromSmarts(pattern) is None
    ]
    record_result(not broken, f"every alert pattern compiles, broken {broken}")
    if failures:
        print(
            "  ....  the record is not readable as five separated levels, so it is not summarised"
        )
        return failures

    rows = [profile(data, compound) for compound in data["compounds"]]
    alerting = [row for row in rows if row["alerts"]]
    record_result(
        0 < len(alerting) < len(rows),
        f"{len(alerting)} of {len(rows)} compounds match an alert, so the set separates",
    )
    silent = [row for row in alerting if row["findings"] == 0]
    record_result(
        len(silent) > 0,
        f"{len(silent)} alerting compounds carry no measured finding at all, so their"
        f" whole safety record is a pattern match: {[r['id'] for r in silent]}",
    )
    multi = [row for row in rows if row["alert_count"] > 1]
    record_result(
        len(multi) > 0 and all(row["findings"] == 0 for row in multi),
        f"a compound matches more than one alert while carrying no finding, so the"
        f" alert count rose without evidence: {[r['id'] for r in multi]}",
    )

    both = disagreements(data)
    record_result(
        len(both["alert_contradicted"]) > 0,
        f"at least one alert is contradicted by a measurement: {both['alert_contradicted']}",
    )
    record_result(
        len(both["positive_without_alert"]) > 0,
        f"at least one positive finding has no alert at all: {both['positive_without_alert']}",
    )
    record_result(
        bool(both["alert_untested"]) and both["alert_contradicted"] != both["alert_untested"],
        "an alert a measurement contradicted is kept apart from an alert nobody checked",
    )

    assays = [
        row for compound in data["compounds"] for row in findings_at(compound, "assay-outcome")
    ]
    missing = [row for row in assays if row["concentration_micromolar"] is None]
    record_result(
        len(missing) > 0,
        f"{len(missing)} of {len(assays)} assay outcomes carry no concentration, so they"
        " cannot be compared with the ones that do",
    )
    record_result(
        data["exposure"]["declared"] is False and bool(data["exposure"]["why_it_matters"]),
        "no exposure is declared anywhere, and the record says why that matters rather"
        " than leaving the gap silent",
    )
    top = [row for row in rows if row["has_organism_level"]]
    record_result(
        0 < len(top) < len(rows) / 2,
        f"organism-level evidence exists for {len(top)} of {len(rows)} compounds, which is"
        " the ordinary shape of a safety record",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    data = load()

    print(f"Record {DATASET.relative_to(ROOT)}")
    print(f"{len(data['compounds'])} constructed compounds, alerts computed rather than stored")
    print()
    if action == "show":
        show(data)
        show_dose(data)
        show_limits()
        print("Run 'check' to recompute these counts from the committed record.")
        return

    print("SAFETY EVIDENCE CHECKS")
    failures = check(data)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies that the five levels stay separated,")
    print("not that any compound is safe and not that any outcome is real.")


if __name__ == "__main__":
    main()
