"""Frozen contract validation before any result directory is made."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROTOCOL_ID = "skempi2-complex-holdout-v1"
SCHEMA_VERSION = "aidd-commons.skempi-affinity-protocol.v1"
SOURCE_URL = (
    "https://huggingface.co/datasets/LiteFold/SKEMPI2/resolve/main/"
    "tables/labeled_skempi2_skempi_v2.csv.jsonl"
)
EXPECTED_BYTES = 6_148_969
SEED = 20261021
HEADER = (
    "#Pdb;Mutation(s)_PDB;Mutation(s)_cleaned;iMutation_Location(s);"
    "Hold_out_type;Hold_out_proteins;Affinity_mut (M);Affinity_mut_parsed;"
    "Affinity_wt (M);Affinity_wt_parsed;Reference;Protein 1;Protein 2;"
    "Temperature;kon_mut (M^(-1)s^(-1));kon_mut_parsed;kon_wt (M^(-1)s^(-1));"
    "kon_wt_parsed;koff_mut (s^(-1));koff_mut_parsed;koff_wt (s^(-1));"
    "koff_wt_parsed;dH_mut (kcal mol^(-1));dH_wt (kcal mol^(-1));"
    "dS_mut (cal mol^(-1) K^(-1));dS_wt (cal mol^(-1) K^(-1));"
    "Notes;Method;SKEMPI version"
)


class ProtocolError(ValueError):
    """The on-disk protocol changed from its frozen contract."""


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(value, dict):
        raise ProtocolError("protocol must be an object")
    required: tuple[tuple[str, ...], ...] = (
        ("schema_version", SCHEMA_VERSION),
        ("protocol_id", PROTOCOL_ID),
        ("source", "retrieval_url", SOURCE_URL),
        ("source", "expected_bytes", str(EXPECTED_BYTES)),
        ("alignment", "outer_key", "row"),
        ("alignment", "header_fields", "29"),
        ("alignment", "delimiter", ";"),
        ("entity", "independent_unit", "#Pdb complex"),
        ("entity", "secondary_group", "Hold_out_proteins, including the empty-string group"),
        (
            "entity", "analysis_subset",
            "Hold_out_type == AB/AG and both parsed affinities are finite and positive",
        ),
        ("endpoint", "target", "Affinity_wt_parsed"),
        ("endpoint", "observed_comparator", "Affinity_mut_parsed"),
        ("endpoint", "source_unit", "M"),
        ("endpoint", "analysis_scale", "log10(M)"),
        ("split", "rule", (
            "Sort distinct eligible #Pdb values, shuffle with the fixed seed, and reserve "
            "the first ceil(20% of complexes) for test. Fit any group statistics on "
            "remaining complexes only."
        )),
        ("split", "independent_unit", "#Pdb complex"),
        ("split", "test_fraction", "0.2"),
        ("seed", str(SEED)),
    )
    for item in required:
        current: Any = value
        for key in item[:-1]:
            if not isinstance(current, dict) or key not in current:
                raise ProtocolError(f"missing protocol field: {'.'.join(item[:-1])}")
            current = current[key]
        if str(current) != item[-1]:
            raise ProtocolError(f"changed protocol field: {'.'.join(item[:-1])}")
    if not isinstance(value["alignment"], dict) or (
        "right-pad" not in value["alignment"].get("rule", "")
        or "do not rejoin" not in value["alignment"].get("rule", "")
    ):
        raise ProtocolError("changed alignment rule")
    if not isinstance(value["baseline"], dict) or (
        "Training median" not in value["baseline"].get("group_only", "")
    ):
        raise ProtocolError("changed group baseline")
    if "training complexes only" not in value["baseline"].get("fit_scope", ""):
        raise ProtocolError("changed baseline fit scope")
    return value
