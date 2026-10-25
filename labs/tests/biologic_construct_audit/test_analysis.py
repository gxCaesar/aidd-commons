"""Constructed source passages exercise the four independent field rules."""

import copy
from pathlib import Path

import pytest
from aidd_commons.biologic_construct_audit import analysis
from aidd_commons.biologic_construct_audit.analysis import (
    AuditError,
    classify_record,
    load_snapshot,
)
from aidd_commons.biologic_construct_audit.protocol import EXPECTED_PROTOCOL

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/biologic_construct_audit"


def source_record(text, *, source="uniprot"):
    if source == "uniprot":
        return {
            "source": source,
            "key": "P00001",
            "entry_type": "UniProtKB reviewed (Swiss-Prot)",
            "protein_name": "Example protein",
            "pharmaceutical_text": [text],
        }
    return {
        "source": source,
        "key": "example-setid",
        "description": [text],
        "mechanism": [],
    }


def spec(*, construct=None, host=None, function=None, modality=("protein", ())):
    return {
        "key": "P00001",
        "anchor": "Example medicine",
        "fields": {
            "modality": modality,
            "construct": construct,
            "expression_system": host,
            "intended_function": function,
        },
        "assembly": "unstated",
        "parts_distinguished": False,
    }


def test_modality_alone_is_neither_construct_nor_definition():
    row = classify_record(source_record("Example medicine is listed."), "example", spec())
    assert row["field_stated"] == {
        "modality": True,
        "construct": False,
        "expression_system": False,
        "intended_function": False,
    }
    assert row["defined_construct"] is False


def test_construct_without_production_host_is_not_defined():
    rule = spec(construct=("two-domain protein", ("domain A joined to domain B",)))
    row = classify_record(
        source_record("Example medicine has domain A joined to domain B."), "example", rule
    )
    assert row["field_stated"]["construct"] is True
    assert row["field_stated"]["expression_system"] is False
    assert row["defined_construct"] is False


def test_host_without_construct_is_not_defined():
    rule = spec(host=("CHO", ("produced in CHO cells",)))
    row = classify_record(
        source_record("Example medicine is produced in CHO cells."), "example", rule
    )
    assert row["field_stated"]["expression_system"] is True
    assert row["field_stated"]["construct"] is False
    assert row["defined_construct"] is False


def test_all_four_require_separate_product_statements():
    rule = spec(
        modality=("protein", ("fusion protein",)),
        construct=("two-domain protein", ("domain A joined to domain B",)),
        host=("CHO", ("produced in CHO cells",)),
        function=("blocks receptor", ("blocks receptor binding",)),
    )
    rule["key"] = "example-setid"
    rule["parts_distinguished"] = True
    row = classify_record(
        source_record(
            "Example medicine is a fusion protein with domain A joined to domain B, "
            "produced in CHO cells, and blocks receptor binding.",
            source="dailymed",
        ),
        "example",
        rule,
    )
    assert all(row["field_stated"].values())
    assert row["parts_distinguished"] is True
    assert row["defined_construct"] is True


def test_unobserved_product_quote_is_refused():
    rule = spec(construct=("two-domain protein", ("domain A joined to domain B",)))
    with pytest.raises(AuditError, match="construct evidence missing"):
        classify_record(source_record("Example medicine is listed."), "example", rule)


def test_overlap_reports_conflict_only_when_stated_values_disagree(monkeypatch):
    snapshot = load_snapshot(LAB, EXPECTED_PROTOCOL)
    baseline = analysis.audit_records(snapshot, EXPECTED_PROTOCOL)
    assert baseline["source_disagreements"] == []
    assert {item["field"] for item in baseline["source_coverage_differences"]} == {
        "construct",
        "expression_system",
        "intended_function",
    }
    changed = copy.deepcopy(analysis.SOURCE_SPECS)
    spec = changed[("etanercept", "dailymed")]
    _, quotes = spec["fields"]["intended_function"]
    spec["fields"]["intended_function"] = ("different-action", quotes)
    monkeypatch.setattr(analysis, "SOURCE_SPECS", changed)
    result = analysis.audit_records(snapshot, EXPECTED_PROTOCOL)
    assert result["source_disagreements"] == [
        {
            "entity": "etanercept",
            "field": "intended_function",
            "left_source": "dailymed",
            "left_value": "different-action",
            "right_source": "uniprot",
            "right_value": "tnf-receptor-interaction-blockade",
        }
    ]
