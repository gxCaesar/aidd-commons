"""The frozen contract of the ROSETTA cross-modality agreement lab.

`protocol.json` beside the lab is the authority: it names the published
objects, the byte lengths and entity tags they must have, the columns that
carry a feature and the columns that carry a perturbation's identity, the
seed, the fold counts and the penalty grid. This module reads it, refuses a
contract it cannot honour, and hands the rest of the package a typed view of
it. A contract that does not describe what the code does is a failure, not
something to work around.

The feature columns are identified by a naming rule, never by position or by
a hard-coded count, so a release that adds or drops columns is either read
correctly or rejected rather than silently misaligned.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

IMPLEMENTED_AGGREGATION = "median across replicate wells"
ETAG_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class ContractError(ValueError):
    """Raised when the committed contract is missing, malformed, or asks for
    something this implementation does not do."""


@dataclass(frozen=True)
class SourceFile:
    """One published object, with the size and entity tag frozen with it."""

    key: str
    url: str
    relative_path: str
    byte_length: int
    s3_etag: str
    role: str

    @property
    def filename(self) -> str:
        return self.relative_path.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Contract:
    """A validated view of the committed protocol."""

    protocol_id: str
    schema_version: str
    study_id: str
    batch_id: str
    cell_line: str
    files: tuple[SourceFile, ...]
    transcriptome_feature_pattern: str
    imaging_feature_pattern: str
    transcriptome_required_columns: tuple[str, ...]
    imaging_required_columns: tuple[str, ...]
    transcriptome_join_key: str
    imaging_join_key: str
    transcriptome_label_columns: tuple[str, ...]
    control_pert_type: str
    profile_aggregation: str
    seed: int
    outer_folds: int
    inner_folds: int
    ridge_alphas: tuple[float, ...]
    example_count: int

    @property
    def transcriptome_file(self) -> SourceFile:
        return self._file("transcriptome_replicate")

    @property
    def imaging_file(self) -> SourceFile:
        return self._file("imaging_replicate")

    def _file(self, key: str) -> SourceFile:
        for source in self.files:
            if source.key == key:
                return source
        raise ContractError(f"the contract declares no source file with key {key!r}")


def default_contract_path() -> Path:
    """Where the committed contract lives, relative to the installed package."""
    return Path(__file__).resolve().parents[3] / "rosetta_cross_modality" / "protocol.json"


def _require(value: object, label: str) -> object:
    if value is None:
        raise ContractError(f"the contract has no {label!r} block")
    return value


def _require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _require_sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{label} must be a non-empty list")
    return value


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty string")
    return value


def _require_int(value: object, label: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label} must be an integer")
    if value < minimum:
        raise ContractError(f"{label} must be at least {minimum}")
    return value


def _require_text_tuple(value: object, label: str) -> tuple[str, ...]:
    items = _require_sequence(value, label)
    texts = []
    for item in items:
        texts.append(_require_text(item, f"{label} entry"))
    if len(set(texts)) != len(texts):
        raise ContractError(f"{label} must not repeat an entry")
    return tuple(texts)


def _load_files(source: dict[str, object]) -> tuple[SourceFile, ...]:
    host = _require_text(_require(source.get("host"), "source.host"), "source.host")
    prefix = _require_text(_require(source.get("prefix"), "source.prefix"), "source.prefix")
    entries = _require_sequence(_require(source.get("files"), "source.files"), "source.files")
    files: list[SourceFile] = []
    for entry in entries:
        block = _require_mapping(entry, "source.files entry")
        url = _require_text(_require(block.get("url"), "source.files.url"), "source.files.url")
        if not url.startswith(f"{host}/{prefix}/"):
            raise ContractError(
                f"source.files.url must sit under {host}/{prefix}/, got {url!r}"
            )
        relative_path = _require_text(
            _require(block.get("relative_path"), "source.files.relative_path"),
            "source.files.relative_path",
        )
        if not url.endswith(f"/{relative_path}"):
            raise ContractError(
                f"source.files.relative_path {relative_path!r} does not match the url {url!r}"
            )
        byte_length = _require_int(
            _require(block.get("byte_length"), "source.files.byte_length"),
            "source.files.byte_length",
            minimum=1,
        )
        s3_etag = _require_text(
            _require(block.get("s3_etag"), "source.files.s3_etag"), "source.files.s3_etag"
        )
        if not ETAG_PATTERN.match(s3_etag):
            raise ContractError(
                f"source.files.s3_etag {s3_etag!r} is not a 32-character entity tag"
            )
        files.append(
            SourceFile(
                key=_require_text(
                    _require(block.get("key"), "source.files.key"), "source.files.key"
                ),
                url=url,
                relative_path=relative_path,
                byte_length=byte_length,
                s3_etag=s3_etag,
                role=_require_text(
                    _require(block.get("role"), "source.files.role"), "source.files.role"
                ),
            )
        )
    keys = [source_file.key for source_file in files]
    if len(set(keys)) != len(keys):
        raise ContractError("source.files must not repeat a key")
    for required in ("transcriptome_replicate", "imaging_replicate"):
        if required not in keys:
            raise ContractError(f"source.files must declare {required!r}")
    return tuple(files)


def load_contract(path: Path | None = None) -> Contract:
    """Read and validate the committed contract.

    Every refusal here is a statement about the contract, not about the
    data: a contract that names a column the reader does not have, a fold
    count of one, an empty penalty grid or an aggregation this code does not
    implement is rejected before anything is read.
    """
    contract_path = path if path is not None else default_contract_path()
    try:
        document = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"could not read the contract at {contract_path}: {error}") from error
    root = _require_mapping(document, "the contract")

    protocol_id = _require_text(_require(root.get("protocol_id"), "protocol_id"), "protocol_id")
    schema_version = _require_text(
        _require(root.get("schema_version"), "schema_version"), "schema_version"
    )
    data_version = _require_mapping(
        _require(root.get("data_version"), "data_version"), "data_version"
    )
    source = _require_mapping(_require(root.get("source"), "source"), "source")
    entity = _require_mapping(_require(root.get("entity"), "entity"), "entity")
    label_contract = _require_mapping(
        _require(root.get("label_contract"), "label_contract"), "label_contract"
    )
    model = _require_mapping(_require(root.get("model"), "model"), "model")

    files = _load_files(source)
    join_key = _require_mapping(
        _require(entity.get("join_key"), "entity.join_key"), "entity.join_key"
    )
    transcriptome_required = _require_text_tuple(
        _require(
            entity.get("transcriptome_required_columns"),
            "entity.transcriptome_required_columns",
        ),
        "entity.transcriptome_required_columns",
    )
    imaging_required = _require_text_tuple(
        _require(entity.get("imaging_required_columns"), "entity.imaging_required_columns"),
        "entity.imaging_required_columns",
    )
    transcriptome_join_key = _require_text(
        _require(join_key.get("transcriptome"), "entity.join_key.transcriptome"),
        "entity.join_key.transcriptome",
    )
    imaging_join_key = _require_text(
        _require(join_key.get("imaging"), "entity.join_key.imaging"), "entity.join_key.imaging"
    )
    label_columns = _require_text_tuple(
        _require(entity.get("transcriptome_label_columns"), "entity.transcriptome_label_columns"),
        "entity.transcriptome_label_columns",
    )
    if transcriptome_join_key not in transcriptome_required:
        raise ContractError(
            "entity.join_key.transcriptome must also be a required transcriptomic column"
        )
    if imaging_join_key not in imaging_required:
        raise ContractError(
            "entity.join_key.imaging must also be a required imaging column"
        )
    for column in label_columns:
        if column not in transcriptome_required:
            raise ContractError(
                f"entity.transcriptome_label_columns names {column!r}, which is not a "
                "required transcriptomic column"
            )

    transcriptome_pattern = _require_text(
        _require(
            label_contract.get("transcriptome_feature_pattern"),
            "label_contract.transcriptome_feature_pattern",
        ),
        "label_contract.transcriptome_feature_pattern",
    )
    imaging_pattern = _require_text(
        _require(
            label_contract.get("imaging_feature_pattern"),
            "label_contract.imaging_feature_pattern",
        ),
        "label_contract.imaging_feature_pattern",
    )
    for name, pattern in (
        ("transcriptome", transcriptome_pattern),
        ("imaging", imaging_pattern),
    ):
        try:
            re.compile(pattern)
        except re.error as error:
            raise ContractError(
                f"label_contract.{name}_feature_pattern is not a valid regular expression: {error}"
            ) from error

    aggregation = _require_text(
        _require(entity.get("profile_aggregation"), "entity.profile_aggregation"),
        "entity.profile_aggregation",
    )
    if aggregation != IMPLEMENTED_AGGREGATION:
        raise ContractError(
            f"entity.profile_aggregation asks for {aggregation!r}; this implementation "
            f"aggregates by {IMPLEMENTED_AGGREGATION!r}"
        )

    penalty_grid = _require_sequence(
        _require(model.get("penalty_grid"), "model.penalty_grid"), "model.penalty_grid"
    )
    alphas: list[float] = []
    for item in penalty_grid:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ContractError("model.penalty_grid entries must be numbers")
        if float(item) <= 0:
            raise ContractError("model.penalty_grid entries must be positive")
        alphas.append(float(item))
    if alphas != sorted(set(alphas)):
        raise ContractError("model.penalty_grid must be sorted and free of repeats")

    seed = _require_int(_require(root.get("seed"), "seed"), "seed", minimum=0)
    outer_folds = _require_int(
        _require(root.get("outer_folds"), "outer_folds"), "outer_folds", minimum=2
    )
    inner_folds = _require_int(
        _require(model.get("inner_folds"), "model.inner_folds"), "model.inner_folds", minimum=2
    )
    example_count = _require_int(
        _require(root.get("example_count"), "example_count"), "example_count", minimum=1
    )

    return Contract(
        protocol_id=protocol_id,
        schema_version=schema_version,
        study_id=_require_text(
            _require(data_version.get("study_id"), "data_version.study_id"),
            "data_version.study_id",
        ),
        batch_id=_require_text(
            _require(data_version.get("batch_id"), "data_version.batch_id"),
            "data_version.batch_id",
        ),
        cell_line=_require_text(
            _require(data_version.get("cell_line"), "data_version.cell_line"),
            "data_version.cell_line",
        ),
        files=files,
        transcriptome_feature_pattern=transcriptome_pattern,
        imaging_feature_pattern=imaging_pattern,
        transcriptome_required_columns=transcriptome_required,
        imaging_required_columns=imaging_required,
        transcriptome_join_key=transcriptome_join_key,
        imaging_join_key=imaging_join_key,
        transcriptome_label_columns=label_columns,
        control_pert_type=_require_text(
            _require(entity.get("control_pert_type"), "entity.control_pert_type"),
            "entity.control_pert_type",
        ),
        profile_aggregation=aggregation,
        seed=seed,
        outer_folds=outer_folds,
        inner_folds=inner_folds,
        ridge_alphas=tuple(alphas),
        example_count=example_count,
    )
