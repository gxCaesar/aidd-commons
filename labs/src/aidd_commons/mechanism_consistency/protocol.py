"""Frozen decision contract for the cross-compound mechanism contrast."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from aidd_commons.l1000_perturbation_context.protocol import CELL_LINE_A, CELL_LINE_B, NULL_ROTATION

PROTOCOL_ID = "lincs-l1000-mechanism-consistency-v1"
PROTOCOL_SCHEMA = "aidd-commons.mechanism-consistency-protocol.v1"
SUMMARY_SCHEMA = "aidd-commons.mechanism-consistency-summary.v1"
INFORMATIVE_RHO_MINIMUM = 0.1


class ProtocolError(ValueError):
    """The on-disk declaration differs from the frozen decision contract."""


def expected_protocol() -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "issued_on": "2026-10-23",
        "run_basis": (
            "Fresh independent CPU computation from the owning laboratory's cached, frozen "
            "LINCS L1000 snapshot."
        ),
        "source": {
            "snapshot": "GEO GSE70138, 2017-03-06 Level 2 release and matching metadata",
            "reader": "aidd_commons.l1000_perturbation_context.data.load_cached_cell_lines",
            "route": ".cache/l1000_perturbation_context/",
            "download_rule": (
                "Reuse the owning laboratory's cache. This laboratory does not fetch or copy data."
            ),
        },
        "counted_unit": (
            f"One compound with an admitted vehicle-corrected response in both {CELL_LINE_A} "
            f"and {CELL_LINE_B} at 10.0 um and 24.0 h."
        ),
        "comparison": {
            "matched": (
                "Spearman rho of the same compound's 978-landmark-gene differential profiles "
                f"in {CELL_LINE_A} and {CELL_LINE_B}."
            ),
            "mismatched": (
                f"Spearman rho of the {CELL_LINE_A} profile with the next compound's "
                f"{CELL_LINE_B} profile in the owning protocol's fixed sorted-ID rotation "
                f"by {NULL_ROTATION}."
            ),
            "informative_rho_minimum": INFORMATIVE_RHO_MINIMUM,
            "threshold_rule": (
                "A matched rho below 0.1 is uninformative and undecided, regardless of the "
                "mismatched rho."
            ),
            "mediator_specific": (
                "If matched rho is at least 0.1 and mismatched rho is below 0.1, place the "
                "pattern on the mediator-specific side."
            ),
            "generic_stress": (
                "If matched rho is at least 0.1 and mismatched rho is strictly greater than "
                "matched rho, place the pattern on the generic-stress side."
            ),
            "shared_control": (
                "If matched and mismatched rho are both at least 0.1 and mismatched rho is "
                "no greater than matched rho, the control also agrees and the case is undecided."
            ),
            "undecided_rule": "No undecided compound counts as mediator-specific support.",
        },
        "explanations": {
            "mediator_specific": (
                "The transcriptional change follows the compound acting through its "
                "intended target."
            ),
            "generic_stress": (
                "Any compound that perturbs the cell produces a similar change regardless "
                "of its target."
            ),
        },
        "excluded_by_design": [
            "Any claim that this correlation comparison establishes a disease mechanism.",
            "Any claim that an individual compound's response is target-mediated.",
            "Any ranking of compounds by how well their responses agree.",
            "Any claim that this comparison establishes disease relevance, target engagement, "
            "or whether a compound is worth making.",
        ],
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if document != expected_protocol():
        raise ProtocolError("protocol differs from the frozen contract")
    return cast(dict[str, Any], document)
