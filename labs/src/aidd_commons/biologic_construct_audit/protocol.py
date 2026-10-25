"""Frozen source and extraction contract for therapeutic construct records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

PROTOCOL_ID = "therapeutic-construct-records-v2"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.biologic-construct-audit-protocol.v2"
SNAPSHOT_SCHEMA_VERSION = "aidd-commons.biologic-construct-audit-snapshot.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.biologic-construct-audit-summary.v2"
ISSUED_ON = "2026-10-23"
FIELD_NAMES = ("modality", "construct", "expression_system", "intended_function")
UNIPROT_ACCESSIONS = ("P00750", "P01308", "P06280", "P20333")
UNIPROT_QUERY = (
    "reviewed:true AND cc_pharmaceutical:* AND "
    "(accession:P20333 OR accession:P01308 OR accession:P00750 OR accession:P06280)"
)
UNIPROT_FIELDS = "accession,id,protein_name,organism_name,cc_pharmaceutical"
SNAPSHOT_PATH = "labs/src/aidd_commons/biologic_construct_audit/__init__.py"

EXPECTED_PROTOCOL: dict[str, Any] = {
    "schema_version": PROTOCOL_SCHEMA_VERSION,
    "protocol_id": PROTOCOL_ID,
    "issued_on": ISSUED_ON,
    "run_basis": (
        "Fresh independent CPU computation over a frozen product and extraction protocol. "
        "Download records a scoped source snapshot; show, check and export read that snapshot."
    ),
    "sources": {
        "uniprot": {
            "search_endpoint": "https://rest.uniprot.org/uniprotkb/search",
            "endpoint_pattern": "https://rest.uniprot.org/uniprotkb/search?query=<query>&size=<n>&fields=<fields>",
            "entry_pattern": "https://rest.uniprot.org/uniprotkb/<accession>.json",
            "query": UNIPROT_QUERY,
            "size": 4,
            "fields": UNIPROT_FIELDS,
            "accessions": list(UNIPROT_ACCESSIONS),
            "retained_sections": [
                "primaryAccession",
                "entryType",
                "entryAudit.entryVersion",
                "entryAudit.lastAnnotationUpdateDate",
                "proteinDescription.recommendedName.fullName.value",
                "comments[commentType=PHARMACEUTICAL].texts[*].value",
            ],
            "terms_url": "https://rest.uniprot.org/help/license",
        },
        "dailymed": {
            "endpoint_pattern": "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/<setid>.xml",
            "namespace": "urn:hl7-org:v3",
            "section_codes": {"description": "34089-3", "mechanism": "43679-0"},
            "labels": [
                {
                    "product": "etanercept",
                    "setid": "a002b40c-097d-47a5-957f-7a7b1807af7f",
                    "description_paragraphs": 1,
                    "mechanism_paragraphs": 3,
                },
                {
                    "product": "adalimumab",
                    "setid": "a06a9aec-fd5b-4c3e-a81f-eb46bb384100",
                    "description_paragraphs": 1,
                    "mechanism_paragraphs": 1,
                },
                {
                    "product": "agalsidase-beta",
                    "setid": "988513ab-b06f-4dd0-93f7-d2d4531dcce4",
                    "description_paragraphs": 2,
                    "mechanism_paragraphs": 1,
                },
            ],
            "terms_scope": (
                "Retain only the declared label paragraphs. DailyMed labels are company "
                "submissions; this protocol assigns no reuse licence to them."
            ),
        },
        "snapshot": {
            "path": SNAPSHOT_PATH,
            "format": "SNAPSHOT_JSON string literal in the listed package file",
            "route": (
                "download fetches the search, individual UniProt entries and selected SPLs, "
                "then overwrites this committed scoped snapshot. Offline runs read it."
            ),
            "fetch_record": (
                "UTC retrieval time, exact URL, response byte length and source version"
            ),
        },
    },
    "entities": [
        {"id": "etanercept", "product": "Enbrel", "uniprot_accession": "P20333"},
        {"id": "insulin-lispro", "product": "Humalog", "uniprot_accession": "P01308"},
        {"id": "human-insulin-humulin", "product": "Humulin", "uniprot_accession": "P01308"},
        {"id": "reteplase", "product": "Retavase", "uniprot_accession": "P00750"},
        {"id": "agalsidase-beta", "product": "Fabrazyme", "uniprot_accession": "P06280"},
        {"id": "adalimumab", "product": "Humira", "uniprot_accession": None},
    ],
    "counted_unit": "One named therapeutic entity, not one accession or source record.",
    "aggregation_rule": (
        "An entity states a field when at least one selected source record states it. "
        "Construct definition requires construct and host in the same source record. "
        "Construct/host gaps are reported by entity and source."
    ),
    "four_fields": {
        "modality": {
            "rule": (
                "Count the product's explicit biological class in its own label. A reviewed "
                "UniProt protein entry with a named pharmaceutical product and protein name "
                "states the broad protein modality. A drug target cross-reference does not."
            )
        },
        "construct": {
            "rule": (
                "Count product-specific components, assembly or sequence alteration in the "
                "selected record passage. A product name, indication or unspecified "
                "glycosylation difference is insufficient. Record whether a multi-chain "
                "assembly and its parts are distinguished."
            )
        },
        "expression_system": {
            "rule": (
                "Count only a named production host explicitly linked to the product. "
                "The UniProt organism is the native source organism, not a production host."
            )
        },
        "intended_function": {
            "rule": (
                "Count an explicit product action in the pharmaceutical annotation or "
                "mechanism section. Disease indication and the endogenous protein's "
                "FUNCTION comment do not fill this field."
            )
        },
    },
    "definition_rule": (
        "A source record defines a construct only when that same record states its "
        "modality, product-specific construct and production host. A modality alone "
        "is not a construct. An entity with neither construct nor host is not defined. "
        "Function remains a separate fourth field."
    ),
    "comparison_rule": (
        "Compare normalized values only where two source records state the same field. "
        "One source's silence is a coverage difference, not a disagreement."
    ),
    "excluded_by_design": [
        "A defined construct is not thereby developable or a therapeutic candidate.",
        "The number of stated fields does not rank the therapeutic entities.",
        "An unstated field in a selected record is not absent from the underlying science.",
        "Native protein annotations and target cross-references do not describe a drug construct.",
    ],
}


class ProtocolError(ValueError):
    """The on-disk protocol differs from the frozen contract."""


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if document != EXPECTED_PROTOCOL:
        raise ProtocolError("protocol differs from the frozen contract")
    return cast(dict[str, Any], document)
