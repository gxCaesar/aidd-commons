"""Reject changes to the frozen data and analysis contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aidd-commons.applicability-domain-audit-protocol.v1"
PROTOCOL_ID = "freesolv-v052-applicability-domain-v1"
SOURCE_PATH = ".cache/freesolv/freesolv-v0.52-database.txt"
SOURCE_BYTES = 144_897
SEED = 20_260_904
TRAIN_FRACTION = 0.8
PROPERTIES = ("MolWt", "MolLogP", "TPSA", "NumHDonors", "NumHAcceptors")
MORGAN_RADIUS = 2
MORGAN_BITS = 2048
RIDGE_ALPHA = 1.0
EXCLUSIONS = (
    "A claim that this chosen distance is the applicability domain",
    "A performance estimate or inside-domain decision for a new molecule",
    "Tuning the representation, distance, split or baseline to improve a number",
    "A chemical-mechanism claim from a computed-property distance",
)


class ProtocolError(ValueError):
    """The on-disk protocol differs from the compiled contract."""


def expected_protocol() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": "2026-10-23",
        "source": {
            "path": SOURCE_PATH,
            "bytes": SOURCE_BYTES,
            "release": "FreeSolv v0.52",
            "license": "unverified; the v0.52 release metadata does not declare licence terms",
            "read_on": "2026-10-23",
            "route": (
                "local cache of "
                "https://raw.githubusercontent.com/MobleyLab/FreeSolv/v0.52/database.txt"
            ),
        },
        "representation": {
            "kind": "RDKit computed 2D properties",
            "properties": list(PROPERTIES),
            "scaling": (
                "divide each absolute property difference by the training population "
                "standard deviation; use 1 when that deviation is 0"
            ),
            "choice": (
                "laboratory diagnostic choice, not a chemical or applicability-domain definition"
            ),
        },
        "distance": (
            "mean of the five scaled absolute property differences to the nearest training molecule"
        ),
        "split": {
            "kind": "Bemis-Murcko scaffold",
            "seed": SEED,
            "train_fraction": TRAIN_FRACTION,
            "target_rule": "floor(0.8 * molecule_count + 0.5)",
            "assignment_rule": (
                "descending scaffold-group size; sorted equal-size keys shuffled with the seed; "
                "assign whole groups to train until the target is reached, then to test"
            ),
            "acyclic_rule": "acyclic:<canonical_isomeric_smiles> singleton group",
        },
        "baseline": {
            "model": "Ridge",
            "alpha": RIDGE_ALPHA,
            "fingerprint": "chirality-aware RDKit Morgan",
            "radius": MORGAN_RADIUS,
            "bits": MORGAN_BITS,
            "target_column": (
                "fourth semicolon-delimited field, experimental hydration free energy in kcal/mol"
            ),
            "role": (
                "cheapest fitted model already taught by the curriculum, "
                "not best model for the data"
            ),
        },
        "error_halves": (
            "sort test molecules by nearest-training distance, then source ID; "
            "lower floor(n/2) versus remaining upper half"
        ),
        "excluded_by_design": list(EXCLUSIONS),
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    expected = expected_protocol()
    if not isinstance(value, dict) or value != expected:
        changed = [
            key
            for key in expected
            if not isinstance(value, dict) or value.get(key) != expected[key]
        ]
        detail = ", ".join(changed) or "extra field"
        raise ProtocolError(f"changed frozen protocol fields: {detail}")
    return value
