"""Constructed overlap cases with an independently readable answer."""

from __future__ import annotations

import pytest
from aidd_commons.split_leakage_audit.analysis import AuditError, AuditRow, audit_rows
from aidd_commons.split_leakage_audit.protocol import UNTESTABLE


def row(number: int, parent: str, scaffold: str, assay: str, target: str, form: str) -> AuditRow:
    return AuditRow(
        (parent, f"assay-{number}", "doc", "IC50"),
        {
            "parent": frozenset((parent,)),
            "scaffold": frozenset((scaffold,)),
            "assay": frozenset((assay,)),
            "target": frozenset((target,)),
            "standard_form": frozenset((form,)),
        },
    )


def test_known_overlap_and_aggregate() -> None:
    rows = [
        row(0, "A", "X", "a", "t1", "fA"),
        row(1, "A", "X", "b", "t2", "fA"),
        row(2, "B", "X", "c", "t1", "fB"),
        row(3, "C", "Y", "d", "t3", "fC"),
    ]
    result = audit_rows(rows, seed=1, train_fraction=0.5)
    assert result["row_split"] == {"seed": 1, "train_rows": 2, "test_rows": 2}
    assert result["routes"] == {
        "parent": {
            "test_rows_with_train_group": 1,
            "shared_groups": 1,
            "train_rows_to_hold_out": 1,
        },
        "scaffold": {
            "test_rows_with_train_group": 2,
            "shared_groups": 1,
            "train_rows_to_hold_out": 1,
        },
        "assay": {
            "test_rows_with_train_group": 0,
            "shared_groups": 0,
            "train_rows_to_hold_out": 0,
        },
        "target": {
            "test_rows_with_train_group": 1,
            "shared_groups": 1,
            "train_rows_to_hold_out": 1,
        },
        "standard_form": {
            "test_rows_with_train_group": 1,
            "shared_groups": 1,
            "train_rows_to_hold_out": 1,
        },
    }
    assert result["aggregate"] == {"contaminated_test_rows": 2, "contributing_routes": 4}
    assert result["highest_overlap_route"] == "scaffold"
    grouped = result["grouped_parent_split"]
    assert grouped["unseen_parent_test_rows"] == grouped["test_rows"]
    assert result["untestable_routes"] == UNTESTABLE


def test_multiple_forms_of_one_measurement_are_all_retained() -> None:
    first = row(0, "A", "X", "a", "t1", "fA")
    second = row(1, "B", "Y", "b", "t2", "fB")
    second = AuditRow(second.key, {**second.groups, "standard_form": frozenset(("fA", "fB"))})
    result = audit_rows((first, second), seed=1, train_fraction=0.5)
    assert result["routes"]["standard_form"]["test_rows_with_train_group"] == 1


@pytest.mark.parametrize("defect", ["duplicate", "missing-route", "wrong-parent"])
def test_invalid_measurement_is_refused(defect: str) -> None:
    good = row(0, "A", "X", "a", "t1", "fA")
    other = row(1, "B", "Y", "b", "t2", "fB")
    if defect == "duplicate":
        rows = (good, good)
    elif defect == "missing-route":
        rows = (good, AuditRow(other.key, {"parent": frozenset(("B",))}))
    else:
        rows = (good, AuditRow(other.key, {**other.groups, "parent": frozenset(("A",))}))
    with pytest.raises(AuditError):
        audit_rows(rows, seed=1, train_fraction=0.5)
