from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from shutil import copyfile

import numpy as np
import pytest
from aidd_commons.rmd17_system_state.pipeline import (
    DEVELOPMENT_DOWNLOAD_URLS,
    LOCKED_DOWNLOAD_URLS,
    LockedEvaluationError,
    PipelineContractError,
    download_development,
    evaluate_locked,
    run_pretest,
    validate_locked_result_payload,
    validate_protocol,
    write_development_summary,
)
from aidd_commons.rmd17_system_state.protocol import FROZEN_ALPHAS

REPOSITORY_ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = REPOSITORY_ROOT / "labs" / "rmd17_system_state" / "protocol.json"
DATA_RELATIVE_PATH = Path("labs/rmd17_system_state/data")
RESULTS_RELATIVE_PATH = Path("labs/rmd17_system_state/results")


def _prepare_lab_root(repository_root: Path) -> None:
    lab_dir = repository_root / "labs" / "rmd17_system_state"
    lab_dir.mkdir(parents=True)
    copyfile(PROTOCOL_PATH, lab_dir / "protocol.json")


def _install_development_inputs(repository_root: Path, source: Path) -> None:
    data_dir = repository_root / DATA_RELATIVE_PATH
    data_dir.mkdir(parents=True)
    copyfile(source, data_dir / "rmd17_ethanol.npz")
    copyfile(source, data_dir / "rmd17_malonaldehyde.npz")


def _write_locked_fixture(
    directory: Path,
    make_arrays: Callable[[int, int], dict[str, np.ndarray]],
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "locked-source.npz"
    np.savez(path, **make_arrays(100_000, 12))
    return path


def test_protocol_validation_rejects_a_changed_canonical_contract(tmp_path: Path) -> None:
    _prepare_lab_root(tmp_path)

    validated = validate_protocol(tmp_path)
    assert validated["protocol_id"] == "rmd17-system-state-v1"
    assert validated["source"]["doi"] == "10.6084/m9.figshare.12672038.v4"

    protocol_path = tmp_path / "labs" / "rmd17_system_state" / "protocol.json"
    altered = json.loads(protocol_path.read_text(encoding="utf-8"))
    altered["source"]["doi"] = "10.6084/m9.figshare.12672038.v3"
    protocol_path.write_text(json.dumps(altered), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="source"):
        validate_protocol(tmp_path)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (
            ("sampling", "rank_expression"),
            "linspace(0, n_frames - 1, 1000).astype(int64)",
        ),
        (("units", "coordinates"), "nanometre"),
        (("source", "checksum"), "forbidden-extra-field"),
        (("features", "ordinary_bins"), 99),
        (
            ("models", "selection"),
            "median validation MAE across ethanol and malonaldehyde; not larger alpha",
        ),
        (("metrics", "forbidden"), ["frame-pooled metrics"]),
        (("feature_and_target_boundaries", "allowed_feature_arrays"), ["coords"]),
    ],
    ids=(
        "rank-expression",
        "units",
        "source-extra-field",
        "features",
        "tie-break",
        "metrics",
        "boundaries",
    ),
)
def test_protocol_validation_freezes_each_public_method_section(
    tmp_path: Path,
    path: tuple[str, str],
    replacement: object,
) -> None:
    _prepare_lab_root(tmp_path)
    protocol_path = tmp_path / "labs" / "rmd17_system_state" / "protocol.json"
    payload = json.loads(protocol_path.read_text(encoding="utf-8"))
    payload[path[0]][path[1]] = replacement
    protocol_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError):
        validate_protocol(tmp_path)


def test_development_download_is_canonical_streamed_and_preserves_valid_files(
    tmp_path: Path,
    valid_ethanol_npz: Path,
) -> None:
    _prepare_lab_root(tmp_path)
    calls: list[tuple[str, Path]] = []

    def transport(url: str, temporary_path: Path) -> None:
        calls.append((url, temporary_path))
        assert temporary_path.parent == tmp_path / DATA_RELATIVE_PATH
        assert temporary_path.name.startswith(".")
        copyfile(valid_ethanol_npz, temporary_path)

    downloaded = download_development(tmp_path, transport=transport)

    assert [path.name for path in downloaded] == [
        "rmd17_ethanol.npz",
        "rmd17_malonaldehyde.npz",
    ]
    assert [url for url, _ in calls] == list(DEVELOPMENT_DOWNLOAD_URLS.values())
    assert set(DEVELOPMENT_DOWNLOAD_URLS.values()).isdisjoint(LOCKED_DOWNLOAD_URLS.values())
    assert not list((tmp_path / DATA_RELATIVE_PATH).glob(".*.partial"))

    def unexpected_transport(url: str, temporary_path: Path) -> None:
        raise AssertionError(f"valid canonical files must prevent download: {url} {temporary_path}")

    assert download_development(tmp_path, transport=unexpected_transport) == downloaded


def test_development_download_removes_invalid_temporary_file(tmp_path: Path) -> None:
    _prepare_lab_root(tmp_path)

    def broken_transport(url: str, temporary_path: Path) -> None:
        temporary_path.write_bytes(b"not an NPZ archive")

    with pytest.raises(PipelineContractError, match="downloaded ethanol"):
        download_development(tmp_path, transport=broken_transport)

    data_dir = tmp_path / DATA_RELATIVE_PATH
    assert not (data_dir / "rmd17_ethanol.npz").exists()
    assert not list(data_dir.glob(".*.partial"))


def test_development_download_removes_temporary_file_after_transport_failure(
    tmp_path: Path,
) -> None:
    _prepare_lab_root(tmp_path)

    def failing_transport(url: str, temporary_path: Path) -> None:
        temporary_path.write_bytes(b"incomplete")
        raise RuntimeError(f"interrupted transport for {url}")

    with pytest.raises(PipelineContractError, match="downloaded ethanol"):
        download_development(tmp_path, transport=failing_transport)

    assert not list((tmp_path / DATA_RELATIVE_PATH).glob(".*.partial"))


@pytest.mark.parametrize("interruption", (KeyboardInterrupt, SystemExit))
def test_development_download_cleans_partial_file_after_base_exception(
    tmp_path: Path,
    interruption: type[BaseException],
) -> None:
    _prepare_lab_root(tmp_path)

    def interrupted_transport(url: str, temporary_path: Path) -> None:
        temporary_path.write_bytes(b"partial")
        raise interruption(url)

    with pytest.raises(interruption):
        download_development(tmp_path, transport=interrupted_transport)

    assert not list((tmp_path / DATA_RELATIVE_PATH).glob(".*.partial"))


def test_pretest_writes_internal_evidence_and_a_redacted_public_summary(
    tmp_path: Path,
    valid_ethanol_npz: Path,
) -> None:
    _prepare_lab_root(tmp_path)
    _install_development_inputs(tmp_path, valid_ethanol_npz)

    artifact = run_pretest(tmp_path)
    payload = json.loads(artifact.pretest_path.read_text(encoding="utf-8"))

    assert artifact.pretest_path == tmp_path / RESULTS_RELATIVE_PATH / "pretest.json"
    assert payload["pretest_passed"] is True
    assert payload["source"]["doi"] == "10.6084/m9.figshare.12672038.v4"
    assert payload["protocol"]["split"]["selected_frames"] == 1_000
    assert payload["protocol"]["split"]["partitions"] == {
        "train": 600,
        "validation": 200,
        "evaluation": 200,
    }
    feature_layouts = payload["protocol"]["features"]["by_system"]
    for layout in feature_layouts.values():
        assert layout["feature_dimension"] == layout["channel_count"] * 101
    assert payload["selection"]["frozen_alphas"] == list(FROZEN_ALPHAS)
    assert len(payload["selection"]["grid"]) == len(FROZEN_ALPHAS)
    assert payload["locked_evaluations"] == {"benzene": "not_run", "uracil": "not_run"}
    ethanol_evaluation = payload["development"]["ethanol"]["evaluation"]
    assert len(payload["development"]["ethanol"]["fit_row_ids"]) == 600
    assert len(ethanol_evaluation["records"]) == 200
    assert set(ethanol_evaluation["records"][0]) == {
        "old_index",
        "source_position",
        "target",
        "predictions",
        "errors",
    }

    summary_path = write_development_summary(tmp_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_path == tmp_path / "labs" / "rmd17_system_state" / "development-summary.json"
    assert summary["artifact_type"] == "reviewed-development-summary"
    assert summary["locked_evaluations"] == {"benzene": "not_run", "uracil": "not_run"}
    assert summary["split"]["original_index_ordering"] == "stable ascending old_indices"
    assert set(summary["development_evaluation"]) == {"ethanol", "malonaldehyde"}


def test_pretest_keeps_feature_layouts_separate_for_different_system_compositions(
    tmp_path: Path,
    valid_ethanol_npz: Path,
    make_arrays: Callable[[int, int], dict[str, np.ndarray]],
) -> None:
    _prepare_lab_root(tmp_path)
    data_dir = tmp_path / DATA_RELATIVE_PATH
    data_dir.mkdir(parents=True)
    copyfile(valid_ethanol_npz, data_dir / "rmd17_ethanol.npz")
    malonaldehyde = make_arrays(100_000, 9)
    malonaldehyde["nuclear_charges"] = np.array(
        [6, 6, 6, 8, 8, 1, 1, 1, 1], dtype=np.int64
    )
    np.savez(data_dir / "rmd17_malonaldehyde.npz", **malonaldehyde)

    artifact = run_pretest(tmp_path)
    payload = json.loads(artifact.pretest_path.read_text(encoding="utf-8"))
    by_system = payload["protocol"]["features"]["by_system"]

    assert by_system["ethanol"] == {
        "element_pair_channels": ["Z1-Z1", "Z1-Z6", "Z1-Z8", "Z6-Z6", "Z6-Z8"],
        "channel_count": 5,
        "feature_dimension": 505,
    }
    assert by_system["malonaldehyde"] == {
        "element_pair_channels": [
            "Z1-Z1",
            "Z1-Z6",
            "Z1-Z8",
            "Z6-Z6",
            "Z6-Z8",
            "Z8-Z8",
        ],
        "channel_count": 6,
        "feature_dimension": 606,
    }


def test_locked_path_claims_before_transport_and_requires_paired_sections(
    tmp_path: Path,
    valid_ethanol_npz: Path,
    make_arrays: Callable[[int, int], dict[str, np.ndarray]],
) -> None:
    _prepare_lab_root(tmp_path)
    _install_development_inputs(tmp_path, valid_ethanol_npz)
    run_pretest(tmp_path)
    locked_source = _write_locked_fixture(tmp_path / "fixtures", make_arrays)
    marker_path = tmp_path / RESULTS_RELATIVE_PATH / "locked-evaluation.started.json"
    calls: list[str] = []

    def locked_transport(url: str, temporary_path: Path) -> None:
        assert marker_path.exists(), "the exclusive marker must precede the first locked download"
        calls.append(url)
        copyfile(locked_source, temporary_path)

    metrics_path = evaluate_locked(tmp_path, confirmed=True, transport=locked_transport)
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert calls == list(LOCKED_DOWNLOAD_URLS.values())
    assert set(payload["results"]) == {"benzene", "uracil"}
    assert payload["selected_alpha"] in FROZEN_ALPHAS

    with pytest.raises(LockedEvaluationError, match="both benzene and uracil"):
        validate_locked_result_payload({"results": {"benzene": {}}})

    with pytest.raises(LockedEvaluationError, match="already been claimed"):
        evaluate_locked(tmp_path, confirmed=True, transport=locked_transport)

    marker_path.unlink()
    with pytest.raises(LockedEvaluationError, match="output already exists"):
        evaluate_locked(tmp_path, confirmed=True, transport=locked_transport)


def test_locked_path_rejects_tampered_pretest_before_marker_or_transport(
    tmp_path: Path,
    valid_ethanol_npz: Path,
) -> None:
    _prepare_lab_root(tmp_path)
    _install_development_inputs(tmp_path, valid_ethanol_npz)
    pretest_path = run_pretest(tmp_path).pretest_path
    payload = json.loads(pretest_path.read_text(encoding="utf-8"))
    original_alpha = payload["selection"]["selected_alpha"]
    payload["selection"]["selected_alpha"] = next(
        alpha for alpha in FROZEN_ALPHAS if alpha != original_alpha
    )
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")
    marker_path = tmp_path / RESULTS_RELATIVE_PATH / "locked-evaluation.started.json"
    calls: list[str] = []

    def transport(url: str, temporary_path: Path) -> None:
        calls.append(url)
        temporary_path.write_bytes(b"must not download after pretest tampering")

    with pytest.raises(LockedEvaluationError, match="recomputed development evidence"):
        evaluate_locked(tmp_path, confirmed=True, transport=transport)

    assert calls == []
    assert not marker_path.exists()


def test_locked_path_requires_existing_pretest_before_marker_or_transport(tmp_path: Path) -> None:
    _prepare_lab_root(tmp_path)
    calls: list[str] = []

    def transport(url: str, temporary_path: Path) -> None:
        calls.append(url)
        temporary_path.write_bytes(b"must not download without a pretest")

    with pytest.raises(LockedEvaluationError, match="development pretest artifact"):
        evaluate_locked(tmp_path, confirmed=True, transport=transport)

    assert calls == []
    assert not (tmp_path / RESULTS_RELATIVE_PATH / "locked-evaluation.started.json").exists()


def test_locked_path_rejects_pretest_after_current_development_data_changes(
    tmp_path: Path,
    valid_ethanol_npz: Path,
) -> None:
    _prepare_lab_root(tmp_path)
    _install_development_inputs(tmp_path, valid_ethanol_npz)
    run_pretest(tmp_path)
    ethanol_path = tmp_path / DATA_RELATIVE_PATH / "rmd17_ethanol.npz"
    with np.load(ethanol_path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    arrays["energies"] = arrays["energies"].copy()
    arrays["energies"][0] += 1.0
    np.savez(ethanol_path, **arrays)
    calls: list[str] = []

    def transport(url: str, temporary_path: Path) -> None:
        calls.append(url)
        temporary_path.write_bytes(b"must not download after development data changes")

    with pytest.raises(LockedEvaluationError, match="recomputed development evidence"):
        evaluate_locked(tmp_path, confirmed=True, transport=transport)

    assert calls == []
    assert not (tmp_path / RESULTS_RELATIVE_PATH / "locked-evaluation.started.json").exists()


def test_locked_path_keeps_marker_without_metrics_when_second_system_fails(
    tmp_path: Path,
    valid_ethanol_npz: Path,
    make_arrays: Callable[[int, int], dict[str, np.ndarray]],
) -> None:
    _prepare_lab_root(tmp_path)
    _install_development_inputs(tmp_path, valid_ethanol_npz)
    run_pretest(tmp_path)
    locked_source = _write_locked_fixture(tmp_path / "fixtures", make_arrays)
    calls: list[str] = []

    def fail_on_uracil(url: str, temporary_path: Path) -> None:
        calls.append(url)
        if len(calls) == 1:
            copyfile(locked_source, temporary_path)
            return
        raise RuntimeError("synthetic uracil transport failure")

    with pytest.raises(PipelineContractError, match="downloaded uracil"):
        evaluate_locked(tmp_path, confirmed=True, transport=fail_on_uracil)

    results_dir = tmp_path / RESULTS_RELATIVE_PATH
    assert calls == list(LOCKED_DOWNLOAD_URLS.values())
    assert (results_dir / "locked-evaluation.started.json").exists()
    assert not (results_dir / "locked-metrics.json").exists()
