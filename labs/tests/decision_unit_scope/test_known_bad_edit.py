"""A mutated frozen contract must be rejected before anything is produced.

The lab's runnable task is `aidd_commons.decision_unit_scope.pipeline.run_census_export`.
It validates the on-disk contract against the compiled-in one before it reads
the cache and before it writes anything, so a known-bad edit to
`labs/decision_unit_scope/protocol.json` fails loudly and leaves no artefact
behind. A mutation the pipeline accepts is a failure of this test, not a pass.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.decision_unit_scope.data import DataContractError
from aidd_commons.decision_unit_scope.pipeline import run_census_export
from aidd_commons.decision_unit_scope.protocol import ProtocolContractError

ROOT = Path(__file__).resolve().parents[3]
LAB_RELATIVE = Path("labs/decision_unit_scope")

Mutation = Callable[[dict[str, Any]], None]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    target = tmp_path / LAB_RELATIVE
    target.mkdir(parents=True)
    shutil.copyfile(ROOT / LAB_RELATIVE / "protocol.json", target / "protocol.json")
    return tmp_path


def _drop_a_seed(protocol: dict[str, Any]) -> None:
    del protocol["cohort"]["seeds"][0]


def _rename_a_seed(protocol: dict[str, Any]) -> None:
    protocol["cohort"]["seeds"][0]["pref_name"] = "SOMETHING ELSE"


def _drop_a_parent(protocol: dict[str, Any]) -> None:
    del protocol["cohort"]["resolved_parents"][0]


def _widen_the_endpoint_family(protocol: dict[str, Any]) -> None:
    protocol["endpoint"]["standard_types"] = ["AC50", "EC50", "ED50", "IC50", "Kd", "Ki"]


def _change_the_unit(protocol: dict[str, Any]) -> None:
    protocol["endpoint"]["standard_units"] = "uM"


def _reorder_the_exclusions(protocol: dict[str, Any]) -> None:
    priority = list(protocol["endpoint"]["exclusion_priority"])
    priority[0], priority[1] = priority[1], priority[0]
    protocol["endpoint"]["exclusion_priority"] = priority


def _drop_the_endpoint_from_the_grouping_unit(protocol: dict[str, Any]) -> None:
    protocol["split_and_grouping"]["grouping_unit"] = ["assay_chembl_id", "document_chembl_id"]


def _widen_the_experiment_unit(protocol: dict[str, Any]) -> None:
    protocol["split_and_grouping"]["experiment_unit"] = [
        "assay_chembl_id",
        "document_chembl_id",
        "target_chembl_id",
    ]


def _change_an_artefact_byte_length(protocol: dict[str, Any]) -> None:
    protocol["artifacts"][0]["byte_length"] = int(protocol["artifacts"][0]["byte_length"]) + 1


def _rename_an_artefact(protocol: dict[str, Any]) -> None:
    protocol["artifacts"][0]["path"] = "status-v2.json"


def _change_the_release_date(protocol: dict[str, Any]) -> None:
    protocol["source"]["release_date"] = "2026-01-01"


def _change_the_licence(protocol: dict[str, Any]) -> None:
    protocol["source"]["licence"]["name"] = "MIT"


def _change_the_protocol_id(protocol: dict[str, Any]) -> None:
    protocol["protocol_id"] = "chembl37-decision-unit-scope-v2"


def _change_the_schema_version(protocol: dict[str, Any]) -> None:
    protocol["schema_version"] = "aidd-commons.decision-unit-scope-protocol.v2"


def _change_the_seed(protocol: dict[str, Any]) -> None:
    protocol["seed"] = 1


def _change_the_issued_on_date(protocol: dict[str, Any]) -> None:
    protocol["issued_on"] = "2026-10-22"


def _empty_the_selection_policy(protocol: dict[str, Any]) -> None:
    protocol["selection_and_stop_policy"]["stop_rule"] = ""


MUTATIONS: dict[str, Mutation] = {
    "protocol-id": _change_the_protocol_id,
    "schema-version": _change_the_schema_version,
    "seed": _change_the_seed,
    "issued-on": _change_the_issued_on_date,
    "release-date": _change_the_release_date,
    "licence": _change_the_licence,
    "seed-dropped": _drop_a_seed,
    "seed-renamed": _rename_a_seed,
    "parent-dropped": _drop_a_parent,
    "endpoint-types": _widen_the_endpoint_family,
    "endpoint-units": _change_the_unit,
    "exclusion-priority": _reorder_the_exclusions,
    "grouping-unit": _drop_the_endpoint_from_the_grouping_unit,
    "experiment-unit": _widen_the_experiment_unit,
    "artefact-byte-length": _change_an_artefact_byte_length,
    "artefact-path": _rename_an_artefact,
    "selection-policy": _empty_the_selection_policy,
}


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_known_bad_protocol_is_rejected_before_any_output(project: Path, mutation: str) -> None:
    path = project / LAB_RELATIVE / "protocol.json"
    protocol = json.loads(path.read_text(encoding="utf-8"))
    MUTATIONS[mutation](protocol)
    path.write_text(json.dumps(protocol), encoding="utf-8")

    with pytest.raises(ProtocolContractError):
        run_census_export(
            project / LAB_RELATIVE,
            project / ".cache/decision_unit_scope-not-fetched",
            project / LAB_RELATIVE / "summary.json",
        )

    assert not (project / LAB_RELATIVE / "summary.json").exists()
    assert not (project / LAB_RELATIVE / "results").exists()


def test_the_unmutated_contract_is_accepted_and_the_failure_is_the_missing_cache(
    project: Path,
) -> None:
    """The control: without a mutation the contract passes and the cache is what fails."""
    with pytest.raises(DataContractError):
        run_census_export(
            project / LAB_RELATIVE,
            project / ".cache/decision_unit_scope-not-fetched",
            project / LAB_RELATIVE / "summary.json",
        )
    assert not (project / LAB_RELATIVE / "summary.json").exists()
    assert not (project / LAB_RELATIVE / "results").exists()


def test_a_contract_that_is_not_json_is_rejected(project: Path) -> None:
    path = project / LAB_RELATIVE / "protocol.json"
    path.write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(ProtocolContractError):
        run_census_export(
            project / LAB_RELATIVE,
            project / ".cache/decision_unit_scope-not-fetched",
            project / LAB_RELATIVE / "summary.json",
        )
    assert not (project / LAB_RELATIVE / "summary.json").exists()
