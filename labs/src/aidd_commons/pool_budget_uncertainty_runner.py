"""One-time orchestration for the uncertainty-acquisition arm.

Writes only under `labs/pool_budget/uncertainty-results/`; never opens, and has
no code path that could open, any file under `labs/pool_budget/results/`, which
belongs to the already-completed `chembl37-egfr-pool-budget-v1` campaign.
"""

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
from aidd_commons.pool_budget_uncertainty import (
    AcquiredLabelLedger,
    UncertaintyContractError,
    ensemble_variance_order,
    prepare_uncertainty_campaign,
    score_uncertainty_policy,
)

PROTOCOL_ID = "chembl37-egfr-pool-budget-uncertainty-v1"
FROZEN_PROTOCOL_ID = "chembl37-egfr-pool-budget-v1"
OUTPUT = Path("labs/pool_budget/uncertainty-results")
MARKER = "uncertainty-locked-evaluation.started.json"
METRICS = "uncertainty-locked-metrics.json"
DETAILS = "uncertainty-locked-details.json"


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise UncertaintyContractError(f"expected a regular non-symlink file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UncertaintyContractError(f"expected an object: {path}")
    return value


def validate_uncertainty_protocol(root: Path) -> dict[str, Any]:
    """Check the new protocol's declared inheritance without opening any assay data."""
    protocol = _read_json(root / "labs/pool_budget/uncertainty-protocol.json")
    frozen = _read_json(root / "labs/pool_budget/real-protocol.json")

    def require(actual: Any, expected: Any, name: str) -> None:
        if actual != expected:
            raise UncertaintyContractError(f"protocol mismatch: {name}")

    try:
        require(protocol["protocol_id"], PROTOCOL_ID, "protocol ID")
        require(frozen["protocol_id"], FROZEN_PROTOCOL_ID, "frozen reference protocol ID")
        require(
            protocol["frozen_reference"]["protocol_id"],
            frozen["protocol_id"],
            "declared frozen reference",
        )
        require(
            protocol["frozen_reference"]["path"],
            "labs/pool_budget/real-protocol.json",
            "frozen reference path",
        )
        require(
            protocol["output_contract"]["directory"],
            "labs/pool_budget/uncertainty-results/",
            "output directory is separate from the completed campaign",
        )
        require(protocol["new_policy"]["name"], "ensemble-variance-uncertainty", "policy name")
    except (KeyError, TypeError) as error:
        raise UncertaintyContractError("missing or malformed protocol field") from error
    return protocol


def _software(root: Path) -> dict[str, str]:
    versions = {package: version(package) for package in ("numpy", "rdkit", "scikit-learn")}
    dependencies = tomllib.loads((root / "pyproject.toml").read_text())["project"]["dependencies"]
    for package, observed in versions.items():
        if f"{package}=={observed}" not in dependencies:
            raise UncertaintyContractError(f"runtime differs from pinned {package} version")
    if platform.python_version_tuple()[:2] != ("3", "11"):
        raise UncertaintyContractError("this campaign requires Python 3.11")
    return {"python": platform.python_version(), **versions}


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
    except FileExistsError as error:
        raise UncertaintyContractError(f"one-time campaign already claimed: {path.name}") from error


def run_locked_uncertainty_campaign(root: Path, *, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise UncertaintyContractError("explicit locked-evaluation confirmation is required")
    root = root.resolve()
    output = root / OUTPUT
    for path in (root / "labs", root / "labs/pool_budget", output):
        if path.is_symlink():
            raise UncertaintyContractError("campaign output ancestors must not be symlinks")
    if any(
        (output / name).exists() or (output / name).is_symlink()
        for name in (MARKER, METRICS, DETAILS)
    ):
        raise UncertaintyContractError(
            "one-time campaign already started or completed; no automatic retry"
        )
    protocol = validate_uncertainty_protocol(root)
    software = _software(root)
    output.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    _write_exclusive(output / MARKER, {"protocol_id": PROTOCOL_ID, "started_at": started})

    # The marker stays on any failure, including ingestion or acquisition failures.
    datasets = load_cached_frozen_datasets(root / ".cache/chembl_egfr")
    validate_frozen_scaffold_counts(datasets.primary, datasets.external)
    assays = (datasets.primary, datasets.external)
    scores: dict[str, Any] = {}
    details: dict[str, Any] = {}
    for dataset in assays:
        library = prepare_uncertainty_campaign(dataset)
        ledger = AcquiredLabelLedger(library.targets, library.initial)
        picks, diagnostics = ensemble_variance_order(
            library.features, ledger, library.pool, library.checkpoints
        )
        scores[dataset.assay_chembl_id] = {
            "partitions": {
                name: {
                    "parents": len(rows),
                    "groups": len({library.groups[row] for row in rows}),
                }
                for name, rows in (
                    ("initial", library.initial),
                    ("pool", library.pool),
                    ("evaluation", library.evaluation),
                )
            },
            "budget": {
                "checkpoints": list(library.checkpoints),
                "batch_size": library.checkpoints[1],
                "acquired_count": library.checkpoints[-1],
                "original_pool_parent_count": len(library.pool),
                "actual_budget_fraction": library.checkpoints[-1] / len(library.pool),
            },
            "policy": score_uncertainty_policy(library, picks),
        }
        details[dataset.assay_chembl_id] = {
            "parent_ids": list(library.parent_ids),
            "scaffold_groups": list(library.groups),
            "acquisition_order": list(picks),
            "round_diagnostics": [asdict(diagnostic) for diagnostic in diagnostics],
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
