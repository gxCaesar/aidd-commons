"""One-time paired orchestration, with no download or public export side effects."""

from __future__ import annotations

import json
import platform
import tomllib
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from aidd_commons.chembl_egfr.data import load_cached_frozen_datasets
from aidd_commons.chembl_egfr.pipeline import validate_frozen_scaffold_counts
from aidd_commons.chembl_egfr.protocol import protocol_payload
from aidd_commons.pool_budget_campaign import (
    CampaignContractError,
    freeze_predictions,
    prepare_campaign,
    score_campaign,
)

PROTOCOL_ID = "chembl37-egfr-pool-budget-v1"
OUTPUT = Path("labs/pool_budget/results")
MARKER = "locked-evaluation.started.json"
METRICS = "locked-metrics.json"
DETAILS = "locked-details.json"


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CampaignContractError(f"expected a regular non-symlink file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CampaignContractError(f"expected an object: {path}")
    return value


def validate_real_protocol(root: Path) -> dict[str, Any]:
    """Check executable settings and source inheritance without opening any data."""
    protocol = _read_json(root / "labs/pool_budget/real-protocol.json")
    source = _read_json(root / "labs/chembl_egfr/protocol.json")

    def require(actual: Any, expected: Any, name: str) -> None:
        if actual != expected:
            raise CampaignContractError(f"frozen protocol mismatch: {name}")

    try:
        require(source, protocol_payload(), "T05 source")
        require(protocol["protocol_id"], PROTOCOL_ID, "protocol ID")
        require(protocol["schema_version"], "aidd-commons.pool-budget-real-protocol.v1", "schema")
        reference = protocol["frozen_t05_reference"]
        require(reference["path"], "labs/chembl_egfr/protocol.json", "source path")
        require(reference["protocol_version"], source["protocol_version"], "source version")
        require(reference["entity_contract"], source["entity"], "parent entities")
        labels = dict(reference["label_contract"])
        labels.update(labels.pop("filters"))
        require(labels, source["labels"], "source labels and filters")
        require(
            {
                assay: replay["expected_parent_count"]
                for assay, replay in reference["assay_replays"].items()
            },
            source["source"]["expected_parent_counts"],
            "assay identities and counts",
        )
        require(protocol["input_contract"]["no_cross_assay_training"], True, "assay separation")
        partition = protocol["partition_contract"]
        require(partition["partition_names"], ["initial", "pool", "evaluation"], "partition order")
        require(
            partition["real_target_capacities"],
            {"initial": "0.10 * N", "pool": "0.70 * N", "evaluation": "0.20 * N"},
            "capacities",
        )
        acquisition = protocol["acquisition_contract"]
        require(acquisition["round_count"], 4, "round count")
        require(acquisition["batch_size"], "q = floor(original_pool_parent_count / 20)", "batch")
        require(acquisition["checkpoint_acquired_counts"], "0, q, 2q, 3q, 4q", "checkpoints")
        require(acquisition["policies"]["random"]["seeds"], [0, 1, 2, 3, 4], "random seeds")
        fingerprint = dict(acquisition["policies"]["maxmin"]["fingerprint_reference"])
        require(
            fingerprint.pop("source"), "frozen T05 morgan_ridge representation", "Morgan source"
        )
        expected_fingerprint = dict(source["representations"]["morgan_ridge"])
        expected_fingerprint.pop("data_fitted_transform")
        require(fingerprint, expected_fingerprint, "Morgan parameters")
        require(
            protocol["prediction_contract"]["model"],
            {
                "family": "Ridge",
                "alpha": 1.0,
                "fit_intercept": True,
                "solver": "lsqr",
                "tol": 1e-8,
                "max_iter": 10000,
                "scaling": "none",
                "tuning": "forbidden",
            },
            "fixed Ridge",
        )
        require(
            protocol["target_and_recovery_contract"]["target_count"],
            "ceil(original_pool_parent_count / 10)",
            "target count",
        )
    except (KeyError, TypeError, AttributeError) as error:
        raise CampaignContractError("missing or malformed frozen protocol field") from error
    return protocol


def _software(root: Path) -> dict[str, str]:
    versions = {package: version(package) for package in ("numpy", "rdkit", "scikit-learn")}
    dependencies = tomllib.loads((root / "pyproject.toml").read_text())["project"]["dependencies"]
    for package, observed in versions.items():
        if f"{package}=={observed}" not in dependencies:
            raise CampaignContractError(f"runtime differs from pinned {package} version")
    if platform.python_version_tuple()[:2] != ("3", "11"):
        raise CampaignContractError("the frozen real campaign requires Python 3.11")
    return {"python": platform.python_version(), **versions}


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
    except FileExistsError as error:
        raise CampaignContractError(f"one-time campaign already claimed: {path.name}") from error


def run_locked_campaign(root: Path, *, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise CampaignContractError("explicit locked-evaluation confirmation is required")
    root = root.resolve()
    output = root / OUTPUT
    for path in (root / "labs", root / "labs/pool_budget", output):
        if path.is_symlink():
            raise CampaignContractError("campaign output ancestors must not be symlinks")
    if any(
        (output / name).exists() or (output / name).is_symlink()
        for name in (MARKER, METRICS, DETAILS)
    ):
        raise CampaignContractError(
            "one-time campaign already started or completed; no automatic retry"
        )
    protocol = validate_real_protocol(root)
    software = _software(root)
    output.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    _write_exclusive(output / MARKER, {"protocol_id": PROTOCOL_ID, "started_at": started})

    # The marker stays on any failure, including ingestion and prediction failures.
    datasets = load_cached_frozen_datasets(root / ".cache/chembl_egfr")
    validate_frozen_scaffold_counts(datasets.primary, datasets.external)
    assays = (datasets.primary, datasets.external)
    prepared = tuple(prepare_campaign(dataset) for dataset in assays)
    frozen = tuple(freeze_predictions(campaign) for campaign in prepared)
    # BOTH assays have fixed all predictions before the first scoring access.
    scores = {
        dataset.assay_chembl_id: score_campaign(campaign, predictions)
        for dataset, campaign, predictions in zip(assays, prepared, frozen, strict=True)
    }
    details = {}
    for dataset, campaign, predictions in zip(assays, prepared, frozen, strict=True):
        details[dataset.assay_chembl_id] = {
            "parent_ids": list(campaign.library.parent_ids),
            "scaffold_groups": list(campaign.library.groups),
            "plan": asdict(campaign.plan),
            "predictions": predictions.values,
            "fit_rows": predictions.fit_rows,
            "evaluation_targets": campaign.oracle.evaluation_targets().tolist(),
            "pool_targets": campaign.oracle.pool_targets().tolist(),
            "initial_targets": [
                next(
                    record.target_pchembl
                    for record in dataset.records
                    if record.parent_molecule_chembl_id == campaign.library.parent_ids[row]
                )
                for row in campaign.plan.initial
            ],
        }
    result = {
        "protocol_id": PROTOCOL_ID,
        "status": "completed",
        "started_at": started,
        "completed_at": datetime.now(UTC).isoformat(),
        "software": software,
        "scope": protocol["interpretation_and_scope"],
        "assays": scores,
    }
    _write_exclusive(output / DETAILS, {"protocol_id": PROTOCOL_ID, "assays": details})
    _write_exclusive(output / METRICS, result)
    return result
