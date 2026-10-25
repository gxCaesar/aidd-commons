"""A self-contained synthetic snapshot for the ROSETTA cross-modality lab.

The known-bad-edit test must be able to run a whole pipeline without a
network and without the real 26 MiB cache, so this module builds a small
published-object-shaped pair of files: a replicate-level transcriptomic
release and a replicate-level imaging release with the same column rules as
the real ones, the same join key, plate-matched controls and two batches.
Everything the contract freezes is computed from these bytes, so a mutated
contract is rejected for the reason it was mutated and not for an
unrelated one.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aidd_commons.rosetta_cross_modality.data import FetchedChunk

PERTURBATION_COUNT = 24
TRANSCRIPTOME_FEATURES = ("200001_at", "200002_s_at", "200003_x_at", "200004_at")
IMAGING_FEATURES = (
    "Cells_AreaShape_Compactness",
    "Nuclei_AreaShape_Compactness",
    "Cytoplasm_Intensity_MeanIntensity_DNA",
    "Cytoplasm_Texture_InfoMeas1_DNA_3_0",
)
IMAGING_PLATES = ("52649", "52651", "52653", "52655")
PLATE_MAPS = {
    "52649": "DOC45.46.47.48",
    "52651": "DOC45.46.47.48",
    "52653": "DOC49.50.51.52",
    "52655": "DOC49.50.51.52",
}
TRANSCRIPTOME_PLATES = ("TA.OE014_A549_96H_X1_B19", "TA.OE015_A549_96H_X1_B19")
CONTROL_NAME = "EMPTY"


def _value(seed: int, index: int, feature: int) -> float:
    """A deterministic, finite, non-constant value."""
    return round(((seed * 37 + index * 11 + feature * 7) % 97) / 10.0 - 4.0, 4)


def _transcriptome_bytes() -> bytes:
    columns = ["id", *TRANSCRIPTOME_FEATURES, "pert_iname", "pert_type", "det_plate",
               "allele", "pert_mfc_desc"]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for index in range(PERTURBATION_COUNT):
        name = f"PERT{index:03d}"
        plate = TRANSCRIPTOME_PLATES[index % len(TRANSCRIPTOME_PLATES)]
        values = [_value(index, 0, feature) for feature in range(len(TRANSCRIPTOME_FEATURES))]
        writer.writerow(
            [
                f"{plate}:A{index:02d}",
                *values,
                name,
                "trt",
                plate,
                f"{name}_allele",
                f"GENE{index:02d}",
            ]
        )
    for index, plate in enumerate(TRANSCRIPTOME_PLATES):
        values = [_value(900 + index, 0, feature) for feature in range(len(TRANSCRIPTOME_FEATURES))]
        writer.writerow(
            [f"{plate}:H01", *values, CONTROL_NAME, "control", plate, "", ""]
        )
    return gzip.compress(buffer.getvalue().encode("utf-8"), mtime=0)


def _imaging_bytes() -> bytes:
    columns = [
        "Metadata_Plate",
        "Metadata_Well",
        "Metadata_Plate_Map_Name",
        "Metadata_pert_name",
        "pert_type",
        *IMAGING_FEATURES,
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for index in range(PERTURBATION_COUNT):
        name = f"PERT{index:03d}"
        plate = IMAGING_PLATES[index % len(IMAGING_PLATES)]
        values = [
            _value(index + 7, 1, feature) for feature in range(len(IMAGING_FEATURES))
        ]
        writer.writerow([plate, f"a{index:02d}", PLATE_MAPS[plate], name, "trt", *values])
    for plate in IMAGING_PLATES:
        for control in range(2):
            values = [
                _value(800 + control, 2, feature) for feature in range(len(IMAGING_FEATURES))
            ]
            writer.writerow(
                [plate, f"h{control:02d}", PLATE_MAPS[plate], CONTROL_NAME, "control", *values]
            )
    return gzip.compress(buffer.getvalue().encode("utf-8"), mtime=0)


@dataclass(frozen=True)
class SyntheticSnapshot:
    """The two synthetic objects and the contract that describes them."""

    transcriptome: bytes
    imaging: bytes
    contract_document: dict[str, Any]

    @property
    def payloads(self) -> dict[str, bytes]:
        return {
            "L1000/replicate_level_l1k.csv.gz": self.transcriptome,
            "CellPainting/replicate_level_cp_normalized_variable_selected.csv.gz": self.imaging,
        }


def build_snapshot() -> SyntheticSnapshot:
    """Build the synthetic objects and the contract that matches them."""
    transcriptome = _transcriptome_bytes()
    imaging = _imaging_bytes()
    host = "https://cellpainting-gallery.s3.amazonaws.com"
    prefix = "cpg0003-rosetta/broad/workspace/preprocessed_data/LUAD-BBBC041-Caicedo"
    files = []
    for key, relative_path, payload, role in (
        (
            "transcriptome_replicate",
            "L1000/replicate_level_l1k.csv.gz",
            transcriptome,
            "transcriptomic readout",
        ),
        (
            "imaging_replicate",
            "CellPainting/replicate_level_cp_normalized_variable_selected.csv.gz",
            imaging,
            "imaging readout",
        ),
    ):
        files.append(
            {
                "key": key,
                "url": f"{host}/{prefix}/{relative_path}",
                "relative_path": relative_path,
                "byte_length": len(payload),
                "s3_etag": hashlib.md5(payload).hexdigest(),
                "role": role,
            }
        )
    document = {
        "schema_version": "aidd-commons.rosetta-cross-modality-protocol.v1",
        "protocol_id": "synthetic-rosetta-cross-modality-v1",
        "issued_on": "2026-10-21",
        "declared_question": "synthetic stand-in for the contract tests",
        "data_version": {
            "study_id": "cpg0003-rosetta",
            "batch_id": "LUAD-BBBC041-Caicedo",
            "cell_line": "A549",
        },
        "source": {"host": host, "prefix": prefix, "files": files},
        "entity": {
            "unit": "one perturbation in both readouts",
            "join_key": {"transcriptome": "pert_iname", "imaging": "Metadata_pert_name"},
            "transcriptome_required_columns": [
                "id",
                "pert_iname",
                "pert_type",
                "det_plate",
                "allele",
                "pert_mfc_desc",
            ],
            "imaging_required_columns": [
                "Metadata_pert_name",
                "Metadata_Plate",
                "Metadata_Well",
                "Metadata_Plate_Map_Name",
                "pert_type",
            ],
            "transcriptome_label_columns": ["allele", "pert_mfc_desc"],
            "control_pert_type": "control",
            "profile_aggregation": "median across replicate wells",
        },
        "label_contract": {
            "transcriptome_feature_pattern": "^\\d+(?:_[a-z])?_at$",
            "imaging_feature_pattern": "^(?:Cells|Nuclei|Cytoplasm)_",
        },
        "model": {
            "penalty_grid": [1.0, 10.0, 100.0, 1000.0],
            "inner_folds": 2,
        },
        "seed": 20261021,
        "outer_folds": 3,
        "example_count": 2,
    }
    return SyntheticSnapshot(
        transcriptome=transcriptome, imaging=imaging, contract_document=document
    )


def fetcher_for(snapshot: SyntheticSnapshot):
    """A fetcher that serves the synthetic bytes without touching a network."""

    def fetch(url: str, start: int) -> FetchedChunk:
        for relative_path, payload in snapshot.payloads.items():
            if url.endswith(relative_path):
                return FetchedChunk(payload=payload[start:], start_offset=start)
        raise AssertionError(f"unexpected url {url!r}")

    return fetch


def write_contract(path: Path, document: dict[str, Any]) -> Path:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
