"""Literal alignment tests, including a partial primary value."""

import json

import pytest
from aidd_commons.skempi_affinity.data import DataContractError, parse_payload, validate_size
from aidd_commons.skempi_affinity.protocol import HEADER


def envelope(index, fields, extra=None):
    return {
        "dataset_id": "skempi2",
        "row_index": index,
        "source_file": "labeled/skempi2/skempi_v2.csv",
        "row": {HEADER: ";".join(fields), **(extra or {})},
    }


def test_ragged_primary_value_pads_without_reassigning_overflow():
    complete = ["complex-1", "m", "m", "x", "AB/AG", "group", "", "1e-8", "", "2e-8"]
    partial = ["complex-2", "m", "m", "x", "AB/AG", "group"]
    payload = (json.dumps(envelope(0, complete)) + "\n" + json.dumps(
        envelope(1, partial, {"column_1": ";1e-8;;2e-8"})
    ) + "\n").encode()
    dataset = parse_payload(payload)
    assert dataset.field_counts == {6: 1, 10: 1}
    assert dataset.fragmented_rows == 1
    assert dataset.records[0].complete
    assert dataset.records[0].mutant_m == 1e-8
    assert not dataset.records[1].complete


@pytest.mark.parametrize("mutation", ["header", "wide", "index", "extra_key"])
def test_malformed_records_rejected(mutation):
    record = envelope(0, ["complex-1", "m"])
    if mutation == "header":
        record["row"] = {"wrong;header": "complex-1;m"}
    elif mutation == "wide":
        record["row"] = {HEADER: ";".join(["x"] * 30)}
    elif mutation == "index":
        record["row_index"] = 5
    else:
        record["row"]["unexpected"] = "x"
    with pytest.raises(DataContractError):
        parse_payload((json.dumps(record) + "\n").encode())


def test_byte_length_guard_rejects_partial_download():
    with pytest.raises(DataContractError, match="bytes"):
        validate_size(b"partial")
