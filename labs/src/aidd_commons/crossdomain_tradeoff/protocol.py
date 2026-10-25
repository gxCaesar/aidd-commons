"""Frozen source and decision contract for a cross-domain nomination decision.

The rule executed here is the curriculum's own. The candidate-nomination
workbook states a fictional project's teaching thresholds, five required
inputs and the three next decisions a reader may take, and this laboratory
executes that rule in one place: on the workbook's own teaching table, where
the rule discriminates between three candidates, and on the measured ChEMBL 37
cohort, where the same rule is applied to real records.

The thresholds, the five inputs and the rule are declared here, before any
measurement is read, so that the decision cannot be tuned to the compounds it
judges. No composite, no weighted sum, no overall desirability value and no
ordering of the candidates is produced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from aidd_commons.multi_endpoint_integration.protocol import (
    expected_contract as integration_contract,
)

PROTOCOL_ID = "chembl37-crossdomain-tradeoff-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.crossdomain-tradeoff-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.crossdomain-tradeoff-summary.v1"
ISSUED_ON = "2026-10-24"
PACKAGE_VERSION_FALLBACK = "0.2.0rc1"

#: The five inputs the curriculum's nomination rule names, in the rule's order.
INPUTS = (
    "potency",
    "selectivity_ratio",
    "exposure_ratio",
    "safety_package",
    "functional_validation",
)

#: The teaching thresholds the workbook states for its fictional project.
POTENCY_LIMIT_NM = 50.0
SELECTIVITY_RATIO_MINIMUM = 20.0
EXPOSURE_RATIO_MINIMUM = 3.0

#: The state of one required input for one candidate.
INPUT_STATES = ("supplied", "absent", "not covered", "indeterminate")

#: The next decision the evidence points to, which is the workbook's own.
NEXT_DECISIONS = ("revise the candidate", "close an evidence gap", "change the product profile")

#: The graded evidence kinds a supplied input may rest on.
EVIDENCE_KINDS = (
    "single-activity point",
    "multi-activity median",
    "matched same-document comparison",
    "constructed teaching row",
    "none",
)

INPUT_RULES = {
    "potency": (
        "Supplied from the admitted response-potency points in nM, and the gate is a matched "
        f"potency of at most {POTENCY_LIMIT_NM:g} nM. It is indeterminate when the admitted "
        "records mix endpoint types, because the representative value then aggregates "
        "quantities that are not the same measure. The scope is observed in vitro response "
        "potency in the named assay and document only."
    ),
    "selectivity_ratio": (
        "Not covered by the measured families. The requirement is a selectivity ratio of at "
        f"least {SELECTIVITY_RATIO_MINIMUM:g} against an intended target, and the cohort "
        "holds inhibition potency against two drug-metabolising enzymes, which is not a "
        "selectivity ratio for any target. The scope of the required input is an intended "
        "target."
    ),
    "exposure_ratio": (
        "Not covered by the measured families. The requirement is an exposure-to-effective-"
        f"concentration ratio of at least {EXPOSURE_RATIO_MINIMUM:g}, and the cohort holds in "
        "vitro intrinsic clearance, which is not an exposure and cannot form the ratio "
        "without a declared effective concentration."
    ),
    "safety_package": (
        "Not covered by the measured families. The requirement is an independently reviewed "
        "safety package, and no measured safety material exists for this cohort. A review is a "
        "human decision, so no measurement can supply this input."
    ),
    "functional_validation": (
        "Not covered by the measured families. The requirement is interpretable functional "
        "validation for the compound, and the measured assay records in this repository "
        "classify assay records rather than validate a compound's function."
    ),
}

#: The workbook's own teaching table, carried here so that one rule runs on the
#: same inputs the curriculum teaches.
TEACHING_CASES = (
    {
        "id": "N1",
        "potency_nm": 20.0,
        "selectivity_ratio": 8.0,
        "exposure_ratio": 4.0,
        "safety_package": "available for review",
        "functional_validation": "interpretable",
    },
    {
        "id": "N2",
        "potency_nm": 40.0,
        "selectivity_ratio": 30.0,
        "exposure_ratio": 2.0,
        "safety_package": "available for review",
        "functional_validation": "interpretable",
    },
    {
        "id": "N3",
        "potency_nm": 45.0,
        "selectivity_ratio": 25.0,
        "exposure_ratio": 3.5,
        "safety_package": "missing",
        "functional_validation": "interpretable",
    },
)

COMPOSITE_RULE = (
    "Refuse every composite, weighted sum, overall desirability value and ordering of the "
    "candidates. A candidate is reported as the state of each required input, the input "
    "that blocks it, and the next decision the evidence points to."
)
MISSING_RULE = (
    "A missing input stays missing. It is never filled with a no-risk, adequate-exposure, "
    "clean, safe or interpretable value, and an input that is not covered never passes."
)
REVIEW_RULE = (
    "A safety package that is available for review is not a favourable review, and a review "
    "is not a measurement. The input is supplied as available for review and the decision "
    "still records that the review outcome is not established."
)
TRADE_RULE = (
    "A candidate that misses a numerical threshold on a supplied input is a candidate to "
    "revise. A candidate that misses a required input that is absent or not covered is a "
    "candidate with an evidence gap to close. Changing a threshold so that a favourite "
    "passes is a change to the product requirement and is not a discovery."
)
BOUNDARY_STATEMENT = (
    "These decisions execute the curriculum's nomination rule. They are not a "
    "development-candidate assessment and they nominate nothing. Response potency does not "
    "validate mechanism or intended-target engagement, a comparison between two "
    "drug-metabolising enzymes is not a selectivity ratio, intrinsic clearance is not "
    "exposure, and a safety package that is available for review is not a favourable review. "
    "The thresholds are the fictional project's teaching thresholds and not pharmacological "
    "criteria."
)
EXCLUDED_BY_DESIGN = [
    "any composite score, weighted sum, overall desirability value or ordering of the candidates",
    "any claim that a candidate is nominated, selected or prioritised",
    "any use of a default, class mean or literature value for an absent input",
    "any claim of validated mechanism, intended-target engagement, systemic exposure, "
    "safety, synthesis feasibility or clinical outcome",
    "any reading of a favourable safety review as a safety result",
    "any threshold changed after the measurements were read",
]


class ProtocolContractError(ValueError):
    """The protocol document differs from the declared frozen contract."""


def expected_contract() -> dict[str, Any]:
    """The frozen contract the protocol document must equal."""
    sources = [
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
    sources.append(
        {
            "laboratory": "capstone_workbook",
            "status": "constructed",
            "reader": "site/src/content/docs/learn/candidate-nomination/capstone-workbook.mdx",
            "read_route": "Case 5, the cross-domain nomination with a missing requirement",
            "compound_join": False,
            "licence": "Original teaching material, CC BY 4.0",
        }
    )
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "sources": sources,
        "inputs": [
            {
                "name": name,
                "state_rule": INPUT_RULES[name],
                "threshold": {
                    "potency": {"maximum_nm": POTENCY_LIMIT_NM},
                    "selectivity_ratio": {"minimum": SELECTIVITY_RATIO_MINIMUM},
                    "exposure_ratio": {"minimum": EXPOSURE_RATIO_MINIMUM},
                    "safety_package": None,
                    "functional_validation": None,
                }[name],
            }
            for name in INPUTS
        ],
        "teaching_cases": [dict(case) for case in TEACHING_CASES],
        "input_states": list(INPUT_STATES),
        "next_decisions": list(NEXT_DECISIONS),
        "evidence_kinds": list(EVIDENCE_KINDS),
        "counted_unit": {
            "name": "one candidate's cross-domain nomination decision",
            "cohort_rule": (
                "Every parent the validated multi-endpoint integration laboratory reads that "
                "has at least two measured endpoint families, because a cross-domain decision "
                "cannot be posed on a single measured family."
            ),
        },
        "rules": {
            "composite_score": COMPOSITE_RULE,
            "missing_input": MISSING_RULE,
            "review_input": REVIEW_RULE,
            "next_decision": TRADE_RULE,
        },
        "boundary_statement": BOUNDARY_STATEMENT,
        "excluded_by_design": EXCLUDED_BY_DESIGN,
    }


def load_protocol_document(path: Path) -> dict[str, Any]:
    """Read the protocol document and refuse it unless it is the frozen one."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError(f"cannot read protocol: {error}") from error
    if not isinstance(document, dict) or document != expected_contract():
        raise ProtocolContractError("protocol differs from the frozen contract")
    return cast(dict[str, Any], document)
