"""Assign a claim to each record using only declared fields and count the result."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from aidd_commons.assay_endpoint_controls.data import AssayDataset, MeasurementRow
from aidd_commons.decision_unit_scope.data import ActivityRow
from aidd_commons.decision_unit_scope.protocol import BOUND_RELATIONS, ENDPOINT_TYPES

from .protocol import (
    ENDPOINT_LABELS,
    KIND_BOUND,
    KIND_NONE,
    KIND_POINT,
    KIND_RESPONSE,
    KINDS,
    UNMEASURABLE_ROUTES,
)
from .records import Tables

TABLE_CHEMBL = "chembl37"
TABLE_PUBCHEM = "pubchem_bioassay"
TABLES = (TABLE_CHEMBL, TABLE_PUBCHEM)
CLAIMS = (
    "endpoint_point",
    "endpoint_bound",
    "binding_point",
    "binding_bound",
    "functional_response",
    "clinical_outcome",
)


class AuditError(ValueError):
    """A record contradicts the declared field rule."""


@dataclass(frozen=True)
class AuditRecord:
    identifier: str
    table: str
    kind: str
    licensed_claims: tuple[str, ...]


def chembl_record(row: ActivityRow) -> AuditRecord:
    """A source-admitted activity row remains a point or a bound."""
    classification = row.classification
    if classification not in ("point", "bound"):
        raise AuditError("the activity row was not admitted by the source reader")
    kind = KIND_POINT if classification == "point" else KIND_BOUND
    claims = ["endpoint_point" if kind == KIND_POINT else "endpoint_bound"]
    if row.assay_type == "B" and row.standard_type in ("Kd", "Ki"):
        claims.append("binding_point" if kind == KIND_POINT else "binding_bound")
    return AuditRecord(f"chembl:{row.activity_id}", TABLE_CHEMBL, kind, tuple(claims))


def pubchem_record(dataset: AssayDataset, row: MeasurementRow) -> AuditRecord:
    """A row's series, response definition, endpoint and qualifier determine its claims."""
    if not row.endpoints or not set(row.endpoints) <= set(dataset.spec.endpoint_labels):
        raise AuditError("assay row has no declared endpoint value")
    if row.qualifier not in ("", "=", *BOUND_RELATIONS):
        raise AuditError("assay row carries an unknown endpoint relation")
    has_series = (
        row.numeric_point_count >= 5
        and dataset.spec.direction in ("activation", "inhibition")
        and bool(dataset.protocol_text.strip())
    )
    if has_series:
        kind = KIND_RESPONSE
    elif row.qualifier == "=":
        kind = KIND_POINT
    elif row.qualifier in BOUND_RELATIONS:
        kind = KIND_BOUND
    else:
        kind = KIND_NONE
    claims: list[str] = []
    if row.qualifier == "=":
        claims.append("endpoint_point")
    elif row.qualifier in BOUND_RELATIONS:
        claims.append("endpoint_bound")
    if has_series:
        claims.append("functional_response")
    return AuditRecord(
        f"pubchem:{dataset.spec.aid}:{row.compound_id}", TABLE_PUBCHEM, kind, tuple(claims)
    )


def audit_records(records: Sequence[AuditRecord]) -> dict[str, object]:
    """Check every record's licence and aggregate without exporting record content."""
    seen: set[str] = set()
    per_table: dict[str, Counter[str]] = {table: Counter() for table in TABLES}
    claim_counts: Counter[str] = Counter()
    for record in records:
        if record.identifier in seen:
            raise AuditError("record identifiers must be unique")
        seen.add(record.identifier)
        if record.table not in TABLES or record.kind not in KINDS:
            raise AuditError("unknown table or record kind")
        claims = set(record.licensed_claims)
        if len(claims) != len(record.licensed_claims) or not claims <= set(CLAIMS):
            raise AuditError("duplicate or unknown claim kind")
        if "clinical_outcome" in claims:
            raise AuditError("neither table can license a clinical outcome")
        if record.kind == KIND_NONE and claims:
            raise AuditError("a no-claim record licenses a claim")
        if record.kind != KIND_NONE and not claims:
            raise AuditError("a claim-bearing record has no claim")
        if record.kind == KIND_POINT and (
            "endpoint_point" not in claims or "endpoint_bound" in claims
        ):
            raise AuditError("point kind has an inconsistent endpoint claim")
        if record.kind == KIND_BOUND and (
            "endpoint_bound" not in claims or "endpoint_point" in claims
        ):
            raise AuditError("bound kind has an inconsistent endpoint claim")
        if record.kind == KIND_RESPONSE and "functional_response" not in claims:
            raise AuditError("a response table lacks its response claim")
        if record.kind != KIND_RESPONSE and "functional_response" in claims:
            raise AuditError("a non-response row licenses a response")
        if record.kind == KIND_RESPONSE and record.table != TABLE_PUBCHEM:
            raise AuditError("the ChEMBL activity snapshot has no response tables")
        if record.table != TABLE_CHEMBL and {"binding_point", "binding_bound"} & claims:
            raise AuditError("the assay response rows are not direct binding records")
        if "binding_point" in claims and "endpoint_point" not in claims:
            raise AuditError("binding point without a point endpoint")
        if "binding_bound" in claims and "endpoint_bound" not in claims:
            raise AuditError("binding bound without a bounded endpoint")
        per_table[record.table][record.kind] += 1
        claim_counts.update(claims)
    return {
        "tables": {
            table: {
                "total_records": sum(per_table[table].values()),
                "kind_counts": {kind: per_table[table][kind] for kind in KINDS},
            }
            for table in TABLES
        },
        "licensed_claim_counts": {claim: claim_counts[claim] for claim in CLAIMS},
        "records_licensing_no_claim": sum(per_table[table][KIND_NONE] for table in TABLES),
        "unmeasurable_routes": dict(UNMEASURABLE_ROUTES),
    }


def audit_tables(tables: Tables) -> dict[str, object]:
    """Count source-admitted records and keep the two source units separate."""
    records = [chembl_record(row) for row in tables.chembl_rows]
    standard_types: Counter[str] = Counter()
    bounds = 0
    for chembl_row in tables.chembl_rows:
        if chembl_row.standard_type not in ENDPOINT_TYPES:
            raise AuditError("admitted ChEMBL row has an unexpected standard type")
        standard_types[chembl_row.standard_type] += 1
        bounds += chembl_row.classification == "bound"

    assays: dict[str, dict[str, object]] = {}
    for aid, dataset in sorted(tables.pubchem_assays.items()):
        endpoint_counts: Counter[str] = Counter()
        qualifier_rows: Counter[str] = Counter()
        value_relations: Counter[str] = Counter()
        for assay_row in dataset.rows:
            records.append(pubchem_record(dataset, assay_row))
            endpoint_counts.update(assay_row.endpoints.keys())
            relation = assay_row.qualifier or "unstated"
            qualifier_rows[relation] += 1
            value_relations[relation] += len(assay_row.endpoints)
        assays[str(aid)] = {
            "total_records": len(dataset.rows),
            "endpoint_counts": {label: endpoint_counts[label] for label in ENDPOINT_LABELS},
            "qualifier_row_counts": dict(sorted(qualifier_rows.items())),
            "stated_qualifier_values": sum(
                count for relation, count in value_relations.items() if relation != "unstated"
            ),
            "equality_values": value_relations["="],
            "bound_values": sum(value_relations[relation] for relation in BOUND_RELATIONS),
            "unstated_relation_values": value_relations["unstated"],
        }
    result = audit_records(records)
    return {
        **result,
        "chembl_standard_type_counts": {name: standard_types[name] for name in ENDPOINT_TYPES},
        "chembl_bound_measurements": bounds,
        "pubchem_assays": assays,
    }
