"""Constructed records exercise every declared contract part."""

from __future__ import annotations

from copy import deepcopy

import pytest
from aidd_commons.tool_contract_audit.contract import check_record
from aidd_commons.tool_contract_audit.protocol import expected_fields


def complete_record() -> tuple[dict, dict]:
    contract = expected_fields()["contract"]
    record = {
        "schema_version": "aidd-commons.example-summary.v1",
        "protocol_id": "example-v1",
        "computed_on": "2026-10-23",
        "software": {"python": "3.11.15"},
        "environment": {
            "requires": ["Python 3.11"],
            "unavailable": ["external execution attestation"],
            "can_attest_external_execution": False,
        },
        "side_effects": {"allowed_writes": []},
        "outcome_status": "complete",
        "scientific_meaning": {
            "licenses": "A self-describing artefact was produced.",
            "does_not_license": "Its measurement is not independently verified.",
        },
        "limits": "The return record cannot establish measurement truth.",
        "result_count": 2,
    }
    return record, contract


def test_complete_record_passes_without_proving_measurement() -> None:
    record, contract = complete_record()
    verdict = check_record(record, contract)
    assert (verdict.name, verdict.failures, verdict.usable_result, verdict.must_stop) == (
        "pass",
        (),
        True,
        False,
    )


@pytest.mark.parametrize(
    ("field", "value", "expected_field"),
    [
        ("schema_version", "", "schema_version"),
        ("protocol_id", "", "protocol_id"),
        ("computed_on", "2026-02-30", "computed_on"),
        ("software", {"python": ""}, "software"),
        (
            "environment",
            {"requires": [], "unavailable": [], "can_attest_external_execution": True},
            "environment.requires",
        ),
        ("side_effects", {"allowed_writes": ["../escape"]}, "side_effects.allowed_writes"),
        ("outcome_status", "success", "outcome_status"),
        (
            "scientific_meaning",
            {"licenses": "", "does_not_license": ""},
            "scientific_meaning.licenses",
        ),
        ("limits", "", "limits"),
    ],
)
def test_each_part_rejects_an_invalid_value(field: str, value: object, expected_field: str) -> None:
    record, contract = complete_record()
    changed = deepcopy(record)
    changed[field] = value
    verdict = check_record(changed, contract)
    assert verdict.name == "invalid"
    assert expected_field in [failure.field for failure in verdict.failures]


@pytest.mark.parametrize(
    ("status", "expected", "must_stop"), [("no_result", "no_result", False), ("halt", "halt", True)]
)
def test_error_states_do_not_license_usable_results(
    status: str, expected: str, must_stop: bool
) -> None:
    record, contract = complete_record()
    record["outcome_status"] = status
    verdict = check_record(record, contract)
    assert (verdict.name, verdict.usable_result, verdict.must_stop) == (expected, False, must_stop)
