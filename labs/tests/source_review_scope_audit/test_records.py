"""The loader reads canonical records and refuses absent identifiers."""

from pathlib import Path

import pytest
from aidd_commons.source_review_scope_audit.analysis import entry_parts
from aidd_commons.source_review_scope_audit.protocol import EXAMINED_IDS, load_protocol
from aidd_commons.source_review_scope_audit.records import (
    RecordError,
    load_catalogue,
    load_reading,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/source_review_scope_audit/protocol.json"


def test_loader_keeps_entries_and_distinguishes_four_parts() -> None:
    catalogue = load_catalogue(ROOT / "catalog/resources")
    record = catalogue["model-boltz-2"]
    assert record["id"] == "model-boltz-2"
    assert [entry["id"] for entry in record["evidence"]] == [
        "resource-links-2026-09-08",
        "repository",
        "readme",
        "license",
        "model-boltz-2-readme",
    ]
    parts = entry_parts(record["evidence"][2])
    assert parts == {
        "surface": "carried",
        "version": "absent",
        "date": "named-in-text",
        "scope": "named-in-text",
    }
    assert record["last_verified"] == "2026-10-23"


def test_missing_declared_record_is_refused() -> None:
    with pytest.raises(RecordError, match="missing catalogue records"):
        load_catalogue(ROOT / "catalog/resources", (*EXAMINED_IDS, "model-no-such-record"))


def test_reading_reports_the_depths_as_the_records_state_them() -> None:
    """The record caught up with the reading once the laboratory existed."""
    reading = load_reading(ROOT, load_protocol(PROTOCOL))
    assert reading["recorded_depth"] == "assessed"
    assert reading["independent_depth"] == "assessed"
