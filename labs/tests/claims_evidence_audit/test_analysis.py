"""Every constructed cell receives one of the four protocol states."""

from pathlib import Path

from aidd_commons.claims_evidence_audit.analysis import classify_cell

ROOT = Path(__file__).resolve().parents[3]


def test_four_states_and_missing_repository_file() -> None:
    record = {
        "evidence": [
            {"id": "present", "repository_path": "README.md"},
            {"id": "missing", "repository_path": "no-such-comparison-evidence.txt"},
        ]
    }
    direct = {"depth": "worked", "evidence": ["present"]}
    interval = {"depth": "unverified", "evidence": ["present"]}
    default = {"depth": "unverified", "evidence": []}
    unsupported = {"depth": "worked", "evidence": ["missing"]}
    assert classify_cell(record, direct, ROOT)[0] == "direct-observation"
    assert classify_cell(record, interval, ROOT)[0] == "bounded-inference"
    assert classify_cell(record, default, ROOT, is_default=True)[0] == "unresolved-field"
    assert classify_cell(record, unsupported, ROOT)[0] == "unsupported-claim"
    assert classify_cell(record, {"depth": "worked", "evidence": []}, ROOT)[0] == (
        "unsupported-claim"
    )


def test_undeclared_evidence_is_unsupported() -> None:
    record = {"evidence": [{"id": "present", "repository_path": "README.md"}]}
    state, reason = classify_cell(record, {"depth": "worked", "evidence": ["other"]}, ROOT)
    assert state == "unsupported-claim"
    assert reason == "undeclared evidence: other"
