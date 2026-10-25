"""The audit checks real local return records without inventing tool status."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from aidd_commons.tool_contract_audit.analysis import audit_records, load_records
from aidd_commons.tool_contract_audit.contract import check_record
from aidd_commons.tool_contract_audit.protocol import expected_fields

ROOT = Path(__file__).resolve().parents[3]


def test_real_records_are_all_audited() -> None:
    protocol = expected_fields()
    records = load_records(
        ROOT / "labs",
        protocol["source"],
        exclude=protocol["source"]["exclude_laboratory"],
    )
    result = audit_records(records, protocol["contract"])
    assert result["return_record_count"] == len(records) == 32
    assert result["fields_in_every_record"] == [
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "software.python",
    ]
    assert result["protocol_file_count"] == result["readme_file_count"] == 32
    assert result["records_with_declared_limits"] + result["records_without_declared_limits"] == 32
    assert result["error_field_counts"]["records_carrying_status"] == 0
    assert len(result["per_laboratory"]) == 32


def test_missing_field_and_empty_value_have_distinct_real_record_failures() -> None:
    protocol = expected_fields()
    record = load_records(
        ROOT / "labs",
        protocol["source"],
        exclude=protocol["source"]["exclude_laboratory"],
    )[0].return_record
    contract = protocol["contract"]
    missing = deepcopy(record)
    missing.pop("protocol_id")
    empty = deepcopy(record)
    empty["protocol_id"] = ""
    missing_reason = next(
        failure.reason
        for failure in check_record(missing, contract).failures
        if failure.field == "protocol_id"
    )
    empty_reason = next(
        failure.reason
        for failure in check_record(empty, contract).failures
        if failure.field == "protocol_id"
    )
    assert missing_reason == "missing_required_field"
    assert empty_reason == "invalid_or_empty_value"
