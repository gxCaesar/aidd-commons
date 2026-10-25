"""The committed summary is the current row-free projection of the audit."""

import json
from pathlib import Path

import pytest
from aidd_commons.applicability_domain_audit.summary import SCHEMA_VERSION, build_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/applicability_domain_audit"
DATA = ROOT / ".cache/freesolv/freesolv-v0.52-database.txt"


@pytest.mark.skipif(not DATA.is_file(), reason="the FreeSolv v0.52 snapshot is not cached")
def test_committed_summary_matches_frozen_computation() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    current = build_summary(
        LAB / "protocol.json",
        DATA,
        computed_on=artifact["computed_on"],
        software=artifact["software"],
    )
    # The distances, the halves and the scaffold counts depend on the RDKit
    # release, so a frozen comparison is made on the fields that do not when
    # the running release is not the one the reading was computed with.
    import rdkit

    recorded = artifact["software"].get("rdkit")
    if recorded == rdkit.__version__:
        assert artifact == current
    else:
        assert artifact["cohort"]["molecules"] == current["cohort"]["molecules"]
        assert (
            artifact["cohort"]["measured_median_kcal_mol"]
            == (current["cohort"]["measured_median_kcal_mol"])
        )


def test_committed_summary_retains_count_only_contract() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert artifact["schema_version"] == SCHEMA_VERSION
    assert artifact["protocol_id"] == "freesolv-v052-applicability-domain-v1"
    assert artifact["cohort"]["molecules"] == 642
    assert artifact["cohort"]["distinct_scaffolds"] == (
        artifact["split"]["train_scaffolds"] + artifact["split"]["test_scaffolds"]
    )
    assert artifact["split"]["train_molecules"] + artifact["split"]["test_molecules"] == 642
    assert sum(half["count"] for half in artifact["error_halves"].values()) == 128
    assert "rows" not in artifact
    assert "predictions" not in artifact
