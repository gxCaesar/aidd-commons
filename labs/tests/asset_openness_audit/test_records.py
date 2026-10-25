"""The YAML loader keeps source claims and protocol membership intact."""

from pathlib import Path

import pytest
from aidd_commons.asset_openness_audit.protocol import DIMENSIONS, EXAMINED_IDS
from aidd_commons.asset_openness_audit.records import RecordError, load_catalogue, load_record

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = ROOT / "catalog/resources"


def test_read_record_keeps_seven_separate_claims() -> None:
    record = load_record(CATALOGUE / "model-boltz-2.yaml")
    assert record["id"] == "model-boltz-2"
    assert set(record["openness"]) == set(DIMENSIONS)
    assert record["openness"]["weights"]["value"] == "available"
    assert record["openness"]["training_data"]["value"] == "available"


def test_missing_declared_record_is_refused() -> None:
    with pytest.raises(RecordError, match="missing catalogue records"):
        load_catalogue(CATALOGUE, (*EXAMINED_IDS, "model-no-such-record"))


def test_duplicate_declared_record_is_refused() -> None:
    with pytest.raises(RecordError, match="repeats"):
        load_catalogue(CATALOGUE, (*EXAMINED_IDS, EXAMINED_IDS[0]))
