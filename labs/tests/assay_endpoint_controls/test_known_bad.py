"""The frozen contract must refuse a mutated protocol, and nothing may be written.

Each mutation below is an edit a reader could make to
`labs/assay_endpoint_controls/protocol.json` by accident or on purpose. The
pipeline must refuse every one of them before it reads the archived records,
and it must not leave a results directory behind.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from aidd_commons.assay_endpoint_controls import pipeline

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_RELATIVE = "labs/assay_endpoint_controls/protocol.json"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    target = tmp_path / PROTOCOL_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / PROTOCOL_RELATIVE, target)
    return tmp_path


def forbid_cache(*args: object, **kwargs: object) -> None:
    raise AssertionError("the archived records must not be read before the contract is checked")


def mutate(protocol: dict, mutation: str) -> None:
    if mutation == "protocol-id":
        protocol["protocol_id"] = "pubchem-bioassay-endpoint-controls-v2"
    elif mutation == "schema-version":
        protocol["schema_version"] = "aidd-commons.assay-endpoint-controls-protocol.v0"
    elif mutation == "data-version":
        protocol["data_version"] = ""
    elif mutation == "byte-length":
        protocol["sources"]["assays"]["548"]["data"]["bytes"] += 1
    elif mutation == "member-name":
        protocol["sources"]["assays"]["439"]["data"]["member"] = "0000001_0001000/440.csv.gz"
    elif mutation == "container-length":
        protocol["sources"]["assays"]["1277"]["data"]["container_bytes"] = 1
    elif mutation == "crc":
        protocol["sources"]["assays"]["519"]["description"]["crc32"] = 1
    elif mutation == "source-scheme":
        protocol["sources"]["assays"]["691"]["data"]["url"] = "http://example.invalid/a.zip"
    elif mutation == "endpoint-unit":
        protocol["endpoint"]["units"] = "nanomolar"
    elif mutation == "endpoint-label":
        protocol["endpoint"]["per_assay"]["439"]["labels"] = ["IC50"]
    elif mutation == "control-regime":
        protocol["control_contract"]["per_assay"]["691"]["regime"] = (
            "positive_and_negative_reference"
        )
    elif mutation == "normalisation-equation":
        protocol["control_contract"]["per_assay"]["548"]["normalisation_equation"] = (
            "wells_relative_to_two_references"
        )
    elif mutation == "reference-count":
        protocol["control_contract"]["per_assay"]["464"]["references_expected"] = 2
    elif mutation == "control-keywords":
        protocol["control_contract"]["keyword_lists"]["control_keywords"] = ["vehicle"]
    elif mutation == "split-rule":
        protocol["split"]["rule"] = "row-order-half"
    elif mutation == "split-seed":
        protocol["split"]["seed"] = 1
    elif mutation == "split-grouping":
        protocol["split"]["grouping_unit"] = "PubChem substance identifier"
    elif mutation == "seed":
        protocol["seed"] = 1
    elif mutation == "fit-scope":
        protocol["preprocessing"]["fit_scope"] = ""
    elif mutation == "fit-scope-leak":
        protocol["preprocessing"]["fit_scope_uses_only_own_compound_points"] = False
    elif mutation == "baselines":
        protocol["baselines"] = []
    elif mutation == "metrics":
        protocol["metrics"] = []
    elif mutation == "curve-tolerance":
        protocol["curve_tolerance_points"] = 25.0
    elif mutation == "equation-band":
        protocol["equation_scale_check"]["band_points"] = 1.0
    elif mutation == "equation-fraction":
        protocol["equation_scale_check"]["fraction_inside_required"] = 0.5
    elif mutation == "recorded-column":
        protocol["replicate_structure"]["per_assay"]["439"]["recorded_column"] = "Number of Points "
    elif mutation == "hill-fit-mode":
        protocol["replicate_structure"]["per_assay"]["519"]["hill_fit_mode"] = "free"
    elif mutation == "run-basis-model":
        protocol["run_basis"]["fits_a_predictive_model"] = True
    elif mutation == "run-basis-text":
        protocol["run_basis"]["description"] = ""
    elif mutation == "entity-grouping":
        protocol["entity_rule"]["grouping_unit"] = "PubChem substance identifier"
    elif mutation == "entity-structure":
        protocol["entity_rule"]["structure"] = "PUBCHEM_EXT_DATASOURCE_SMILES"
    else:
        raise AssertionError(f"unknown mutation: {mutation}")


MUTATIONS = [
    "protocol-id",
    "schema-version",
    "data-version",
    "byte-length",
    "member-name",
    "container-length",
    "crc",
    "source-scheme",
    "endpoint-unit",
    "endpoint-label",
    "control-regime",
    "normalisation-equation",
    "reference-count",
    "control-keywords",
    "split-rule",
    "split-seed",
    "split-grouping",
    "seed",
    "fit-scope",
    "fit-scope-leak",
    "baselines",
    "metrics",
    "curve-tolerance",
    "equation-band",
    "equation-fraction",
    "recorded-column",
    "hill-fit-mode",
    "run-basis-model",
    "run-basis-text",
    "entity-grouping",
    "entity-structure",
]


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_known_bad_protocol_is_rejected_before_the_archive_is_read(
    project: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    monkeypatch.setattr(pipeline, "load_cached_assays", forbid_cache)
    path = project / PROTOCOL_RELATIVE
    protocol = json.loads(path.read_text(encoding="utf-8"))
    mutate(protocol, mutation)
    path.write_text(json.dumps(protocol), encoding="utf-8")

    with pytest.raises(pipeline.ProtocolContractError):
        pipeline.run_pipeline(project)

    assert not (project / "labs/assay_endpoint_controls/results").exists()


def test_the_unmutated_protocol_passes_the_contract_check(project: Path) -> None:
    protocol = pipeline.load_protocol(project)
    pipeline.validate_protocol_contract(protocol)


def test_a_contract_failure_is_refused_even_when_the_archive_would_be_readable(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The contract check runs first, so a broken contract never reaches the data."""
    monkeypatch.setattr(pipeline, "load_cached_assays", forbid_cache)
    path = project / PROTOCOL_RELATIVE
    protocol = json.loads(path.read_text(encoding="utf-8"))
    protocol["sources"]["assays"]["439"]["data"]["bytes"] = 1
    path.write_text(json.dumps(protocol), encoding="utf-8")

    with pytest.raises(pipeline.ProtocolContractError):
        pipeline.run_pipeline(project)
    assert not (project / "labs/assay_endpoint_controls/results").exists()
