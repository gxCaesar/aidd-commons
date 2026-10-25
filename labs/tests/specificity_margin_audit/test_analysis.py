"""The partner unit and incomplete-measurement rules."""

import json

from aidd_commons.skempi_affinity.protocol import HEADER
from aidd_commons.specificity_margin_audit.analysis import (
    MeasurementRow,
    audit_rows,
    rows_from_payload,
)


def test_partner_counts_and_distribution():
    rows = (
        MeasurementRow(0, "A", "B", True),
        MeasurementRow(1, "A", "B", True),
        MeasurementRow(2, "A", "C", True),
        MeasurementRow(3, "B", "C", True),
        MeasurementRow(4, "B", "D", True),
        MeasurementRow(5, "C", "D", False),
        MeasurementRow(6, "", "", True),
    )
    result = audit_rows(rows)
    assert result["archive_counts"] == {
        "rows": 7,
        "protein_pairs": 4,
        "proteins": 4,
        "rows_with_parsed_measurement": 6,
        "counted_pair_rows": 5,
        "parsed_rows_without_pair_labels": 1,
    }
    assert result["partner_distribution"] == {
        "proteins_by_distinct_partner_count": {"1": 1, "2": 2, "3": 1},
        "median": 2,
        "iqr": {"q1": 1.75, "q3": 2.25},
        "exactly_one_partner": 1,
    }
    assert result["comparable_pair_count"] == 3
    assert result["per_protein"] == [
        {
            "protein": "A",
            "measurement_count": 3,
            "distinct_partners": 2,
            "beyond_one_partner": True,
        },
        {
            "protein": "B",
            "measurement_count": 4,
            "distinct_partners": 3,
            "beyond_one_partner": True,
        },
        {
            "protein": "C",
            "measurement_count": 2,
            "distinct_partners": 2,
            "beyond_one_partner": True,
        },
        {
            "protein": "D",
            "measurement_count": 1,
            "distinct_partners": 1,
            "beyond_one_partner": False,
        },
    ]


def test_reader_alignment_and_missing_parsed_value():
    fields = ["complex-1", "m", "m", "x", "AB/AG", "group", "", "1e-8", "", "", "ref", "A", "B"]
    envelope = {
        "dataset_id": "skempi2",
        "row_index": 0,
        "source_file": "labeled/skempi2/skempi_v2.csv",
        "row": {HEADER: ";".join(fields)},
    }
    missing = dict(envelope, row_index=1, row={HEADER: ";".join(fields[:6])})
    payload = (json.dumps(envelope) + "\n" + json.dumps(missing) + "\n").encode()
    rows = rows_from_payload(payload)
    assert rows == (
        MeasurementRow(0, "A", "B", True),
        MeasurementRow(1, "", "", False),
    )
    assert audit_rows(rows)["archive_counts"]["counted_pair_rows"] == 1
