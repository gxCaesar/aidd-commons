"""The loader retains claim depth, evidence and note as separate source fields."""

from pathlib import Path

import pytest
from aidd_commons.claims_evidence_audit.records import RecordError, load_provider

ROOT = Path(__file__).resolve().parents[3]
SYSTEMS = ROOT / "catalog/comparisons/systems"


def test_load_provider_keeps_distinct_fields() -> None:
    record = load_provider(SYSTEMS, "aidd-commons")
    cell = next(
        row for row in record["coverage"] if row["topic_id"] == "t01-evidence-claim-unknown"
    )
    # The loader keeps the fields apart. The recorded depth and the evidence
    # list are not pinned to a value, because a raise on a new reading changes
    # the first and the second, and the test is about the separation.
    assert cell["depth"] in {"worked", "executable", "assessed"}
    assert cell["evidence"]
    assert isinstance(cell["note"], str) and cell["note"]
    assert record["coverage_default"]["depth"] == "unverified"


def test_missing_provider_is_refused() -> None:
    with pytest.raises(RecordError, match="cannot read"):
        load_provider(SYSTEMS, "not-a-provider")


def test_path_like_provider_id_is_refused() -> None:
    with pytest.raises(RecordError, match="invalid provider id"):
        load_provider(SYSTEMS, "../aidd-commons")
