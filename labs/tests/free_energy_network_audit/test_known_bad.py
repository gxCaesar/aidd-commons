"""Known defects must fail before a summary can be written."""

from __future__ import annotations

import bz2
import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.free_energy_network_audit.analysis import (
    BindingEdge,
    DataContractError,
    cycle_basis,
    parse_archive,
)
from aidd_commons.free_energy_network_audit.protocol import SOURCE_FILES, source_filename
from aidd_commons.free_energy_network_audit.summary import export_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/free_energy_network_audit"
CACHE = ROOT / ".cache/free_energy_network_audit"


def _edited_payload(edit: str) -> bytes:
    system, key, _ = SOURCE_FILES[0]
    pairs = json.loads(bz2.decompress((CACHE / source_filename(system, key)).read_bytes()))
    objects: dict[str, dict[str, Any]] = dict(pairs)
    archive = next(
        value for name, value in objects.items() if name.startswith("AlchemicalArchive-")
    )
    network = next(
        value for name, value in objects.items() if name.startswith("AlchemicalNetwork-")
    )
    transformation = next(
        value for name, value in objects.items() if name.startswith("Transformation-")
    )
    unit = next(value for name, value in objects.items() if name.startswith("ProtocolUnitResult-"))
    if edit == "missing_edge":
        network["edges"].pop()
    elif edit == "bad_mapping":
        transformation["mapping"] = {":gufe-key:": "LigandAtomMapping-missing"}
    elif edit == "bad_uncertainty":
        unit["outputs"]["unit_estimate_error"]["magnitude"] = -1
    elif edit == "duplicate_repeat":
        _, dag_refs = archive["transformation_results"][0]
        first = objects[dag_refs[0][":gufe-key:"]]
        second = objects[dag_refs[1][":gufe-key:"]]
        first_unit = objects[first["protocol_unit_results"][0][":gufe-key:"]]
        second_unit = objects[second["protocol_unit_results"][0][":gufe-key:"]]
        second_unit["outputs"]["repeat_id"] = first_unit["outputs"]["repeat_id"]
    else:
        raise AssertionError(edit)
    return bz2.compress(json.dumps(pairs).encode("utf-8"))


@pytest.mark.parametrize(
    "edit", ["missing_edge", "bad_mapping", "bad_uncertainty", "duplicate_repeat"]
)
@pytest.mark.skipif(not CACHE.is_dir(), reason="the free-energy source archives are not cached")
def test_refused_archive_leaves_no_summary(edit: str, tmp_path: Path) -> None:
    payload = _edited_payload(edit)
    with pytest.raises(DataContractError):
        parse_archive(payload)
    lab = tmp_path / "lab"
    cache = tmp_path / "cache"
    lab.mkdir()
    cache.mkdir()
    (lab / "protocol.json").write_bytes((LAB / "protocol.json").read_bytes())
    system, key, _ = SOURCE_FILES[0]
    (cache / source_filename(system, key)).write_bytes(payload)
    output = tmp_path / "summary.json"
    with pytest.raises(DataContractError):
        export_summary(lab, cache, output)
    assert not output.exists()


def test_refused_protocol_leaves_no_summary(tmp_path: Path) -> None:
    lab = tmp_path / "lab"
    lab.mkdir()
    protocol = json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))
    protocol["cycle_rule"]["closure"] = "Count every cycle as closed."
    (lab / "protocol.json").write_text(json.dumps(protocol), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ValueError, match="frozen contract"):
        export_summary(lab, tmp_path / "cache", output)
    assert not output.exists()


def test_known_inconsistent_cycle_is_failed_and_retained() -> None:
    edges = (
        BindingEdge("A_B", "a", "b", "A", "B", 1.0, 0.1),
        BindingEdge("B_C", "b", "c", "B", "C", 1.0, 0.1),
        BindingEdge("C_A", "c", "a", "C", "A", -1.0, 0.1),
    )
    cycles = cycle_basis(edges)
    assert len(cycles) == 1
    assert sum(cycle["closed"] for cycle in cycles) == 0
    assert cycles[0]["name"] == "C -> A -> B -> C"
    assert cycles[0]["discrepancy_size_kcal_mol"] == 1.0
