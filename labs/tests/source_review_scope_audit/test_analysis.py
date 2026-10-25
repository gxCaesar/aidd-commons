"""The field rule separates carried fields from words in a label."""

from pathlib import Path

from aidd_commons.source_review_scope_audit.analysis import (
    analyze,
    audit_record,
    check_invariants,
    entry_parts,
)
from aidd_commons.source_review_scope_audit.protocol import EXAMINED_IDS
from aidd_commons.source_review_scope_audit.records import load_catalogue

ROOT = Path(__file__).resolve().parents[3]


def constructed_record() -> dict[str, object]:
    return {
        "id": "example",
        "status": {"value": "unverified"},
        "access_level": {"value": "open_source", "evidence": ["complete"]},
        "openness": {
            name: {"value": "unverified"}
            for name in (
                "inference_code",
                "training_code",
                "weights",
                "architecture",
                "data_recipe",
                "training_data",
                "evaluation_code",
            )
        },
        "licenses": [],
        "evidence": [
            {
                "id": "complete",
                "url": "https://example.org/release",
                "label": "Release 2 read 2026-10-23",
                "version": "2",
                "reviewed_on": "2026-10-23",
                "reviewed_scope": "Release notes, section 3",
                "supports": ["access_level"],
            },
            {
                "id": "no-version",
                "url": "https://example.org/terms",
                "label": "Policy read 2026-10-23",
                "reviewed_on": "2026-10-23",
                "supports": [],
            },
            {"id": "name-only", "label": "Release 3 read 2026-10-23", "supports": []},
        ],
    }


def test_constructed_part_and_record_counts() -> None:
    row = audit_record(constructed_record())
    assert row["part_counts"]["surface"] == {
        "carried": 2,
        "named-in-text": 1,
        "absent": 0,
    }
    assert row["special_counts"] == {
        "all_four": 1,
        "date_surface_no_version": 1,
        "name_only": 1,
    }
    assert row["claim_counts"]["claims"] == 9
    assert row["claim_counts"]["claims_with_dated_reference"] == 1
    assert row["errors"] == []


def test_label_date_and_scope_are_not_carried() -> None:
    parts = entry_parts(
        {
            "url": "https://example.org/readme",
            "label": "README reviewed 2026-10-23, version 4",
        }
    )
    assert parts == {
        "surface": "carried",
        "version": "named-in-text",
        "date": "named-in-text",
        "scope": "named-in-text",
    }
    assert (
        entry_parts({"url": "https://example.org/", "label": "Example repository"})["scope"]
        == "absent"
    )
    assert (
        entry_parts({"url": "https://example.org/releases/v3.0", "label": "Example"})["version"]
        == "named-in-text"
    )


def test_real_totals_equal_per_record_counts() -> None:
    result = analyze(load_catalogue(ROOT / "catalog/resources"), EXAMINED_IDS)
    assert check_invariants(result, EXAMINED_IDS) == []
    assert result["totals"]["evidence_entries"] == sum(
        row["evidence_entries"] for row in result["records"]
    )
    assert result["totals"]["parts"]["date"]["carried"] == 0
    assert result["totals"]["parts"]["date"]["named-in-text"] > 0
