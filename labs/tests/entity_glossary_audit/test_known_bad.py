"""Defective contracts and admitted rows cannot create a summary."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from aidd_commons.decision_unit_scope.data import load_cached_cohort
from aidd_commons.entity_glossary_audit import summary
from aidd_commons.entity_glossary_audit.analysis import AuditError, admitted_rows
from aidd_commons.entity_glossary_audit.protocol import ProtocolError

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/entity_glossary_audit"
CACHE = ROOT / ".cache/decision_unit_scope"


@pytest.mark.parametrize("mutation", ["cohort", "endpoint", "kind", "missing_kind", "artifact"])
def test_changed_protocol_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    changed = copy.deepcopy(json.loads((LAB / "protocol.json").read_text(encoding="utf-8")))
    if mutation == "cohort":
        changed["cohort"]["seeds"].pop()
    elif mutation == "endpoint":
        changed["endpoint"]["point_relation"] = ">"
    elif mutation == "kind":
        changed["named_kinds"].pop("target")
    elif mutation == "missing_kind":
        changed["unnamed_kinds"].pop("patient")
    else:
        changed["artifacts"][0]["byte_length"] += 1
    original_read = Path.read_text

    def changed_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == LAB / "protocol.json":
            return json.dumps(changed)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", changed_read)
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        summary.build_summary(LAB, CACHE, output=output)
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["missing_target", "duplicate_id", "wrong_parent", "bound"])
@pytest.mark.skipif(not CACHE.is_dir(), reason="the decision-unit ChEMBL snapshot is not cached")
def test_bad_row_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    rows = list(admitted_rows(load_cached_cohort(CACHE)))
    if mutation == "missing_target":
        rows[0] = replace(rows[0], target_chembl_id=None)
    elif mutation == "duplicate_id":
        rows[1] = replace(rows[1], activity_id=rows[0].activity_id)
    elif mutation == "wrong_parent":
        rows[0] = replace(rows[0], parent_molecule_chembl_id="CHEMBL999")
    else:
        rows[0] = replace(rows[0], standard_relation=">")
    monkeypatch.setattr(summary, "admitted_rows", lambda _: tuple(rows))
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        summary.build_summary(LAB, CACHE, output=output)
    assert not output.exists()
