"""Read source-record excerpts and audit product-specific construct statements."""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, cast

from .protocol import FIELD_NAMES, PROTOCOL_ID, SNAPSHOT_SCHEMA_VERSION


class AuditError(ValueError):
    """A source record or computed classification violates the audit contract."""


# Each quote is required in the selected product's own source passage. Values are
# deliberately broad comparison terms. More detail in one record is not a conflict.
SOURCE_SPECS: dict[tuple[str, str], dict[str, Any]] = {
    ("etanercept", "uniprot"): {
        "key": "P20333",
        "anchor": "Enbrel",
        "fields": {
            "modality": ("protein", ()),
            "construct": (
                "tnfr2-ectodomain+igg-fc",
                (
                    "Enbrel consist of the extracellular ligand-binding portion of "
                    "TNFRSF1B linked to an immunoglobulin Fc chain",
                ),
            ),
            "expression_system": None,
            "intended_function": (
                "tnf-receptor-interaction-blockade",
                ("It binds to TNF and blocks its interactions with receptors",),
            ),
        },
        "assembly": "unstated",
        "parts_distinguished": False,
    },
    ("etanercept", "dailymed"): {
        "key": "a002b40c-097d-47a5-957f-7a7b1807af7f",
        "anchor": "Etanercept",
        "fields": {
            "modality": ("protein", ("dimeric fusion protein",)),
            "construct": (
                "tnfr2-ectodomain+igg-fc",
                (
                    "extracellular ligand-binding portion of the human 75 kilodalton "
                    "(p75) tumor necrosis factor receptor (TNFR) linked to the Fc "
                    "portion of human IgG1",
                ),
            ),
            "expression_system": (
                "CHO",
                ("Chinese hamster ovary (CHO) mammalian cell expression system",),
            ),
            "intended_function": (
                "tnf-receptor-interaction-blockade",
                (
                    "Etanercept inhibits binding of TNF-α and TNF-β "
                    "(lymphotoxin alpha [LT-α]) to cell surface TNFRs",
                ),
            ),
        },
        "assembly": "dimer",
        "parts_distinguished": True,
    },
    ("insulin-lispro", "uniprot"): {
        "key": "P01308",
        "anchor": "Humalog",
        "fields": {
            "modality": ("protein", ()),
            "construct": (
                "insulin-lispro-residue-swap",
                ("Humalog is an insulin analog with 52-Lys-Pro-53 instead of 52-Pro-Lys-53",),
            ),
            "expression_system": None,
            "intended_function": None,
        },
        "assembly": "unstated",
        "parts_distinguished": False,
    },
    ("human-insulin-humulin", "uniprot"): {
        "key": "P01308",
        "anchor": "Humulin",
        "fields": {
            "modality": ("protein", ()),
            "construct": None,
            "expression_system": None,
            "intended_function": None,
        },
        "assembly": "unstated",
        "parts_distinguished": False,
    },
    ("reteplase", "uniprot"): {
        "key": "P00750",
        "anchor": "Retavase",
        "fields": {
            "modality": ("protein", ()),
            "construct": (
                "tpa-kringle2+protease-fragment",
                ("Retavase is a fragment of TPA that contains kringle 2 and the protease domain",),
            ),
            "expression_system": None,
            "intended_function": ("fibrinolysis", ("to initiate fibrinolysis",)),
        },
        "assembly": "unstated",
        "parts_distinguished": False,
    },
    ("agalsidase-beta", "uniprot"): {
        "key": "P06280",
        "anchor": "Fabrazyme",
        "fields": {
            "modality": ("protein", ()),
            "construct": None,
            "expression_system": (
                "CHO",
                ("Agalsidase beta is produced in the hamster CHO cell line",),
            ),
            "intended_function": None,
        },
        "assembly": "unstated",
        "parts_distinguished": False,
    },
    ("agalsidase-beta", "dailymed"): {
        "key": "988513ab-b06f-4dd0-93f7-d2d4531dcce4",
        "anchor": "Agalsidase beta",
        "fields": {
            "modality": ("protein", ("recombinant human α-galactosidase A enzyme",)),
            "construct": (
                "alpha-galactosidase-a-homodimer",
                ("homodimeric glycoprotein", "two subunits of 398 amino acids"),
            ),
            "expression_system": (
                "CHO",
                ("Chinese hamster ovary mammalian cell expression system",),
            ),
            "intended_function": (
                "lysosomal-gl3-reduction",
                (
                    "Agalsidase beta is internalized and transported into lysosomes "
                    "where it exerts enzymatic activity and reduces accumulated GL-3",
                ),
            ),
        },
        "assembly": "homodimer",
        "parts_distinguished": True,
    },
    ("adalimumab", "dailymed"): {
        "key": "a06a9aec-fd5b-4c3e-a81f-eb46bb384100",
        "anchor": "Adalimumab",
        "fields": {
            "modality": ("antibody", ("recombinant human IgG1 monoclonal antibody",)),
            "construct": (
                "igg1-heavy+light",
                (
                    "human derived heavy and light chain variable regions and "
                    "human IgG1:k constant regions",
                ),
            ),
            "expression_system": ("CHO", ("Chinese Hamster Ovary (CHO)",)),
            "intended_function": (
                "tnf-alpha-receptor-interaction-blockade",
                (
                    "Adalimumab binds specifically to TNF-alpha and blocks its "
                    "interaction with the p55 and p75 cell surface TNF receptors",
                ),
            ),
        },
        "assembly": "heavy+light",
        "parts_distinguished": True,
    },
}


def snapshot_file(lab_dir: Path, protocol: dict[str, Any]) -> Path:
    return lab_dir.parents[1] / cast(str, protocol["sources"]["snapshot"]["path"])


def load_snapshot(lab_dir: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    path = snapshot_file(lab_dir, protocol)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assignments = [
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "SNAPSHOT_JSON"
        ]
        if len(assignments) != 1:
            raise AuditError("snapshot literal is missing or duplicated")
        literal = ast.literal_eval(assignments[0])
        snapshot = json.loads(literal)
    except (OSError, UnicodeError, SyntaxError, TypeError, ValueError) as error:
        raise AuditError("snapshot cannot be read") from error
    validate_snapshot(snapshot, protocol)
    return cast(dict[str, Any], snapshot)


def render_snapshot(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    chunks = [payload[index : index + 72] for index in range(0, len(payload), 72)]
    literals = [
        repr(chunk) if '"' in chunk else json.dumps(chunk, ensure_ascii=False) for chunk in chunks
    ]
    lines = [
        '"""Committed scoped excerpts from live therapeutic-entity records."""',
        "",
        "SNAPSHOT_JSON = (",
        *(f"    {literal}" for literal in literals),
        ")",
        "",
    ]
    return "\n".join(lines)


def validate_snapshot(snapshot: Any, protocol: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "schema_version",
        "protocol_id",
        "fetched_at_utc",
        "uniprot_search",
        "records",
    }:
        raise AuditError("snapshot field set")
    if snapshot["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
        raise AuditError("snapshot schema version")
    if snapshot["protocol_id"] != PROTOCOL_ID:
        raise AuditError("snapshot protocol id")
    try:
        fetched = datetime.fromisoformat(snapshot["fetched_at_utc"])
        offset = fetched.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("not UTC")
    except (TypeError, ValueError, AttributeError) as error:
        raise AuditError("snapshot fetch time") from error
    search = snapshot["uniprot_search"]
    if not isinstance(search, dict) or set(search) != {
        "url",
        "retrieved_bytes",
        "result_accessions",
    }:
        raise AuditError("UniProt search receipt")
    source = protocol["sources"]["uniprot"]
    if not str(search["url"]).startswith(source["search_endpoint"] + "?"):
        raise AuditError("UniProt search URL")
    if sorted(search["result_accessions"]) != sorted(source["accessions"]):
        raise AuditError("UniProt search accession set")
    if not isinstance(search["retrieved_bytes"], int) or search["retrieved_bytes"] <= 0:
        raise AuditError("UniProt search response length")
    records = snapshot["records"]
    if not isinstance(records, list):
        raise AuditError("snapshot records")
    expected_keys = {("uniprot", key) for key in source["accessions"]} | {
        ("dailymed", label["setid"]) for label in protocol["sources"]["dailymed"]["labels"]
    }
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            raise AuditError("source record must be an object")
        source_name = record.get("source")
        key = record.get("key")
        if not isinstance(source_name, str) or not isinstance(key, str):
            raise AuditError("source record identity")
        identity = (source_name, key)
        if identity in seen or identity not in expected_keys:
            raise AuditError("duplicate or unexpected source record")
        seen.add(identity)
        if not isinstance(record.get("retrieved_bytes"), int) or record["retrieved_bytes"] <= 0:
            raise AuditError("source response length")
        if source_name == "uniprot":
            if set(record) != {
                "source",
                "key",
                "url",
                "retrieved_bytes",
                "entry_type",
                "entry_version",
                "annotation_date",
                "protein_name",
                "pharmaceutical_text",
            }:
                raise AuditError("UniProt record fields")
            if record["url"] != source["entry_pattern"].replace("<accession>", key):
                raise AuditError("UniProt record URL")
            if record["entry_type"] != "UniProtKB reviewed (Swiss-Prot)":
                raise AuditError("UniProt record is not reviewed")
            if not isinstance(record["entry_version"], int) or record["entry_version"] <= 0:
                raise AuditError("UniProt entry version")
            if not isinstance(record["protein_name"], str) or not record["protein_name"].strip():
                raise AuditError("UniProt protein name")
            if not isinstance(record["pharmaceutical_text"], list) or not all(
                isinstance(text, str) and text.strip() for text in record["pharmaceutical_text"]
            ):
                raise AuditError("UniProt pharmaceutical text")
        else:
            if set(record) != {
                "source",
                "key",
                "url",
                "retrieved_bytes",
                "document_id",
                "version",
                "effective_time",
                "description",
                "mechanism",
            }:
                raise AuditError("DailyMed record fields")
            if record["url"] != protocol["sources"]["dailymed"]["endpoint_pattern"].replace(
                "<setid>", key
            ):
                raise AuditError("DailyMed record URL")
            if not isinstance(record["version"], int) or record["version"] <= 0:
                raise AuditError("DailyMed version")
            for field in ("description", "mechanism"):
                if not isinstance(record[field], list) or not all(
                    isinstance(text, str) and text.strip() for text in record[field]
                ):
                    raise AuditError(f"DailyMed {field} paragraphs")
    if seen != expected_keys:
        raise AuditError("missing source record")


def classify_record(record: dict[str, Any], entity: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Extract only product-linked claims that the declared source passage contains."""
    source = record["source"]
    if record["key"] != spec["key"]:
        raise AuditError(f"{entity}: source key differs")
    passages = (
        record["pharmaceutical_text"]
        if source == "uniprot"
        else [*record["description"], *record["mechanism"]]
    )
    text = " ".join(passages)
    if spec["anchor"].casefold() not in text.casefold():
        raise AuditError(f"{entity}: product absent from source passage")
    values: dict[str, str | None] = {}
    stated: dict[str, bool] = {}
    for field in FIELD_NAMES:
        evidence = spec["fields"][field]
        if evidence is None:
            values[field] = None
            stated[field] = False
            continue
        value, quotes = evidence
        if field == "modality" and source == "uniprot":
            if (
                record["entry_type"] != "UniProtKB reviewed (Swiss-Prot)"
                or not record["protein_name"]
            ):
                raise AuditError(f"{entity}: UniProt protein modality is unsupported")
        elif not quotes:
            raise AuditError(f"{entity}: {field} has no product-specific evidence")
        if any(quote not in text for quote in quotes):
            raise AuditError(f"{entity}: {field} evidence missing from {source} record")
        values[field] = value
        stated[field] = True
    defined = stated["modality"] and stated["construct"] and stated["expression_system"]
    return {
        "entity": entity,
        "source": source,
        "field_stated": stated,
        "values": values,
        "assembly": spec["assembly"],
        "parts_distinguished": spec["parts_distinguished"],
        "defined_construct": defined,
    }


def classified_source_rows(
    snapshot: dict[str, Any], protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    validate_snapshot(snapshot, protocol)
    record_index = {(record["source"], record["key"]): record for record in snapshot["records"]}
    entity_ids = {entity["id"] for entity in protocol["entities"]}
    if {entity for entity, _ in SOURCE_SPECS} != entity_ids:
        raise AuditError("source plan and entity list differ")
    return [
        classify_record(record_index[(source, spec["key"])], entity, spec)
        for (entity, source), spec in sorted(SOURCE_SPECS.items())
    ]


def audit_records(snapshot: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    source_rows = classified_source_rows(snapshot, protocol)
    entity_ids = {entity["id"] for entity in protocol["entities"]}
    by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        by_entity[row["entity"]].append(row)
    entity_rows = []
    for entity in sorted(entity_ids):
        rows = by_entity[entity]
        fields = {name: any(row["field_stated"][name] for row in rows) for name in FIELD_NAMES}
        entity_rows.append(
            {
                "entity": entity,
                "field_stated": fields,
                "field_count": sum(fields.values()),
                "defined_construct": any(row["defined_construct"] for row in rows),
            }
        )
    buckets = {
        "all_four": [row["entity"] for row in entity_rows if row["field_count"] == 4],
        "some_two_or_three": [row["entity"] for row in entity_rows if row["field_count"] in (2, 3)],
        "one": [row["entity"] for row in entity_rows if row["field_count"] == 1],
        "zero": [row["entity"] for row in entity_rows if row["field_count"] == 0],
    }
    gaps = {
        "construct_without_host": [
            {"entity": row["entity"], "source": row["source"]}
            for row in source_rows
            if row["field_stated"]["construct"] and not row["field_stated"]["expression_system"]
        ],
        "host_without_construct": [
            {"entity": row["entity"], "source": row["source"]}
            for row in source_rows
            if row["field_stated"]["expression_system"] and not row["field_stated"]["construct"]
        ],
    }
    disagreements: list[dict[str, str]] = []
    coverage_differences: list[dict[str, str]] = []
    for entity, rows in sorted(by_entity.items()):
        for left, right in combinations(rows, 2):
            for name in FIELD_NAMES:
                left_value = left["values"][name]
                right_value = right["values"][name]
                if left_value is None and right_value is not None:
                    coverage_differences.append(
                        {"entity": entity, "field": name, "stated_by": right["source"]}
                    )
                elif right_value is None and left_value is not None:
                    coverage_differences.append(
                        {"entity": entity, "field": name, "stated_by": left["source"]}
                    )
                elif (
                    left_value is not None and right_value is not None and left_value != right_value
                ):
                    disagreements.append(
                        {
                            "entity": entity,
                            "field": name,
                            "left_source": left["source"],
                            "left_value": left_value,
                            "right_source": right["source"],
                            "right_value": right_value,
                        }
                    )
    result = {
        "entity_count": len(entity_rows),
        "per_field_counts": {
            name: {
                "stated": sum(row["field_stated"][name] for row in entity_rows),
                "unstated": sum(not row["field_stated"][name] for row in entity_rows),
            }
            for name in FIELD_NAMES
        },
        "entities_by_fields": buckets,
        "per_entity": entity_rows,
        "per_source": [
            {
                "entity": row["entity"],
                "source": row["source"],
                "field_stated": row["field_stated"],
                "assembly": row["assembly"],
                "parts_distinguished": row["parts_distinguished"],
                "defined_construct": row["defined_construct"],
            }
            for row in source_rows
        ],
        "gaps": gaps,
        "source_coverage_differences": coverage_differences,
        "source_disagreements": disagreements,
    }
    failures = check_invariants(result)
    if failures:
        raise AuditError("; ".join(failures))
    return result


def check_invariants(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    try:
        rows = result["per_entity"]
        source_rows = result["per_source"]
        if result["entity_count"] != len(rows):
            failures.append("entity count")
        ids = [row["entity"] for row in rows]
        if ids != sorted(set(ids)):
            failures.append("entity identities")
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for source_row in source_rows:
            grouped[source_row["entity"]].append(source_row)
            flags = source_row["field_stated"]
            if set(flags) != set(FIELD_NAMES) or not all(
                type(flag) is bool for flag in flags.values()
            ):
                failures.append("source field flags")
            expected_defined = (
                flags["modality"] and flags["construct"] and flags["expression_system"]
            )
            if source_row["defined_construct"] is not expected_defined:
                failures.append(f"{source_row['entity']}: source definition rule")
            if source_row["parts_distinguished"] and not flags["construct"]:
                failures.append(f"{source_row['entity']}: parts without construct")
        if set(grouped) != set(ids):
            failures.append("source/entity identities")
        for row in rows:
            fields = row["field_stated"]
            if set(fields) != set(FIELD_NAMES) or not all(
                type(flag) is bool for flag in fields.values()
            ):
                failures.append(f"{row['entity']}: field flags")
            if row["field_count"] != sum(fields.values()):
                failures.append(f"{row['entity']}: field count")
            for name in FIELD_NAMES:
                if fields[name] is not any(
                    item["field_stated"][name] for item in grouped[row["entity"]]
                ):
                    failures.append(f"{row['entity']}: {name} source agreement")
            if row["defined_construct"] is not any(
                item["defined_construct"] for item in grouped[row["entity"]]
            ):
                failures.append(f"{row['entity']}: entity definition rule")
            if row["defined_construct"] and not (
                fields["construct"] and fields["expression_system"]
            ):
                failures.append(f"{row['entity']}: modality-only or hostless definition")
        for name in FIELD_NAMES:
            count = result["per_field_counts"][name]
            if count["stated"] != sum(row["field_stated"][name] for row in rows):
                failures.append(f"{name}: stated count")
            if count["stated"] + count["unstated"] != len(rows):
                failures.append(f"{name}: total")
        buckets = result["entities_by_fields"]
        expected_buckets = {
            "all_four": [row["entity"] for row in rows if row["field_count"] == 4],
            "some_two_or_three": [row["entity"] for row in rows if row["field_count"] in (2, 3)],
            "one": [row["entity"] for row in rows if row["field_count"] == 1],
            "zero": [row["entity"] for row in rows if row["field_count"] == 0],
        }
        if buckets != expected_buckets:
            failures.append("field-count buckets")
        expected_gaps = {
            "construct_without_host": [
                {"entity": item["entity"], "source": item["source"]}
                for item in source_rows
                if item["field_stated"]["construct"]
                and not item["field_stated"]["expression_system"]
            ],
            "host_without_construct": [
                {"entity": item["entity"], "source": item["source"]}
                for item in source_rows
                if item["field_stated"]["expression_system"]
                and not item["field_stated"]["construct"]
            ],
        }
        if result["gaps"] != expected_gaps:
            failures.append("construct/host gaps")
    except (KeyError, TypeError, ValueError, AttributeError):
        failures.append("count structure")
    return failures
