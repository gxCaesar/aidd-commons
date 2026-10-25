from __future__ import annotations

import csv
import gzip
import io
from pathlib import Path

import h5py
import numpy as np
import pytest
from aidd_commons.l1000_perturbation_context.protocol import FILES

INST_FIELDS = [
    "inst_id",
    "cell_id",
    "det_plate",
    "det_well",
    "pert_mfc_id",
    "pert_dose",
    "pert_dose_unit",
    "pert_id",
    "pert_iname",
    "pert_type",
    "pert_time",
    "pert_time_unit",
]

PERT_FIELDS = ["pert_id", "canonical_smiles", "inchi_key", "pert_iname", "pert_type"]

BENZENE = "c1ccccc1"


def _write_gz_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    path.write_bytes(gzip.compress(buffer.getvalue().encode("utf-8")))


def _write_gctx(path: Path, col_ids: list[str], row_ids: list[str], matrix: np.ndarray) -> None:
    with h5py.File(path, "w") as h5:
        h5.create_dataset("0/META/COL/id", data=[c.encode("utf-8") for c in col_ids])
        h5.create_dataset("0/META/ROW/id", data=[r.encode("utf-8") for r in row_ids])
        h5.create_dataset("0/DATA/0/matrix", data=matrix.astype(np.float32))
    compressed = gzip.compress(path.read_bytes())
    (path.parent / (path.name + ".gz")).write_bytes(compressed)
    path.unlink()


@pytest.fixture
def synthetic_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A small, fully consistent synthetic GSE70138-shaped cache: two cell
    lines, two plates, a handful of compounds exercising every exclusion
    reason, and a tiny real GCTX file with three genes."""
    cache_dir = tmp_path / "l1000-cache"
    cache_dir.mkdir()

    inst_rows = [
        # MCF7, plate P1: two vehicle wells
        dict(
            inst_id="P1:V1",
            cell_id="MCF7",
            det_plate="P1",
            det_well="V1",
            pert_mfc_id="DMSO",
            pert_dose="-666",
            pert_dose_unit="-666",
            pert_id="DMSO",
            pert_iname="DMSO",
            pert_type="ctl_vehicle",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        dict(
            inst_id="P1:V2",
            cell_id="MCF7",
            det_plate="P1",
            det_well="V2",
            pert_mfc_id="DMSO",
            pert_dose="-666",
            pert_dose_unit="-666",
            pert_id="DMSO",
            pert_iname="DMSO",
            pert_type="ctl_vehicle",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # MCF7, plate P1: CMPD1 at the fixed condition, two replicates
        dict(
            inst_id="P1:A1",
            cell_id="MCF7",
            det_plate="P1",
            det_well="A1",
            pert_mfc_id="CMPD1",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD1",
            pert_iname="compound-one",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        dict(
            inst_id="P1:A2",
            cell_id="MCF7",
            det_plate="P1",
            det_well="A2",
            pert_mfc_id="CMPD1",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD1",
            pert_iname="compound-one",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # MCF7, plate P1: CMPD4 shared compound
        dict(
            inst_id="P1:A3",
            cell_id="MCF7",
            det_plate="P1",
            det_well="A3",
            pert_mfc_id="CMPD4",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD4",
            pert_iname="compound-four",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # MCF7, plate P1: CMPD2 at the wrong dose
        dict(
            inst_id="P1:A4",
            cell_id="MCF7",
            det_plate="P1",
            det_well="A4",
            pert_mfc_id="CMPD2",
            pert_dose="1.0",
            pert_dose_unit="um",
            pert_id="CMPD2",
            pert_iname="compound-two",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # MCF7, plate P1: CMPD2 at the wrong time
        dict(
            inst_id="P1:A5",
            cell_id="MCF7",
            det_plate="P1",
            det_well="A5",
            pert_mfc_id="CMPD2",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD2",
            pert_iname="compound-two",
            pert_type="trt_cp",
            pert_time="48.0",
            pert_time_unit="h",
        ),
        # MCF7, plate P2 (no vehicle control on this plate): CMPD5
        dict(
            inst_id="P2:A1",
            cell_id="MCF7",
            det_plate="P2",
            det_well="A1",
            pert_mfc_id="CMPD5",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD5",
            pert_iname="compound-five",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # PC3, plate Q1: two vehicle wells
        dict(
            inst_id="Q1:V1",
            cell_id="PC3",
            det_plate="Q1",
            det_well="V1",
            pert_mfc_id="DMSO",
            pert_dose="-666",
            pert_dose_unit="-666",
            pert_id="DMSO",
            pert_iname="DMSO",
            pert_type="ctl_vehicle",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        dict(
            inst_id="Q1:V2",
            cell_id="PC3",
            det_plate="Q1",
            det_well="V2",
            pert_mfc_id="DMSO",
            pert_dose="-666",
            pert_dose_unit="-666",
            pert_id="DMSO",
            pert_iname="DMSO",
            pert_type="ctl_vehicle",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # PC3, plate Q1: CMPD1 (shared with MCF7)
        dict(
            inst_id="Q1:A1",
            cell_id="PC3",
            det_plate="Q1",
            det_well="A1",
            pert_mfc_id="CMPD1",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD1",
            pert_iname="compound-one",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # PC3, plate Q1: CMPD4 (shared with MCF7)
        dict(
            inst_id="Q1:A2",
            cell_id="PC3",
            det_plate="Q1",
            det_well="A2",
            pert_mfc_id="CMPD4",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD4",
            pert_iname="compound-four",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
        # PC3, plate Q1: CMPD3 has an invalid/restricted structure
        dict(
            inst_id="Q1:A3",
            cell_id="PC3",
            det_plate="Q1",
            det_well="A3",
            pert_mfc_id="CMPD3",
            pert_dose="10.0",
            pert_dose_unit="um",
            pert_id="CMPD3",
            pert_iname="compound-three",
            pert_type="trt_cp",
            pert_time="24.0",
            pert_time_unit="h",
        ),
    ]
    pert_rows = [
        dict(
            pert_id="CMPD1",
            canonical_smiles=BENZENE,
            inchi_key="XXX1",
            pert_iname="compound-one",
            pert_type="trt_cp",
        ),
        dict(
            pert_id="CMPD2",
            canonical_smiles=BENZENE,
            inchi_key="XXX2",
            pert_iname="compound-two",
            pert_type="trt_cp",
        ),
        dict(
            pert_id="CMPD3",
            canonical_smiles="restricted",
            inchi_key="-666",
            pert_iname="compound-three",
            pert_type="trt_cp",
        ),
        dict(
            pert_id="CMPD4",
            canonical_smiles=BENZENE,
            inchi_key="XXX4",
            pert_iname="compound-four",
            pert_type="trt_cp",
        ),
        dict(
            pert_id="CMPD5",
            canonical_smiles=BENZENE,
            inchi_key="XXX5",
            pert_iname="compound-five",
            pert_type="trt_cp",
        ),
        dict(
            pert_id="DMSO",
            canonical_smiles="-666",
            inchi_key="-666",
            pert_iname="DMSO",
            pert_type="ctl_vehicle",
        ),
    ]

    inst_filename, _ = FILES["inst_info"]
    pert_filename, _ = FILES["pert_info"]
    cell_filename, _ = FILES["cell_info"]
    gene_filename, _ = FILES["gene_info"]
    gctx_filename, _ = FILES["level2_gctx"]

    _write_gz_tsv(cache_dir / inst_filename, INST_FIELDS, inst_rows)
    _write_gz_tsv(cache_dir / pert_filename, PERT_FIELDS, pert_rows)
    _write_gz_tsv(cache_dir / cell_filename, ["cell_id"], [{"cell_id": "MCF7"}, {"cell_id": "PC3"}])
    _write_gz_tsv(
        cache_dir / gene_filename,
        ["pr_gene_id", "pr_is_lm"],
        [{"pr_gene_id": "1", "pr_is_lm": "1"}],
    )

    col_ids = [row["inst_id"] for row in inst_rows]
    row_ids = ["100", "200", "300"]
    rng = np.random.default_rng(0)
    matrix = rng.normal(loc=5.0, scale=1.0, size=(len(col_ids), len(row_ids)))
    # give vehicle wells a tight, near-identical baseline so the differential
    # is dominated by the deliberate per-compound offsets added below
    vehicle_positions = [i for i, r in enumerate(inst_rows) if r["pert_type"] == "ctl_vehicle"]
    for i in vehicle_positions:
        matrix[i, :] = [5.0, 5.0, 5.0]
    offsets = {
        "CMPD1": np.array([1.0, 0.5, -0.5]),
        "CMPD2": np.array([2.0, -1.0, 0.0]),
        "CMPD3": np.array([0.3, 0.3, 0.3]),
        "CMPD4": np.array([-1.0, 1.0, 2.0]),
        "CMPD5": np.array([0.7, 0.7, 0.7]),
    }
    for i, row in enumerate(inst_rows):
        if row["pert_type"] == "trt_cp":
            matrix[i, :] = 5.0 + offsets[row["pert_id"]]

    _write_gctx(cache_dir / gctx_filename.removesuffix(".gz"), col_ids, row_ids, matrix)

    monkeypatch.setattr(
        "aidd_commons.l1000_perturbation_context.protocol.FILES",
        {
            "inst_info": (inst_filename, (cache_dir / inst_filename).stat().st_size),
            "cell_info": (cell_filename, (cache_dir / cell_filename).stat().st_size),
            "gene_info": (gene_filename, (cache_dir / gene_filename).stat().st_size),
            "pert_info": (pert_filename, (cache_dir / pert_filename).stat().st_size),
            "level2_gctx": (gctx_filename, (cache_dir / gctx_filename).stat().st_size),
        },
    )
    monkeypatch.setattr(
        "aidd_commons.l1000_perturbation_context.data.FILES",
        {
            "inst_info": (inst_filename, (cache_dir / inst_filename).stat().st_size),
            "cell_info": (cell_filename, (cache_dir / cell_filename).stat().st_size),
            "gene_info": (gene_filename, (cache_dir / gene_filename).stat().st_size),
            "pert_info": (pert_filename, (cache_dir / pert_filename).stat().st_size),
            "level2_gctx": (gctx_filename, (cache_dir / gctx_filename).stat().st_size),
        },
    )
    return cache_dir
