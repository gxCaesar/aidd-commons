from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_ID = "rmd17-system-state-v1"
FIGSHARE_ARTICLE_ID = "12672038"
FIGSHARE_DOI = "10.6084/m9.figshare.12672038.v4"
PRIMARY_PAPER_DOI = "10.1088/2632-2153/abba6f"
LICENCE = "CC0"
EXPECTED_FRAME_COUNT = 100_000
SAMPLED_FRAME_COUNT = 1_000
TRAIN_FRAME_COUNT = 600
VALIDATION_FRAME_COUNT = 200
EVALUATION_FRAME_COUNT = 200
DISTANCE_BIN_WIDTH = 0.1
DISTANCE_MAXIMUM = 10.0
DISTANCE_EDGES = tuple(index * DISTANCE_BIN_WIDTH for index in range(101))
FROZEN_ALPHAS = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
REQUIRED_NPZ_KEYS = (
    "nuclear_charges",
    "coords",
    "energies",
    "forces",
    "old_indices",
    "old_energies",
    "old_forces",
)


@dataclass(frozen=True)
class SystemSpec:
    system_id: str
    filename: str
    file_id: str
    expected_atoms: int


SYSTEMS: dict[str, SystemSpec] = {
    "ethanol": SystemSpec("ethanol", "rmd17_ethanol.npz", "62265733", 9),
    "malonaldehyde": SystemSpec("malonaldehyde", "rmd17_malonaldehyde.npz", "62265736", 9),
    "benzene": SystemSpec("benzene", "rmd17_benzene.npz", "62265739", 12),
    "uracil": SystemSpec("uracil", "rmd17_uracil.npz", "62265745", 12),
}
DEVELOPMENT_SYSTEM_IDS = ("ethanol", "malonaldehyde")
LOCKED_SYSTEM_IDS = ("benzene", "uracil")
