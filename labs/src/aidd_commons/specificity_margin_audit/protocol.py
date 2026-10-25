"""The frozen contract for the partner coverage census."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.skempi_affinity.protocol import EXPECTED_BYTES, SOURCE_URL

PROTOCOL_ID = "skempi2-specificity-margin-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.specificity-margin-audit-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.specificity-margin-audit-summary.v1"
ISSUED_ON = "2026-10-23"
SNAPSHOT_REVISION = "d17a8bb0ec82ed1a5f34e106106f9d1034d19d07"


class ProtocolError(ValueError):
    """The on-disk protocol differs from the frozen contract."""


def expected_fields() -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "run_basis": (
            "Fresh independent computation from the cached, reader-validated snapshot on CPU."
        ),
        "source": {
            "archive": "SKEMPI 2.0 CSV",
            "snapshot": f"LiteFold/SKEMPI2 JSONL, revision {SNAPSHOT_REVISION}",
            "expected_bytes": EXPECTED_BYTES,
            "retrieval_url": SOURCE_URL,
            "upstream_terms_url": "https://life.bsc.es/pid/skempi2/info/terms",
            "upstream_licence": "CC BY 4.0",
            "mirror_card_licence": "other",
            "reader": "aidd_commons.skempi_affinity.data.parse_payload",
        },
        "counted_unit": {
            "protein_pair": (
                "Unordered pair of the exact, nonempty Protein 1 and Protein 2 labels "
                "in the validated primary row value."
            ),
            "measurement_rule": (
                "A row counts toward its protein pair only when at least one parsed affinity "
                "is present. Rows without both protein labels remain in archive counts but "
                "not pair counts."
            ),
            "label_rule": (
                "Strip surrounding whitespace only; do not merge aliases or infer labels "
                "from overflow fragments."
            ),
        },
        "partner_rule": {
            "definition": (
                "Count distinct opposite protein labels across counted rows for each protein."
            ),
            "one_partner": (
                "A protein measured with exactly one partner has no alternative-partner "
                "margin in this table."
            ),
            "comparable_pair": (
                "Both proteins in the counted pair must each have more than one distinct "
                "measured partner."
            ),
        },
        "excluded_by_design": [
            "Any prediction of selectivity for a protein the table does not measure.",
            "Any claim that a protein with one measured partner is selective.",
            "Any ranking of proteins by measurement or partner counts.",
            "Any estimate of a selectivity margin from this census.",
        ],
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    expected = expected_fields()
    if not isinstance(document, dict):
        raise ProtocolError("protocol must be an object")
    for key, value in expected.items():
        if document.get(key) != value:
            raise ProtocolError(f"changed protocol field: {key}")
    if set(document) != set(expected):
        raise ProtocolError("unexpected protocol field")
    return document
