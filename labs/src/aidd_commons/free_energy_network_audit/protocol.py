"""Frozen source and calculation rules for the OpenFE network audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

PROTOCOL_ID = "openfe-jacs-relative-network-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.free-energy-network-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.free-energy-network-summary.v1"
ISSUED_ON = "2026-10-23"
RECORD_URL = "https://zenodo.org/records/21797903"
FILE_PREFIX = "AlchemicalNetwork-"
FILE_SUFFIX = "-openff-openff_3_0_0_alpha1b_opc3-rbfe_pontibus_jacs_set_"
SOURCE_FILES = (
    ("jnk1", "6cea205bc124349b8add8824e2060147", 542432),
    ("bace", "58ef1baba714145eaddb8f81abf609ce", 867452),
    ("tyk2", "51caad3a5d3daea240406eb23fa6dad6", 434490),
    ("thrombin", "7fcf1d4cb0a6af702747de83fc23af69", 333717),
    ("mcl1", "ee5422ba932ced782b51da9bb9eb24ff", 981146),
    ("ptp1b", "3885e858e4b36849e110edbebe348ae2", 611820),
    ("cdk2", "8b3e6b25fe046924998a1f520c798b19", 552594),
    ("p38", "c613a533bdaa47f92e9a1cf4d58fe6dd", 867679),
)


class ProtocolError(ValueError):
    """The local protocol differs from the declared one."""


def source_filename(system: str, key: str) -> str:
    return f"{FILE_PREFIX}{key}{FILE_SUFFIX}{system}.json.bz2"


def expected_fields() -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "run_basis": "Fresh independent CPU computation from a locally cached source snapshot.",
        "source": {
            "record_id": 21797903,
            "record_url": RECORD_URL,
            "publication_date": "2026-08-04",
            "licence": "CC BY 4.0",
            "retrieval_route": RECORD_URL + "/files/<file name>?download=1",
            "snapshot_rule": (
                "Download each named archive into the lab cache, validate its byte length "
                "and structure, and retain that local copy for offline reruns."
            ),
            "files": [
                {"system": system, "name": source_filename(system, key), "bytes": size}
                for system, key, size in SOURCE_FILES
            ],
        },
        "endpoint_rule": {
            "kind": "relative binding free energy",
            "direction": "ligand A to ligand B",
            "pairing": (
                "Pair the complex and solvent transformations for the same ordered "
                "ligand mapping. DeltaDeltaG_bind(A to B) = DeltaG_complex(A to B) "
                "- DeltaG_solvent(A to B)."
            ),
            "separation": (
                "A solvent edge and a complex edge are different quantities. "
                "This calculation does not produce an absolute binding free energy."
            ),
        },
        "estimate_rule": {
            "value": (
                "For each distinct repeat ID select its highest recorded generation, then "
                "take the arithmetic mean of the three selected estimates per leg. "
                "Count successful unit estimates and unit records without an estimate separately."
            ),
            "uncertainty": (
                "For each leg use the larger of the propagated reported standard error "
                "of its mean and its between-repeat standard error. Treat distinct "
                "repeats, paired legs, and graph edges as independent for propagation."
            ),
            "unit": "kilocalorie_per_mole",
        },
        "cycle_rule": {
            "selection": (
                "Build a deterministic spanning forest from binding edges sorted by name. "
                "Each non-tree edge and its unique tree path form one fundamental cycle."
            ),
            "sum": "Signed sum of ordered relative binding edge means around the cycle.",
            "tolerance": (
                "Two times the quadrature sum of the included edge standard errors, "
                "in kilocalorie per mole. This tolerance is fixed before examining cycle residuals."
            ),
            "closure": (
                "A cycle closes only if the absolute signed sum is at most its tolerance. "
                "Every inconsistent cycle is failed and retains its name and discrepancy."
            ),
        },
        "counted_unit": ("One transformation edge. Three distinct repeat IDs measure one edge."),
        "excluded_by_design": [
            "Any claim that this laboratory computes an absolute binding free energy.",
            "Any claim that a closed cycle means an estimate is correct or converged.",
            "Any ranking of the eight systems by cycle closure.",
            "Any comparison to assay endpoints or experimental affinity.",
        ],
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    expected = expected_fields()
    if document != expected:
        raise ProtocolError("protocol differs from the frozen contract")
    return cast(dict[str, Any], document)
