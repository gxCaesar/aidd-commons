"""Read the frozen ChEMBL EGFR contract and check the committed artifacts agree.

This command needs no network, no download and no third-party package. It reads
only the JSON files committed beside it, so a reader can inspect the screening
unit, the endpoint definition and the admission rules before deciding whether to
run anything. It reports what each rule excludes, not only what it admits.

    python labs/chembl_egfr/inspect_contract.py show
    python labs/chembl_egfr/inspect_contract.py check

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


def show_screening_unit(protocol: dict, development: dict) -> None:
    """The unit a result is about: one assay, not one target and not one paper."""
    print("SCREENING UNIT")
    print("  A measurement belongs to an assay. Two assays on the same target are")
    print("  two units, so a model that transfers between them has to be shown to.")
    roles = {
        development["data"]["primary"]["assay_chembl_id"]: "primary",
        development["data"]["replication"]["assay_chembl_id"]: "replication",
    }
    for assay_id, assay in sorted(protocol["source"]["assays"].items()):
        print(f"  {assay_id} [{roles.get(assay_id, 'unassigned')}]")
        print(f"    assay type       {assay['assay_type']}   (B is a binding assay)")
        print(f"    BAO format       {assay['bao_format']}")
        print(f"    confidence score {assay['confidence_score']}")
        print(f"    document         {assay['document_chembl_id']}")
    print("  Excluded by this choice: every other EGFR assay in the release, and")
    print("  therefore any claim about EGFR activity in general.")
    print()


def show_endpoint(protocol: dict) -> None:
    """What the number means before any model is fitted."""
    labels = protocol["labels"]
    print("ENDPOINT DEFINITION")
    print(f"  measured quantity   {labels['endpoint']}")
    print(f"  admitted relation   {labels['standard_relation']}   (censored rows are dropped)")
    print(f"  admitted units      {labels['standard_units']}")
    print(f"  modelled target     {labels['target']}")
    print(f"  repeats per parent  {labels['parent_aggregation']}")
    print(f"  standard_flag       {labels['standard_flag']}")
    print(f"  potential_duplicate {labels['potential_duplicate']}")
    print(f"  pchembl tolerance   {labels['pchembl_consistency_tolerance']}")
    print("  Excluded by this choice: Ki and Kd rows, non-nanomolar rows, and every")
    print("  greater-than or less-than measurement, which is most of the weak end.")
    print("  A model trained here predicts a potency summary, not an activity call.")
    print()


def show_entity_and_admission(protocol: dict, development: dict) -> None:
    """Which object one row is about, and which rows never enter."""
    entity = protocol["entity"]
    print("ENTITY AND ADMISSION")
    print(f"  independent unit  {entity['unit']}")
    print(f"  child-parent rule {entity['child_parent_rule']}")
    print(f"  structure source  {entity['structure']}")
    for role in ("primary", "replication"):
        block = development["data"][role]
        excluded = block.get("exclusion_counts", {})
        total = sum(excluded.values())
        print(f"  {role} {block['assay_chembl_id']}")
        print(f"    rows read            {block['input_rows']}")
        for reason, count in sorted(excluded.items()):
            print(f"    excluded {reason:<18} {count}")
        print(
            f"    rows retained        {block['retained_rows']}  ({block['input_rows']} - {total})"
        )
        print(f"    parent molecules     {block['parent_count']}")
        print(f"    parents with repeats {block['duplicate_parent_count']}")
    print(f"  parents shared between the two assays: {development['data']['parent_overlap']}")
    print("  A salt and its parent are one unit here, so they can never land on")
    print("  opposite sides of a split.")
    print()


def check(protocol: dict, development: dict, locked: dict, amendment: dict) -> list[str]:
    """Recompute what must hold across the three artifacts. Returns failures."""
    failures: list[str] = []

    def record(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    version = protocol["protocol_version"]
    record(
        development["protocol_version"] == version
        and locked["protocol_id"] == version
        and amendment["base_protocol"] == version,
        f"all four artifacts declare protocol {version}",
    )

    for role in ("primary", "replication"):
        block = development["data"][role]
        excluded = sum(block.get("exclusion_counts", {}).values())
        record(
            block["input_rows"] - excluded == block["retained_rows"],
            f"{role} admission arithmetic closes: "
            f"{block['input_rows']} - {excluded} = {block['retained_rows']}",
        )

    grid = protocol["models"]["ridge_alphas"]
    selected = development["selection"]["selected_alphas"]
    record(
        all(alpha in grid for alpha in selected.values()),
        "every selected alpha is a member of the frozen grid",
    )

    for name, rows in sorted(development["selection"]["grid_scores"].items()):
        # The protocol rule is minimum validation MAE, ties choosing the smaller alpha.
        best = min(rows, key=lambda row: (row["metrics"]["mae"], row["alpha"]))
        record(
            best["alpha"] == selected[name],
            f"{name} selection replays to alpha {selected[name]} from the stored grid",
        )

    record(
        locked["selected_alphas"] == selected,
        "the locked run reused the development alphas without reselecting",
    )
    record(
        all(
            development["software"][key] == locked["software"][key]
            for key in ("python", "numpy", "rdkit")
        ),
        "development and locked runs report the same python, numpy and rdkit",
    )

    constant = development["selection"]["metrics"]["train_mean"]
    record(
        constant["spearman"] is None
        and constant["spearman_status"] == "undefined_constant_prediction",
        "the constant baseline reports an undefined rank correlation rather than zero",
    )

    print()
    print("  Note: the protocol still records locked_evaluation.state as")
    print(f"  '{protocol['locked_evaluation']['state']}' while the locked summary reads")
    print(f"  '{locked['status']}'. The protocol was not rewritten. Amendment")
    print(f"  {amendment['id']} records the change and states that it supersedes")
    print(f"  {amendment['supersedes']}.")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action

    protocol = load("protocol.json")
    development = load("development-summary.json")
    locked = load("locked-summary.json")
    amendment = load("execution-amendment.json")

    print(f"Frozen contract {protocol['protocol_version']}")
    print(f"development reviewed {development['reviewed_on']}")
    print(f"locked reviewed {locked['reviewed_on']}")
    print()
    if action == "show":
        show_screening_unit(protocol, development)
        show_endpoint(protocol)
        show_entity_and_admission(protocol, development)
        print("Run 'check' to recompute the relationships between these artifacts.")
        return

    print("CONTRACT CHECKS")
    failures = check(protocol, development, locked, amendment)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies internal agreement, not scientific validity.")


if __name__ == "__main__":
    main()
