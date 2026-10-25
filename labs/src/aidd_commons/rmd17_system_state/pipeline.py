from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypeAlias, cast
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np
import sklearn  # type: ignore[import-untyped]

from .data import DataContractError, RMD17SystemData, load_system_npz
from .evaluation import EnergyMetrics, aggregate_system_maes, energy_metrics
from .features import PairDistanceFeatures, build_pair_distance_features
from .models import (
    FittedSystemRidge,
    ModelContractError,
    SharedAlphaSelection,
    SystemDevelopmentData,
    fit_system_ridge,
    predict_system_ridge,
    select_alpha_from_scores,
    select_shared_alpha,
    train_mean_predictions,
)
from .protocol import (
    DEVELOPMENT_SYSTEM_IDS,
    DISTANCE_BIN_WIDTH,
    EVALUATION_FRAME_COUNT,
    EXPECTED_FRAME_COUNT,
    FIGSHARE_ARTICLE_ID,
    FIGSHARE_DOI,
    FROZEN_ALPHAS,
    LICENCE,
    LOCKED_SYSTEM_IDS,
    PRIMARY_PAPER_DOI,
    PROTOCOL_ID,
    REQUIRED_NPZ_KEYS,
    SAMPLED_FRAME_COUNT,
    SYSTEMS,
    TRAIN_FRAME_COUNT,
    VALIDATION_FRAME_COUNT,
    SystemSpec,
)
from .splits import FramePartition, SystemSplit, partition_system

DATA_RELATIVE_PATH = Path("labs/rmd17_system_state/data")
RESULTS_RELATIVE_PATH = Path("labs/rmd17_system_state/results")
SUMMARY_RELATIVE_PATH = Path("labs/rmd17_system_state/development-summary.json")
PROTOCOL_RELATIVE_PATH = Path("labs/rmd17_system_state/protocol.json")
PRETEST_FILE_NAME = "pretest.json"
LOCKED_MARKER_FILE_NAME = "locked-evaluation.started.json"
LOCKED_METRICS_FILE_NAME = "locked-metrics.json"
REVIEWED_ON = "2026-09-05"

DEVELOPMENT_DOWNLOAD_URLS = {
    "ethanol": "https://ndownloader.figshare.com/files/62265733",
    "malonaldehyde": "https://ndownloader.figshare.com/files/62265736",
}
LOCKED_DOWNLOAD_URLS = {
    "benzene": "https://ndownloader.figshare.com/files/62265739",
    "uracil": "https://ndownloader.figshare.com/files/62265745",
}
LOCKED_COMMAND_TOKENS = (
    "uv",
    "run",
    "python",
    "labs/rmd17_system_state/run_lab.py",
    "evaluate-locked",
    "--confirm-run-locked-evaluation",
)

JsonValue: TypeAlias = object
DownloadTransport: TypeAlias = Callable[[str, Path], None]


class PipelineContractError(ValueError):
    """Raised when the canonical pipeline or its development evidence is invalid."""


class LockedEvaluationError(ValueError):
    """Raised when the one-time paired locked evaluation boundary is violated."""


class PublicSummaryError(ValueError):
    """Raised when a public summary contains internal evidence."""


@dataclass(frozen=True)
class LabPaths:
    repository_root: Path
    data_dir: Path
    results_dir: Path
    protocol_path: Path
    pretest_path: Path
    locked_marker_path: Path
    locked_metrics_path: Path
    summary_path: Path


@dataclass(frozen=True)
class PretestArtifact:
    pretest_path: Path


@dataclass(frozen=True)
class _PreparedSystem:
    system_id: str
    split: SystemSplit
    train_features: PairDistanceFeatures
    validation_features: PairDistanceFeatures
    evaluation_features: PairDistanceFeatures
    train_row_ids: tuple[str, ...]


_PUBLIC_FORBIDDEN_KEYS = frozenset(
    "".join(character for character in key.lower() if character.isalnum())
    for key in {
        "coordinates",
        "coords",
        "nuclear_charges",
        "charges",
        "energies",
        "forces",
        "old_indices",
        "old_index",
        "source_positions",
        "source_position",
        "frame_ids",
        "frame_id",
        "membership",
        "split_membership",
        "records",
        "fit_row_ids",
        "row_ids",
        "target",
        "predictions",
        "prediction",
        "errors",
        "error",
        "scaler",
        "scaler_vectors",
        "scaler_mean",
        "scaler_scale",
        "coefficient",
        "coefficients",
        "ridge_coefficients",
        "data_path",
        "lock_path",
        "command",
        "evaluation_command",
        "planned_locked_evaluation_command",
        "receipt",
    }
)
_PUBLIC_FORBIDDEN_PATH_SEGMENTS = (
    "labs/rmd17_system_state/data",
    "labs/rmd17_system_state/results",
)


def canonical_paths(repository_root: Path) -> LabPaths:
    root = repository_root.resolve()
    results_dir = root / RESULTS_RELATIVE_PATH
    return LabPaths(
        repository_root=root,
        data_dir=root / DATA_RELATIVE_PATH,
        results_dir=results_dir,
        protocol_path=root / PROTOCOL_RELATIVE_PATH,
        pretest_path=results_dir / PRETEST_FILE_NAME,
        locked_marker_path=results_dir / LOCKED_MARKER_FILE_NAME,
        locked_metrics_path=results_dir / LOCKED_METRICS_FILE_NAME,
        summary_path=root / SUMMARY_RELATIVE_PATH,
    )


def portable_locked_evaluation_command() -> str:
    """Return the only repository-relative command planned for locked evaluation."""

    return shlex.join(LOCKED_COMMAND_TOKENS)


def validate_protocol(repository_root: Path) -> dict[str, JsonValue]:
    """Validate that the checked-in JSON protocol still matches the frozen Python contract."""

    paths = canonical_paths(repository_root)
    payload = _read_json(paths.protocol_path, PipelineContractError)
    if set(payload) != {
        "protocol_id",
        "source",
        "systems",
        "required_npz_keys",
        "units",
        "sampling",
        "features",
        "models",
        "metrics",
        "feature_and_target_boundaries",
    }:
        raise PipelineContractError("protocol top-level fields differ from the frozen contract")
    if payload.get("protocol_id") != PROTOCOL_ID:
        raise PipelineContractError("protocol_id differs from the frozen rMD17 protocol")

    source = _mapping(payload.get("source"), "protocol source must be an object")
    expected_source: dict[str, object] = {
        "figshare_article": FIGSHARE_ARTICLE_ID,
        "doi": FIGSHARE_DOI,
        "version": 4,
        "licence": LICENCE,
        "primary_paper_doi": PRIMARY_PAPER_DOI,
    }
    if dict(source) != expected_source:
        raise PipelineContractError("protocol source differs from the frozen contract")

    systems = _list(payload.get("systems"), "protocol systems must be a list")
    expected_systems = (
        ("ethanol", "development"),
        ("malonaldehyde", "development"),
        ("benzene", "locked"),
        ("uracil", "locked"),
    )
    if len(systems) != len(expected_systems):
        raise PipelineContractError("protocol systems differ from the four frozen systems")
    for observed, (system_id, role) in zip(systems, expected_systems, strict=True):
        system = _mapping(observed, "each protocol system must be an object")
        specification = SYSTEMS[system_id]
        expected_system: dict[str, object] = {
            "system_id": system_id,
            "filename": specification.filename,
            "file_id": specification.file_id,
            "role": role,
            "expected_frames": EXPECTED_FRAME_COUNT,
            "expected_atoms": specification.expected_atoms,
        }
        if dict(system) != expected_system:
            raise PipelineContractError(f"protocol {system_id} differs from the frozen contract")

    if payload.get("required_npz_keys") != list(REQUIRED_NPZ_KEYS):
        raise PipelineContractError("protocol required NPZ keys differ from the frozen contract")
    _validate_protocol_sampling(payload)
    _validate_protocol_models(payload)
    _validate_protocol_method_sections(payload)
    return payload


def download_development(
    repository_root: Path,
    *,
    transport: DownloadTransport | None = None,
) -> tuple[Path, ...]:
    """Fetch only the two development NPZ files into their canonical locations."""

    validate_protocol(repository_root)
    paths = canonical_paths(repository_root)
    downloader = transport if transport is not None else _stream_download
    return tuple(
        _download_and_validate(
            paths, SYSTEMS[system_id], DEVELOPMENT_DOWNLOAD_URLS[system_id], downloader
        )
        for system_id in DEVELOPMENT_SYSTEM_IDS
    )


def run_pretest(repository_root: Path) -> PretestArtifact:
    """Fit development-only baselines and write auditable internal evidence."""

    protocol_payload = validate_protocol(repository_root)
    paths = canonical_paths(repository_root)
    _refuse_after_locked_evaluation(paths, PipelineContractError)
    payload = _current_pretest_payload(paths, protocol_payload)

    paths.results_dir.mkdir(parents=True, exist_ok=True)
    if paths.pretest_path.exists():
        existing = _read_json(paths.pretest_path, PipelineContractError)
        if existing != payload:
            raise PipelineContractError(
                "existing pretest artifact differs from the current frozen development evidence"
            )
    else:
        _write_json(paths.pretest_path, payload)
    return PretestArtifact(pretest_path=paths.pretest_path)


def _current_pretest_payload(
    paths: LabPaths,
    protocol_payload: Mapping[str, object],
) -> dict[str, JsonValue]:
    prepared = tuple(
        _prepare_system(_load_canonical_system(paths, SYSTEMS[system_id]))
        for system_id in DEVELOPMENT_SYSTEM_IDS
    )
    _validate_development_system_order(prepared)
    selection, grid = _shared_alpha_evidence(prepared)
    payload = _pretest_payload(
        protocol_payload, prepared, selection.models, grid, selection.selected_alpha
    )
    return payload


def evaluate_locked(
    repository_root: Path,
    *,
    confirmed: bool,
    transport: DownloadTransport | None = None,
) -> Path:
    """Run the paired benzene/uracil evaluation once after explicit confirmation."""

    if not confirmed:
        raise LockedEvaluationError("locked evaluation requires explicit confirmation")
    protocol_payload = validate_protocol(repository_root)
    paths = canonical_paths(repository_root)
    _refuse_after_locked_evaluation(paths, LockedEvaluationError)
    pretest = _read_pretest_for_locked_evaluation(paths.pretest_path)
    expected_pretest = _current_pretest_payload(paths, protocol_payload)
    if pretest != expected_pretest:
        raise LockedEvaluationError("pretest differs from recomputed development evidence")
    selected_alpha = _selected_alpha(pretest)
    _claim_locked_evaluation(paths)

    downloader = transport if transport is not None else _stream_download
    prepared = tuple(
        _prepare_system(
            _load_or_download_locked_system(
                paths,
                SYSTEMS[system_id],
                LOCKED_DOWNLOAD_URLS[system_id],
                downloader,
            )
        )
        for system_id in LOCKED_SYSTEM_IDS
    )
    payload = _locked_metrics_payload(prepared, selected_alpha)
    validate_locked_result_payload(payload)
    _write_json(paths.locked_metrics_path, payload)
    return paths.locked_metrics_path


def validate_locked_result_payload(payload: Mapping[str, object]) -> None:
    """Reject any locked result that does not contain both required systems."""

    results = _mapping(payload.get("results"), "locked evaluation results must be an object")
    missing = set(LOCKED_SYSTEM_IDS).difference(results)
    if missing or set(results).difference(LOCKED_SYSTEM_IDS):
        raise LockedEvaluationError("both benzene and uracil result sections are required")


def development_summary(pretest_path: Path) -> dict[str, JsonValue]:
    """Project internal development evidence into a public aggregate-only summary."""

    pretest = _read_json(pretest_path, PipelineContractError)
    if pretest.get("pretest_passed") is not True:
        raise PipelineContractError("cannot summarize a pretest artifact that did not pass")
    if pretest.get("protocol_id") != PROTOCOL_ID:
        raise PipelineContractError("pretest artifact uses the wrong protocol")

    source = _mapping(pretest.get("source"), "pretest source evidence is missing")
    protocol = _mapping(pretest.get("protocol"), "pretest protocol evidence is missing")
    selection = _mapping(pretest.get("selection"), "pretest selection evidence is missing")
    development = _mapping(pretest.get("development"), "pretest development evidence is missing")
    locked = _mapping(pretest.get("locked_evaluations"), "pretest lock states are missing")
    if {system_id: locked.get(system_id) for system_id in LOCKED_SYSTEM_IDS} != {
        "benzene": "not_run",
        "uracil": "not_run",
    }:
        raise PipelineContractError(
            "public development summary requires both locked systems to be not_run"
        )

    split = _mapping(protocol.get("split"), "pretest split evidence is missing")
    features = _public_feature_summary(
        _mapping(protocol.get("features"), "pretest feature evidence is missing")
    )
    frozen_alphas = selection.get("frozen_alphas")
    public_grid = _public_validation_grid(selection.get("grid"))
    if frozen_alphas != list(FROZEN_ALPHAS) or [
        entry["alpha"] for entry in public_grid
    ] != list(FROZEN_ALPHAS):
        raise PipelineContractError("pretest must retain the complete frozen shared-alpha grid")
    if selection.get("selected_alpha") not in FROZEN_ALPHAS:
        raise PipelineContractError("pretest selected alpha is outside the frozen grid")
    try:
        selected_alpha = select_alpha_from_scores(
            {
                _finite_number(entry["alpha"], "pretest validation alpha must be numeric"):
                _finite_number(
                    entry["median_validation_mae"],
                    "pretest median validation MAE must be numeric",
                )
                for entry in public_grid
            }
        )
    except ModelContractError as error:
        raise PipelineContractError(
            "pretest validation grid is not a frozen selection grid"
        ) from error
    persisted_alpha = _finite_number(
        selection.get("selected_alpha"), "pretest selected alpha must be numeric"
    )
    if persisted_alpha != selected_alpha:
        raise PipelineContractError("persisted selected alpha differs from the frozen grid rule")
    per_system_metrics = {
        system_id: _evaluation_metrics_for_public(development, system_id)
        for system_id in DEVELOPMENT_SYSTEM_IDS
    }
    ordering_diagnostics = _public_ordering_diagnostics_by_system(development)
    aggregate_payload = {
        model_name: asdict(
            aggregate_system_maes(
                {
                    system_id: _metric_mae(metrics[model_name])
                    for system_id, metrics in per_system_metrics.items()
                }
            )
        )
        for model_name in ("train_mean", "ridge")
    }
    software = _mapping(pretest.get("software"), "pretest software evidence is missing")
    public_software = {
        key: software[key] for key in ("python", "numpy", "scikit_learn") if key in software
    }
    summary: dict[str, JsonValue] = {
        "schema_version": "aidd-commons.rmd17-system-state-development-summary.v1",
        "artifact_type": "reviewed-development-summary",
        "protocol_id": PROTOCOL_ID,
        "reviewed_on": REVIEWED_ON,
        "source": {
            "version": _required_value(source, "version", "pretest source version is missing"),
            "doi": _required_value(source, "doi", "pretest source DOI is missing"),
            "licence": _required_value(source, "licence", "pretest source licence is missing"),
        },
        "systems": {
            "ethanol": "development_evaluation_complete",
            "malonaldehyde": "development_evaluation_complete",
            "benzene": "not_run",
            "uracil": "not_run",
        },
        "split": {
            "selected_frames": _required_value(
                split, "selected_frames", "pretest selected frame count is missing"
            ),
            "partitions": _required_value(
                split, "partitions", "pretest partition counts are missing"
            ),
            "original_index_ordering": _required_value(
                split,
                "original_index_ordering",
                "pretest original-index ordering is missing",
            ),
            "ordering_diagnostics_by_system": ordering_diagnostics,
        },
        "features": features,
        "selection": {
            "frozen_alphas": _required_value(
                selection, "frozen_alphas", "pretest frozen alpha grid is missing"
            ),
            "validation_grid": public_grid,
            "selected_alpha": selected_alpha,
        },
        "development_evaluation": per_system_metrics,
        "aggregates": aggregate_payload,
        "software": public_software,
        "locked_evaluations": {"benzene": "not_run", "uracil": "not_run"},
        "limitations": [
            "Development metrics use ethanol and malonaldehyde only; "
            "benzene and uracil are not run.",
            "Stable original-index ordering does not remove molecular-dynamics time correlation.",
            "Within-system development evaluation does not establish cross-system generalization.",
        ],
    }
    validate_public_summary(summary)
    return summary


def write_development_summary(repository_root: Path) -> Path:
    """Write the public aggregate only at its one canonical repository-relative path."""

    paths = canonical_paths(repository_root)
    summary = development_summary(paths.pretest_path)
    _write_json(paths.summary_path, summary)
    return paths.summary_path


def validate_public_summary(summary: Mapping[str, object]) -> None:
    """Recursively reject internal arrays, identities, paths, and command receipts."""

    _validate_public_value(summary, "summary")


def _validate_protocol_sampling(payload: Mapping[str, object]) -> None:
    sampling = _mapping(payload.get("sampling"), "protocol sampling must be an object")
    expected_sampling = {
        "sort": "stable ascending old_indices",
        "rank_expression": "rint(linspace(0, n_frames - 1, 1000)).astype(int64)",
        "selected_frames": SAMPLED_FRAME_COUNT,
        "partitions": {
            "train": TRAIN_FRAME_COUNT,
            "validation": VALIDATION_FRAME_COUNT,
            "evaluation": EVALUATION_FRAME_COUNT,
        },
    }
    if dict(sampling) != expected_sampling:
        raise PipelineContractError("protocol sampling differs from the frozen contract")


def _validate_protocol_models(payload: Mapping[str, object]) -> None:
    models = _mapping(payload.get("models"), "protocol models must be an object")
    expected_models = {
        "control": "per-system train mean energy",
        "learned": "StandardScaler on train features; train-energy centering; "
        "Ridge(fit_intercept=False, solver=lsqr)",
        "alphas": list(FROZEN_ALPHAS),
        "selection": "median validation MAE across ethanol and malonaldehyde; "
        "exact ties choose larger alpha",
    }
    if dict(models) != expected_models:
        raise PipelineContractError("protocol models differ from the frozen contract")


def _validate_protocol_method_sections(payload: Mapping[str, object]) -> None:
    expected_sections: dict[str, dict[str, object]] = {
        "units": {
            "coordinates": "Angstrom",
            "energies": "kcal/mol",
            "forces": "kcal/mol/Angstrom",
        },
        "features": {
            "channels": "lexicographic unordered element pairs",
            "edges_angstrom": "0.0, 0.1, ..., 10.0",
            "ordinary_bins": 100,
            "overflow": "distance over 10.0 Angstrom",
            "normalization": "fixed atom-pair count per channel",
        },
        "metrics": {
            "per_system": ["MAE kcal/mol", "RMSE kcal/mol", "target range kcal/mol"],
            "aggregate": ["median per-system MAE", "range of per-system MAEs"],
            "forbidden": ["frame-pooled metrics", "confidence intervals"],
        },
        "feature_and_target_boundaries": {
            "target_array": "energies",
            "allowed_feature_arrays": ["nuclear_charges", "coords"],
            "prohibited_arrays": ["forces", "old_energies", "old_forces"],
        },
    }
    for name, expected in expected_sections.items():
        observed = _mapping(payload.get(name), f"protocol {name} must be an object")
        if dict(observed) != expected:
            raise PipelineContractError(f"protocol {name} differs from the frozen contract")


def _download_and_validate(
    paths: LabPaths,
    specification: SystemSpec,
    url: str,
    transport: DownloadTransport,
) -> Path:
    destination = paths.data_dir / specification.filename
    if destination.exists():
        try:
            load_system_npz(destination, specification)
        except DataContractError:
            pass
        else:
            return destination

    paths.data_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = _sibling_temporary_path(paths.data_dir, specification.filename)
    try:
        transport(url, temporary_path)
        _validate_staged_npz(temporary_path, specification)
        os.replace(temporary_path, destination)
    except (KeyboardInterrupt, SystemExit):
        temporary_path.unlink(missing_ok=True)
        raise
    except Exception as error:
        temporary_path.unlink(missing_ok=True)
        if isinstance(error, PipelineContractError):
            raise
        raise PipelineContractError(
            f"downloaded {specification.system_id} failed validation: {error}"
        ) from error
    return destination


def _load_or_download_locked_system(
    paths: LabPaths,
    specification: SystemSpec,
    url: str,
    transport: DownloadTransport,
) -> RMD17SystemData:
    path = _download_and_validate(paths, specification, url, transport)
    return _load_system(path, specification)


def _sibling_temporary_path(directory: Path, filename: str) -> Path:
    with tempfile.NamedTemporaryFile(
        dir=directory,
        prefix=f".{filename}.",
        suffix=".partial",
        delete=False,
    ) as temporary:
        return Path(temporary.name)


def _validate_staged_npz(path: Path, specification: SystemSpec) -> None:
    validation_dir = Path(
        tempfile.mkdtemp(prefix=f".{specification.system_id}-validate-", dir=path.parent)
    )
    validation_path = validation_dir / specification.filename
    try:
        try:
            os.link(path, validation_path)
        except OSError:
            shutil.copyfile(path, validation_path)
        load_system_npz(validation_path, specification)
    finally:
        validation_path.unlink(missing_ok=True)
        validation_dir.rmdir()


def _stream_download(url: str, destination: Path) -> None:
    try:
        with urlopen(url) as response, destination.open("wb") as handle:  # noqa: S310
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
    except (OSError, URLError) as error:
        raise PipelineContractError(f"could not stream {url}: {error}") from error


def _load_canonical_system(paths: LabPaths, specification: SystemSpec) -> RMD17SystemData:
    path = paths.data_dir / specification.filename
    if not path.exists():
        relative_path = path.relative_to(paths.repository_root)
        raise PipelineContractError(
            f"missing canonical {specification.system_id} development file: {relative_path}"
        )
    return _load_system(path, specification)


def _load_system(path: Path, specification: SystemSpec) -> RMD17SystemData:
    try:
        return load_system_npz(path, specification)
    except DataContractError as error:
        raise PipelineContractError(f"invalid {specification.system_id} NPZ: {error}") from error


def _prepare_system(system: RMD17SystemData) -> _PreparedSystem:
    split = partition_system(system)
    train_features = build_pair_distance_features(system.nuclear_charges, split.train.coordinates)
    validation_features = build_pair_distance_features(
        system.nuclear_charges, split.validation.coordinates
    )
    evaluation_features = build_pair_distance_features(
        system.nuclear_charges, split.evaluation.coordinates
    )
    if (
        train_features.channels != validation_features.channels
        or train_features.channels != evaluation_features.channels
        or train_features.names != validation_features.names
        or train_features.names != evaluation_features.names
    ):
        raise PipelineContractError(f"feature channels differ across {system.system_id} partitions")
    return _PreparedSystem(
        system_id=system.system_id,
        split=split,
        train_features=train_features,
        validation_features=validation_features,
        evaluation_features=evaluation_features,
        train_row_ids=tuple(
            f"{system.system_id}:{int(position)}" for position in split.train.source_positions
        ),
    )


def _validate_development_system_order(prepared: Sequence[_PreparedSystem]) -> None:
    if tuple(item.system_id for item in prepared) != DEVELOPMENT_SYSTEM_IDS:
        raise PipelineContractError("development systems must be ethanol then malonaldehyde")


def _shared_alpha_evidence(
    prepared: Sequence[_PreparedSystem],
) -> tuple[SharedAlphaSelection, list[dict[str, JsonValue]]]:
    development_data = tuple(
        SystemDevelopmentData(
            system_id=item.system_id,
            train_features=item.train_features.values,
            train_energies=item.split.train.energies,
            train_row_ids=item.train_row_ids,
            validation_features=item.validation_features.values,
            validation_energies=item.split.validation.energies,
        )
        for item in prepared
    )
    try:
        selection = select_shared_alpha(development_data)
    except ModelContractError as error:
        raise PipelineContractError(f"could not select the frozen shared alpha: {error}") from error

    grid: list[dict[str, JsonValue]] = []
    for alpha in FROZEN_ALPHAS:
        per_system_mae: dict[str, JsonValue] = {}
        for item in prepared:
            fitted = fit_system_ridge(
                item.train_features.values,
                item.split.train.energies,
                item.train_row_ids,
                alpha=alpha,
            )
            predictions = predict_system_ridge(fitted, item.validation_features.values)
            per_system_mae[item.system_id] = float(
                energy_metrics(item.split.validation.energies, predictions).mae
            )
        median_mae = float(np.median(np.asarray(list(per_system_mae.values()), dtype=float)))
        expected_median = selection.median_validation_mae[alpha]
        if not np.isclose(median_mae, expected_median, rtol=0.0, atol=0.0):
            raise PipelineContractError(
                "selection evidence diverges from the frozen shared-alpha routine"
            )
        grid.append(
            {
                "alpha": alpha,
                "per_system_validation_mae": per_system_mae,
                "median_validation_mae": median_mae,
            }
        )
    return selection, grid


def _pretest_payload(
    protocol_payload: Mapping[str, object],
    prepared: Sequence[_PreparedSystem],
    selected_models: Sequence[FittedSystemRidge],
    grid: list[dict[str, JsonValue]],
    selected_alpha: float,
) -> dict[str, JsonValue]:
    source = _mapping(protocol_payload.get("source"), "protocol source must be an object")
    if len(prepared) != len(selected_models):
        raise PipelineContractError("selected models do not align with development systems")
    development = {
        item.system_id: _development_system_payload(item, fitted)
        for item, fitted in zip(prepared, selected_models, strict=True)
    }
    return {
        "schema_version": "aidd-commons.rmd17-system-state-pretest.v1",
        "artifact_type": "internal-development-pretest",
        "protocol_id": PROTOCOL_ID,
        "pretest_passed": True,
        "source": {
            "figshare_article": source["figshare_article"],
            "version": source["version"],
            "doi": source["doi"],
            "licence": source["licence"],
            "primary_paper_doi": source["primary_paper_doi"],
            "systems": {
                system_id: {
                    "file_id": SYSTEMS[system_id].file_id,
                    "status": "development_available",
                }
                for system_id in DEVELOPMENT_SYSTEM_IDS
            },
        },
        "protocol": {
            "split": {
                "selected_frames": SAMPLED_FRAME_COUNT,
                "partitions": {
                    "train": TRAIN_FRAME_COUNT,
                    "validation": VALIDATION_FRAME_COUNT,
                    "evaluation": EVALUATION_FRAME_COUNT,
                },
                "original_index_ordering": "stable ascending old_indices",
            },
            "features": {
                "construction": "per-system lexicographic unordered element-pair channels",
                "bins_per_channel": 101,
                "distance_bin_width_angstrom": DISTANCE_BIN_WIDTH,
                "by_system": {
                    item.system_id: _feature_layout_payload(item.train_features)
                    for item in prepared
                },
            },
            "feature_target_boundary": {
                "target": "energies",
                "feature_arrays": ["nuclear_charges", "coords"],
                "validation_only_arrays": ["forces", "old_energies", "old_forces"],
            },
        },
        "development": development,
        "selection": {
            "frozen_alphas": list(FROZEN_ALPHAS),
            "grid": grid,
            "selected_alpha": selected_alpha,
        },
        "software": _software_payload(),
        "locked_evaluations": {"benzene": "not_run", "uracil": "not_run"},
    }


def _development_system_payload(
    prepared: _PreparedSystem,
    fitted: FittedSystemRidge,
) -> dict[str, JsonValue]:
    if fitted.alpha not in FROZEN_ALPHAS:
        raise PipelineContractError("development model alpha is outside the frozen grid")
    train_mean = train_mean_predictions(
        prepared.split.train.energies,
        row_count=prepared.split.evaluation.energies.shape[0],
    )
    ridge = predict_system_ridge(fitted, prepared.evaluation_features.values)
    target = prepared.split.evaluation.energies
    metrics = {
        "train_mean": _metrics_payload(energy_metrics(target, train_mean)),
        "ridge": _metrics_payload(energy_metrics(target, ridge)),
    }
    records = _evaluation_records(prepared.split.evaluation, target, train_mean, ridge)
    return {
        "split_membership": _split_membership_payload(prepared.split),
        "fit_row_ids": list(prepared.train_row_ids),
        "evaluation": {"metrics": metrics, "records": records},
    }


def _evaluation_records(
    partition: FramePartition,
    targets: np.ndarray,
    train_mean: np.ndarray,
    ridge: np.ndarray,
) -> list[JsonValue]:
    return [
        {
            "old_index": int(partition.old_indices[index]),
            "source_position": int(partition.source_positions[index]),
            "target": float(targets[index]),
            "predictions": {
                "train_mean": float(train_mean[index]),
                "ridge": float(ridge[index]),
            },
            "errors": {
                "train_mean": float(targets[index] - train_mean[index]),
                "ridge": float(targets[index] - ridge[index]),
            },
        }
        for index in range(targets.shape[0])
    ]


def _split_membership_payload(split: SystemSplit) -> dict[str, JsonValue]:
    return {
        partition_name: {
            "old_indices": [int(value) for value in partition.old_indices],
            "source_positions": [int(value) for value in partition.source_positions],
        }
        for partition_name, partition in (
            ("train", split.train),
            ("validation", split.validation),
            ("evaluation", split.evaluation),
        )
    }


def _read_pretest_for_locked_evaluation(pretest_path: Path) -> dict[str, JsonValue]:
    if not pretest_path.exists():
        raise LockedEvaluationError("a development pretest artifact is required before evaluation")
    pretest = _read_json(pretest_path, LockedEvaluationError)
    if pretest.get("pretest_passed") is not True:
        raise LockedEvaluationError("locked evaluation requires a passed development pretest")
    return pretest


def _selected_alpha(pretest: Mapping[str, object]) -> float:
    selection = _mapping(pretest.get("selection"), "pretest selection evidence is missing")
    selected = selection.get("selected_alpha")
    if not isinstance(selected, (int, float)) or isinstance(selected, bool):
        raise LockedEvaluationError("pretest selected alpha must be numeric")
    alpha = float(selected)
    if alpha not in FROZEN_ALPHAS:
        raise LockedEvaluationError("pretest selected alpha is outside the frozen grid")
    return alpha


def _claim_locked_evaluation(paths: LabPaths) -> None:
    paths.results_dir.mkdir(parents=True, exist_ok=True)
    marker_payload: dict[str, JsonValue] = {
        "schema_version": "aidd-commons.rmd17-system-state-locked-started.v1",
        "protocol_id": PROTOCOL_ID,
        "systems": list(LOCKED_SYSTEM_IDS),
        "status": "started",
    }
    try:
        with paths.locked_marker_path.open("x", encoding="utf-8") as marker:
            json.dump(marker_payload, marker, indent=2, sort_keys=True)
            marker.write("\n")
    except FileExistsError as error:
        raise LockedEvaluationError("locked evaluation has already been claimed") from error


def _locked_metrics_payload(
    prepared: Sequence[_PreparedSystem],
    selected_alpha: float,
) -> dict[str, JsonValue]:
    if tuple(item.system_id for item in prepared) != LOCKED_SYSTEM_IDS:
        raise LockedEvaluationError("locked evaluation must include benzene and uracil together")
    results: dict[str, JsonValue] = {}
    for item in prepared:
        fitted = fit_system_ridge(
            item.train_features.values,
            item.split.train.energies,
            item.train_row_ids,
            alpha=selected_alpha,
        )
        train_mean = train_mean_predictions(
            item.split.train.energies,
            row_count=item.split.evaluation.energies.shape[0],
        )
        ridge = predict_system_ridge(fitted, item.evaluation_features.values)
        target = item.split.evaluation.energies
        results[item.system_id] = {
            "train_mean": _metrics_payload(energy_metrics(target, train_mean)),
            "ridge": _metrics_payload(energy_metrics(target, ridge)),
        }
    return {
        "schema_version": "aidd-commons.rmd17-system-state-locked-metrics.v1",
        "protocol_id": PROTOCOL_ID,
        "selected_alpha": selected_alpha,
        "results": results,
        "software": _software_payload(),
    }


def _refuse_after_locked_evaluation(paths: LabPaths, error_type: type[ValueError]) -> None:
    if paths.locked_marker_path.exists():
        raise error_type("locked evaluation has already been claimed")
    if paths.locked_metrics_path.exists():
        raise error_type("locked evaluation output already exists")


def _evaluation_metrics_for_public(
    development: Mapping[str, object], system_id: str
) -> dict[str, JsonValue]:
    system = _mapping(development.get(system_id), f"pretest {system_id} evidence is missing")
    evaluation = _mapping(system.get("evaluation"), f"pretest {system_id} evaluation is missing")
    metrics = _mapping(evaluation.get("metrics"), f"pretest {system_id} metrics are missing")
    if set(metrics) != {"train_mean", "ridge"}:
        raise PipelineContractError(f"pretest {system_id} metrics schema is invalid")
    return {
        model_name: _public_metric_schema(
            metrics[model_name],
            f"pretest {system_id} {model_name} metrics",
        )
        for model_name in ("train_mean", "ridge")
    }


def _public_ordering_diagnostics_by_system(
    development: Mapping[str, object],
) -> dict[str, JsonValue]:
    return {
        system_id: _public_ordering_diagnostics(development, system_id)
        for system_id in DEVELOPMENT_SYSTEM_IDS
    }


def _public_ordering_diagnostics(
    development: Mapping[str, object], system_id: str
) -> dict[str, JsonValue]:
    system = _mapping(development.get(system_id), f"pretest {system_id} evidence is missing")
    membership = _mapping(
        system.get("split_membership"),
        f"pretest {system_id} split membership is missing",
    )
    partition_sizes = {
        "train": TRAIN_FRAME_COUNT,
        "validation": VALIDATION_FRAME_COUNT,
        "evaluation": EVALUATION_FRAME_COUNT,
    }
    if set(membership) != set(partition_sizes):
        raise PipelineContractError(
            f"pretest {system_id} split membership partition schema is invalid"
        )

    old_indices_by_partition: dict[str, list[int]] = {}
    for partition_name, expected_size in partition_sizes.items():
        partition = _mapping(
            membership[partition_name],
            f"pretest {system_id} {partition_name} split membership is invalid",
        )
        if set(partition) != {"old_indices", "source_positions"}:
            raise PipelineContractError(
                f"pretest {system_id} {partition_name} split membership partition schema is invalid"
            )
        old_indices = _nonnegative_integer_list(
            partition["old_indices"],
            f"pretest {system_id} {partition_name} old indices must be non-negative integers",
        )
        source_positions = _nonnegative_integer_list(
            partition["source_positions"],
            f"pretest {system_id} {partition_name} source positions must be non-negative integers",
        )
        if len(old_indices) != expected_size or len(source_positions) != expected_size:
            raise PipelineContractError(
                f"pretest {system_id} {partition_name} split membership length is invalid"
            )
        old_indices_by_partition[partition_name] = old_indices

    ordered_old_indices = [
        old_index
        for partition_name in partition_sizes
        for old_index in old_indices_by_partition[partition_name]
    ]
    if any(
        current <= previous
        for previous, current in zip(
            ordered_old_indices, ordered_old_indices[1:], strict=False
        )
    ):
        raise PipelineContractError(
            f"pretest {system_id} split membership old indices must be globally strictly increasing"
        )
    adjacent_gaps = [
        current - previous
        for previous, current in zip(
            ordered_old_indices, ordered_old_indices[1:], strict=False
        )
    ]
    sorted_gaps = sorted(adjacent_gaps)
    return {
        "strictly_increasing": True,
        "adjacent_original_index_gap": {
            "minimum": min(adjacent_gaps),
            "median": sorted_gaps[len(sorted_gaps) // 2],
            "maximum": max(adjacent_gaps),
        },
        "partition_boundary_gap": {
            "train_to_validation": old_indices_by_partition["validation"][0]
            - old_indices_by_partition["train"][-1],
            "validation_to_evaluation": old_indices_by_partition["evaluation"][0]
            - old_indices_by_partition["validation"][-1],
        },
    }


def _feature_layout_payload(features: PairDistanceFeatures) -> dict[str, JsonValue]:
    return {
        "element_pair_channels": [_channel_name(channel) for channel in features.channels],
        "channel_count": len(features.channels),
        "feature_dimension": int(features.values.shape[1]),
    }


def _public_feature_summary(features: Mapping[str, object]) -> dict[str, JsonValue]:
    expected_keys = {
        "construction",
        "bins_per_channel",
        "distance_bin_width_angstrom",
        "by_system",
    }
    if set(features) != expected_keys:
        raise PipelineContractError("pretest feature schema is invalid")
    construction = features.get("construction")
    if construction != "per-system lexicographic unordered element-pair channels":
        raise PipelineContractError("pretest feature construction differs from the frozen contract")
    bins_per_channel = _positive_integer(
        features.get("bins_per_channel"), "pretest bins per channel must be a positive integer"
    )
    if bins_per_channel != 101:
        raise PipelineContractError("pretest bins per channel differ from the frozen contract")
    bin_width = _finite_number(
        features.get("distance_bin_width_angstrom"),
        "pretest distance bin width must be numeric",
    )
    if bin_width != DISTANCE_BIN_WIDTH:
        raise PipelineContractError("pretest distance bin width differs from the frozen contract")
    by_system = _mapping(features.get("by_system"), "pretest system feature layouts are missing")
    if set(by_system) != set(DEVELOPMENT_SYSTEM_IDS):
        raise PipelineContractError("pretest feature layouts must cover both development systems")
    return {
        "construction": construction,
        "bins_per_channel": bins_per_channel,
        "distance_bin_width_angstrom": bin_width,
        "by_system": {
            system_id: _public_feature_layout(
                by_system[system_id], system_id, bins_per_channel
            )
            for system_id in DEVELOPMENT_SYSTEM_IDS
        },
    }


def _public_feature_layout(
    value: object,
    system_id: str,
    bins_per_channel: int,
) -> dict[str, JsonValue]:
    layout = _mapping(value, f"pretest {system_id} feature layout must be an object")
    expected_keys = {"element_pair_channels", "channel_count", "feature_dimension"}
    if set(layout) != expected_keys:
        raise PipelineContractError(f"pretest {system_id} feature layout schema is invalid")
    channels_value = layout.get("element_pair_channels")
    if not isinstance(channels_value, list) or not all(
        isinstance(channel, str) for channel in channels_value
    ):
        raise PipelineContractError(f"pretest {system_id} element-pair channels must be strings")
    channels = cast(list[str], channels_value)
    parsed_channels = tuple(_parse_channel_name(channel, system_id) for channel in channels)
    if len(set(parsed_channels)) != len(parsed_channels) or parsed_channels != tuple(
        sorted(parsed_channels)
    ):
        raise PipelineContractError(
            f"pretest {system_id} element-pair channels must be unique and lexicographic"
        )
    channel_count = _positive_integer(
        layout.get("channel_count"), f"pretest {system_id} channel count must be positive"
    )
    feature_dimension = _positive_integer(
        layout.get("feature_dimension"),
        f"pretest {system_id} feature dimension must be positive",
    )
    if channel_count != len(channels):
        raise PipelineContractError(f"pretest {system_id} channel count is inconsistent")
    if feature_dimension != channel_count * bins_per_channel:
        raise PipelineContractError(f"pretest {system_id} feature dimension is inconsistent")
    return {
        "element_pair_channels": list(channels),
        "channel_count": channel_count,
        "feature_dimension": feature_dimension,
    }


def _parse_channel_name(channel: str, system_id: str) -> tuple[int, int]:
    components = channel.removeprefix("Z").split("-Z")
    if len(components) != 2 or not all(component.isdigit() for component in components):
        raise PipelineContractError(f"pretest {system_id} has an invalid element-pair channel")
    left, right = (int(component) for component in components)
    if left <= 0 or right <= 0 or left > right or channel != f"Z{left}-Z{right}":
        raise PipelineContractError(f"pretest {system_id} has an invalid element-pair channel")
    return left, right


def _positive_integer(value: object, message: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PipelineContractError(message)
    return value


def _nonnegative_integer_list(value: object, message: str) -> list[int]:
    entries = _list(value, message)
    if not all(
        isinstance(entry, int) and not isinstance(entry, bool) and entry >= 0
        for entry in entries
    ):
        raise PipelineContractError(message)
    return [cast(int, entry) for entry in entries]


def _public_metric_schema(value: object, description: str) -> dict[str, JsonValue]:
    metrics = _mapping(value, f"{description} must be an object")
    expected_keys = ("mae", "rmse", "target_range")
    if set(metrics) != set(expected_keys):
        raise PipelineContractError(f"{description} schema is invalid")
    return {
        key: _finite_number(metrics[key], f"{description} {key} must be a finite scalar")
        for key in expected_keys
    }


def _public_validation_grid(grid: object) -> list[dict[str, JsonValue]]:
    if not isinstance(grid, list) or len(grid) != len(FROZEN_ALPHAS):
        raise PipelineContractError("pretest validation grid must cover every frozen alpha")
    public_grid: list[dict[str, JsonValue]] = []
    for expected_alpha, entry in zip(FROZEN_ALPHAS, grid, strict=True):
        record = _mapping(entry, "pretest validation grid entry must be an object")
        alpha = _finite_number(record.get("alpha"), "pretest validation alpha must be numeric")
        if alpha != expected_alpha:
            raise PipelineContractError(
                "pretest validation grid differs from the frozen alpha order"
            )
        per_system = _mapping(
            record.get("per_system_validation_mae"),
            "pretest per-system validation MAE is missing",
        )
        if set(per_system) != set(DEVELOPMENT_SYSTEM_IDS):
            raise PipelineContractError(
                "pretest validation grid must contain both development systems"
            )
        public_grid.append(
            {
                "alpha": alpha,
                "per_system_validation_mae": {
                    system_id: _finite_number(
                        per_system[system_id],
                        f"pretest {system_id} validation MAE must be numeric",
                    )
                    for system_id in DEVELOPMENT_SYSTEM_IDS
                },
                "median_validation_mae": _finite_number(
                    record.get("median_validation_mae"),
                    "pretest median validation MAE must be numeric",
                ),
            }
        )
    return public_grid


def _finite_number(value: object, message: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not np.isfinite(value):
        raise PipelineContractError(message)
    return float(value)


def _metric_mae(metrics: JsonValue) -> float:
    mapping = _mapping(metrics, "public metrics must be an object")
    value = mapping.get("mae")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PipelineContractError("public MAE must be numeric")
    return float(value)


def _metrics_payload(metrics: EnergyMetrics) -> dict[str, JsonValue]:
    return cast(dict[str, JsonValue], asdict(metrics))


def _software_payload() -> dict[str, JsonValue]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
    }


def _channel_name(channel: tuple[int, int]) -> str:
    return f"Z{channel[0]}-Z{channel[1]}"


def _read_json(path: Path, error_type: type[ValueError]) -> dict[str, JsonValue]:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise error_type(f"could not read JSON artifact {path}: {error}") from error
    if not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        raise error_type(f"JSON artifact {path} must contain an object")
    return cast(dict[str, JsonValue], loaded)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".partial",
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
        json.dump(payload, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
    os.replace(temporary_path, path)


def _mapping(value: object, message: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise PipelineContractError(message)
    return cast(Mapping[str, object], value)


def _list(value: object, message: str) -> list[object]:
    if not isinstance(value, list):
        raise PipelineContractError(message)
    return value


def _required_value(mapping: Mapping[str, object], key: str, message: str) -> JsonValue:
    if key not in mapping:
        raise PipelineContractError(message)
    return mapping[key]


def _validate_public_value(value: object, location: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise PublicSummaryError(f"public summary has a non-string key at {location}")
            normalized_key = "".join(character for character in key.lower() if character.isalnum())
            if normalized_key in _PUBLIC_FORBIDDEN_KEYS:
                raise PublicSummaryError(
                    f"public summary contains forbidden key {key} at {location}"
                )
            _validate_public_value(child, f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_public_value(child, f"{location}[{index}]")
        return
    if isinstance(value, str):
        normalized = value.replace("\\", "/").lower()
        if any(segment in normalized for segment in _PUBLIC_FORBIDDEN_PATH_SEGMENTS):
            raise PublicSummaryError(f"public summary contains forbidden path at {location}")
