"""Frozen source and claim contract for candidate evidence chains."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from aidd_commons.multi_endpoint_integration.protocol import (
    expected_contract as integration_contract,
)

PROTOCOL_ID = "chembl37-candidate-evidence-chain-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.candidate-evidence-chain-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.candidate-evidence-chain-summary.v1"
ISSUED_ON = "2026-10-23"
PACKAGE_VERSION_FALLBACK = "0.2.0rc1"
LINKS = (
    "mechanism",
    "target",
    "activity",
    "selectivity",
    "exposure",
    "safety",
    "synthesis",
    "reproducibility",
)
EXAMPLE_PARENTS = ("CHEMBL1144", "CHEMBL1232461", "CHEMBL1963249")
STATES = ("measured", "absent", "constructed", "not covered")
CLAIM_GATE = (
    "A chain supports a claim only when every link is measured. An absent, constructed or not "
    "covered link stops the claim, even when later links have measurements."
)
SCOPE_RULE = (
    "A claim may not exceed the first measured link's own scope. A supported chain carries "
    "exactly that scope."
)
BOUNDARY_STATEMENT = (
    "These chains assemble selected ChEMBL 37 measurements, not a development-candidate "
    "assessment. Response potency does not validate mechanism or intended-target engagement. "
    "A matched CYP3A4/CYP2D6 comparison describes only those enzymes, and intrinsic clearance "
    "is not systemic exposure. This repository has no measured safety, synthesis or clinical "
    "outcome for these parents. Constructed teaching cases cannot fill those links, and the "
    "missing links are not known to be fillable."
)
EXCLUDED_BY_DESIGN = [
    "any claim that a chain makes a compound a development candidate",
    "any ranking of compounds by how far their chains reach",
    "any use of a constructed link as if it were measured",
    "any claim of validated mechanism, intended-target engagement, systemic exposure, "
    "safety, synthesis feasibility or clinical outcome",
    "any default, class mean or literature value substituted for an absent compound measurement",
]


class ProtocolContractError(ValueError):
    """The protocol document differs from the declared frozen contract."""


def expected_contract() -> dict[str, Any]:
    measured_sources = [
        {
            "laboratory": source["name"],
            "status": "measured",
            "reader": source["read_route"],
            "read_route": source["cache_directory"],
            "snapshot": source["snapshot"],
            "snapshot_byte_length": source["snapshot_byte_length"],
            "read_on": source["read_on"],
            "archive": source["archive"],
            "licence": source["licence"],
        }
        for source in integration_contract()["sources"]
    ]
    constructed_sources = [
        {
            "laboratory": "safety_evidence",
            "status": "constructed",
            "reader": "labs/safety_evidence/inspect_safety.py",
            "read_route": "labs/safety_evidence/dataset.json",
            "compound_join": False,
            "licence": "Original teaching material, CC BY 4.0",
        },
        {
            "laboratory": "retro_disconnection",
            "status": "constructed",
            "reader": "labs/retro_disconnection/inspect_disconnection.py",
            "read_route": "labs/retro_disconnection/routes.json",
            "compound_join": False,
            "licence": "Original teaching material, CC BY 4.0",
        },
    ]
    link_rules = {
        "mechanism": "Not covered without a compound-specific measured mechanism validation.",
        "target": (
            "Not covered without measured intended-target engagement or validation for this parent."
        ),
        "activity": (
            "Measured for admitted exact AC50, EC50 or IC50 response-potency points; "
            "otherwise absent."
        ),
        "selectivity": (
            "Measured only for one admitted CYP3A4 and one CYP2D6 IC50 from the same "
            "document, each based on one activity; otherwise absent. The scope is these "
            "CYP enzymes, not intended-target selectivity."
        ),
        "exposure": (
            "Measured only as in vitro intrinsic clearance in a named assay system; "
            "otherwise absent. It does not establish systemic exposure."
        ),
        "safety": (
            "Not covered for these parents. The safety teaching cases are constructed "
            "and cannot be joined to them."
        ),
        "synthesis": (
            "Not covered for these parents. Constructed route recovery is not a measured "
            "synthesis or feasibility result."
        ),
        "reproducibility": (
            "Not covered without independent replication of this compound's chain; "
            "repeated rows or a rerun of this audit do not supply it."
        ),
    }
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "sources": measured_sources + constructed_sources,
        "links": [{"name": name, "state_rule": link_rules[name]} for name in LINKS],
        "states": list(STATES),
        "example_parent_ids": list(EXAMPLE_PARENTS),
        "counted_unit": {
            "name": "one ChEMBL parent molecule's eight-link chain",
            "join_rule": (
                "Use only equal parent_molecule_chembl_id from the three validated "
                "measured readers. Constructed records have no join to these parents."
            ),
        },
        "rules": {"claim_gate": CLAIM_GATE, "claim_scope": SCOPE_RULE},
        "excluded_by_design": EXCLUDED_BY_DESIGN,
    }


def load_protocol_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError(f"cannot read protocol: {error}") from error
    if not isinstance(document, dict) or document != expected_contract():
        raise ProtocolContractError("protocol differs from the frozen contract")
    return cast(dict[str, Any], document)
