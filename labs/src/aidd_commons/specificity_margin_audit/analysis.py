"""Count observed partner coverage without estimating a margin."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from aidd_commons.skempi_affinity.data import parse_payload
from aidd_commons.skempi_affinity.protocol import HEADER


class AuditError(ValueError):
    """A row or census violates the declared counting rule."""


@dataclass(frozen=True)
class MeasurementRow:
    row_index: int
    protein_1: str
    protein_2: str
    has_parsed_measurement: bool


def rows_from_payload(payload: bytes) -> tuple[MeasurementRow, ...]:
    """Use the established reader, then extract two fields it does not expose.

    The reader validates the envelope, order, positional width and affinity
    values. No overflow fragment is reconstructed into a protein label.
    """
    dataset = parse_payload(payload)
    header = HEADER.split(";")
    first = header.index("Protein 1")
    second = header.index("Protein 2")
    rows: list[MeasurementRow] = []
    for record, line in zip(dataset.records, payload.decode("utf-8").splitlines(), strict=True):
        fields = json.loads(line)["row"][HEADER].split(";")
        protein_1 = fields[first].strip() if len(fields) > first else ""
        protein_2 = fields[second].strip() if len(fields) > second else ""
        rows.append(
            MeasurementRow(
                row_index=record.row_index,
                protein_1=protein_1,
                protein_2=protein_2,
                has_parsed_measurement=(
                    record.mutant_m is not None or record.wild_type_m is not None
                ),
            )
        )
    return tuple(rows)


def audit_rows(rows: Sequence[MeasurementRow]) -> dict[str, Any]:
    if not rows or [row.row_index for row in rows] != list(range(len(rows))):
        raise AuditError("rows must have consecutive source indices")
    pair_measurements: Counter[tuple[str, str]] = Counter()
    protein_measurements: Counter[str] = Counter()
    partners: dict[str, set[str]] = defaultdict(set)
    parsed_rows = 0
    unnamed_parsed_rows = 0
    for row in rows:
        parsed_rows += row.has_parsed_measurement
        if not row.has_parsed_measurement:
            continue
        if not row.protein_1 or not row.protein_2:
            unnamed_parsed_rows += 1
            continue
        if row.protein_1 == row.protein_2:
            raise AuditError(f"row {row.row_index}: self-pair protein labels")
        first, second = sorted((row.protein_1, row.protein_2))
        pair = (first, second)
        pair_measurements[pair] += 1
        for protein, partner in ((pair[0], pair[1]), (pair[1], pair[0])):
            protein_measurements[protein] += 1
            partners[protein].add(partner)

    if not pair_measurements:
        raise AuditError("no measured pair has two protein labels")
    partner_counts = sorted(len(values) for values in partners.values())
    q1, _, q3 = statistics.quantiles(partner_counts, n=4, method="inclusive")
    distribution = Counter(partner_counts)
    per_protein = [
        {
            "protein": protein,
            "measurement_count": protein_measurements[protein],
            "distinct_partners": len(partners[protein]),
            "beyond_one_partner": len(partners[protein]) > 1,
        }
        for protein in sorted(partners)
    ]
    archive_counts = {
        "rows": len(rows),
        "protein_pairs": len(pair_measurements),
        "proteins": len(partners),
        "rows_with_parsed_measurement": parsed_rows,
        "counted_pair_rows": sum(pair_measurements.values()),
        "parsed_rows_without_pair_labels": unnamed_parsed_rows,
    }
    result = {
        "archive_counts": archive_counts,
        "partner_distribution": {
            "proteins_by_distinct_partner_count": {
                str(count): frequency for count, frequency in sorted(distribution.items())
            },
            "median": statistics.median(partner_counts),
            "iqr": {"q1": q1, "q3": q3},
            "exactly_one_partner": distribution[1],
        },
        "comparable_pair_count": sum(
            len(partners[first]) > 1 and len(partners[second]) > 1
            for first, second in pair_measurements
        ),
        "per_protein": per_protein,
    }
    if sum(protein_measurements.values()) != 2 * archive_counts["counted_pair_rows"]:
        raise AuditError("per-protein measurement count does not reconcile")
    if sum(distribution.values()) != archive_counts["proteins"]:
        raise AuditError("partner distribution does not reconcile")
    if parsed_rows != archive_counts["counted_pair_rows"] + unnamed_parsed_rows:
        raise AuditError("parsed row count does not reconcile")
    return result
