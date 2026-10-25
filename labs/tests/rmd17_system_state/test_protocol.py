from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.rmd17_system_state.protocol import (
    DEVELOPMENT_SYSTEM_IDS,
    DISTANCE_EDGES,
    FROZEN_ALPHAS,
    LOCKED_SYSTEM_IDS,
    PROTOCOL_ID,
    REQUIRED_NPZ_KEYS,
    SYSTEMS,
)


def test_protocol_constants_freeze_exact_source_systems_and_roles() -> None:
    assert PROTOCOL_ID == "rmd17-system-state-v1"
    assert tuple(SYSTEMS) == ("ethanol", "malonaldehyde", "benzene", "uracil")
    assert DEVELOPMENT_SYSTEM_IDS == ("ethanol", "malonaldehyde")
    assert LOCKED_SYSTEM_IDS == ("benzene", "uracil")
    assert [(spec.filename, spec.file_id, spec.expected_atoms) for spec in SYSTEMS.values()] == [
        ("rmd17_ethanol.npz", "62265733", 9),
        ("rmd17_malonaldehyde.npz", "62265736", 9),
        ("rmd17_benzene.npz", "62265739", 12),
        ("rmd17_uracil.npz", "62265745", 12),
    ]
    assert REQUIRED_NPZ_KEYS == (
        "nuclear_charges",
        "coords",
        "energies",
        "forces",
        "old_indices",
        "old_energies",
        "old_forces",
    )


def test_protocol_constants_freeze_sampling_features_and_model_grid() -> None:
    assert len(DISTANCE_EDGES) == 101
    assert DISTANCE_EDGES[0] == 0.0
    assert DISTANCE_EDGES[-1] == 10.0
    assert tuple(FROZEN_ALPHAS) == (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)


def test_public_protocol_json_has_no_checksum_and_prohibits_auxiliary_labels() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    payload = json.loads(
        (repository_root / "labs" / "rmd17_system_state" / "protocol.json").read_text(
            encoding="utf-8"
        )
    )
    serialised = json.dumps(payload).lower()
    assert payload["protocol_id"] == PROTOCOL_ID
    assert payload["source"]["figshare_article"] == "12672038"
    assert payload["source"]["version"] == 4
    assert payload["source"]["licence"] == "CC0"
    assert payload["feature_and_target_boundaries"]["prohibited_arrays"] == [
        "forces",
        "old_energies",
        "old_forces",
    ]
    assert "checksum" not in serialised
