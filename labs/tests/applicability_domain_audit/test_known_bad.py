"""Changed contracts and defective analyses cannot create a summary."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from aidd_commons.applicability_domain_audit import summary
from aidd_commons.applicability_domain_audit.analysis import AuditError, analyze, load_release
from aidd_commons.applicability_domain_audit.protocol import ProtocolError

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/applicability_domain_audit"
PROTOCOL = LAB / "protocol.json"
DATA = ROOT / ".cache/freesolv/freesolv-v0.52-database.txt"


@pytest.mark.parametrize("mutation", ["size", "seed", "distance", "baseline", "licence"])
def test_changed_protocol_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    changed = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "size":
        changed["source"]["bytes"] -= 1
    elif mutation == "seed":
        changed["split"]["seed"] += 1
    elif mutation == "distance":
        changed["distance"] = "Tanimoto"
    elif mutation == "baseline":
        changed["baseline"]["radius"] = 3
    else:
        changed["source"]["license"] = "MIT"
    original_read = Path.read_text

    def altered_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == PROTOCOL:
            return json.dumps(changed)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", altered_read)
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        summary.build_summary(PROTOCOL, DATA, output=output)
    assert not output.exists()


def test_wrong_source_length_refused_without_output(tmp_path: Path) -> None:
    bad_source = tmp_path / "short.txt"
    bad_source.write_bytes(b"short")
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError, match="byte length"):
        summary.build_summary(PROTOCOL, bad_source, output=output)
    assert not output.exists()


@pytest.mark.parametrize(
    "mutation", ["neighbour", "scaffold_overlap", "absolute_error", "cohort_median"]
)
@pytest.mark.skipif(not DATA.is_file(), reason="the FreeSolv v0.52 snapshot is not cached")
def test_defective_audit_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    result = analyze(load_release(DATA))
    if mutation == "neighbour":
        result = replace(result, nearest_indices=np.full(len(result.test), len(result.train) - 1))
    elif mutation == "scaffold_overlap":
        result = replace(result, train=(result.test[0],) + result.train[1:])
    elif mutation == "cohort_median":
        result = replace(result, cohort={**result.cohort, "measured_median_kcal_mol": 0.0})
    else:
        result = replace(result, errors=result.errors + 1)
    monkeypatch.setattr(summary, "analyze", lambda _: result)
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        summary.build_summary(PROTOCOL, DATA, output=output)
    assert not output.exists()
