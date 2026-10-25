"""The frozen contract check and the one runnable task.

`validate_protocol_contract` reads `labs/assay_endpoint_controls/protocol.json`
and checks it against the frozen constants in `protocol.py`. It reads no data
and touches no network, so a broken contract is refused before any archive is
opened.

`run_pipeline` is the one runnable task of this lab: it validates the
contract, loads the cached records, computes the descriptive read-out and
writes the result. It writes into a results directory that it creates, and it
creates that directory only after every check has passed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .analysis import assay_profile, split_counts, split_stability
from .data import DataContractError, load_cached_assays
from .protocol import (
    AMBIGUOUS_CONTROL_WORDS,
    ASSAYS,
    CONTAINER_BYTES,
    CONTROL_KEYWORDS,
    CONTROL_REGIMES,
    CURVE_TOLERANCE_POINTS,
    DECLARED_ASSAYS,
    EQUATION_SCALE_BAND_POINTS,
    EQUATION_SCALE_FRACTION,
    HILL_FIT_MODES,
    NORMALISATION_EQUATIONS,
    PROTOCOL_ID,
    PROTOCOL_SCHEMA_VERSION,
    REFERENCE_KEYWORDS,
    SPLIT_RULE,
    SPLIT_SEED,
)


class ProtocolContractError(ValueError):
    """Raised when the frozen protocol does not match the frozen contract."""


#: How many reference wells each declared control regime implies.
EXPECTED_REFERENCES = {
    "positive_and_negative_reference": 2,
    "single_positive_reference": 1,
    "none_declared": 0,
}


def load_protocol(project_root: Path) -> dict[str, Any]:
    """Read the frozen protocol document of this lab."""
    path = project_root / "labs/assay_endpoint_controls/protocol.json"
    if not path.is_file():
        raise ProtocolContractError(f"the frozen protocol {path} is not present")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError(
            f"the frozen protocol {path} is not readable JSON: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise ProtocolContractError(f"the frozen protocol {path} is not a JSON object")
    return payload


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolContractError(message)


def _check_sources(sources: Any) -> None:
    _require(isinstance(sources, dict), "the protocol must declare a sources object")
    assert isinstance(sources, dict)
    declared = sources.get("assays")
    _require(isinstance(declared, dict), "the protocol must declare its assays under sources")
    assert isinstance(declared, dict)
    _require(
        sorted(int(key) for key in declared) == list(DECLARED_ASSAYS),
        "the protocol must declare exactly the assays the frozen contract declares",
    )
    for aid in DECLARED_ASSAYS:
        spec = ASSAYS[aid]
        entry = declared.get(str(aid))
        _require(isinstance(entry, dict), f"assay {aid} is missing from the protocol sources")
        assert isinstance(entry, dict)
        for kind, source in (("data", spec.source_data), ("description", spec.source_description)):
            block = entry.get(kind)
            _require(isinstance(block, dict), f"assay {aid} has no {kind} source block")
            assert isinstance(block, dict)
            _require(
                block.get("member") == source.member,
                f"assay {aid} {kind}: the protocol names a different archived member",
            )
            _require(
                block.get("container_bytes")
                == CONTAINER_BYTES[source.container][
                    "data" if kind == "data" else "description"
                ],
                f"assay {aid} {kind}: the declared container length is not the frozen one",
            )
            _require(
                block.get("compressed_bytes") == source.compressed_bytes,
                f"assay {aid} {kind}: the declared compressed length is not the frozen one",
            )
            _require(
                block.get("member_bytes") == source.member_bytes,
                f"assay {aid} {kind}: the declared member length is not the frozen one",
            )
            _require(
                block.get("bytes") == source.record_bytes,
                f"assay {aid} {kind}: the declared byte length is not the frozen one",
            )
            _require(
                block.get("crc32") == source.crc32,
                f"assay {aid} {kind}: the declared CRC-32 is not the frozen one",
            )
            url = block.get("url")
            _require(
                isinstance(url, str) and url.startswith("https://"),
                f"assay {aid} {kind}: the source URL must be an HTTPS URL",
            )
            _require(
                isinstance(url, str) and url.endswith(f"{source.container}.zip"),
                f"assay {aid} {kind}: the source URL must address the ranged container",
            )


def validate_protocol_contract(protocol: Mapping[str, Any]) -> None:
    """Check the frozen protocol document against the frozen contract.

    Every check reads only the protocol document. A protocol that has been
    edited in a way the contract does not allow is refused here, before any
    archive is opened and before any result is written.
    """
    _require(
        protocol.get("protocol_id") == PROTOCOL_ID,
        f"the protocol id must be {PROTOCOL_ID}",
    )
    _require(
        protocol.get("schema_version") == PROTOCOL_SCHEMA_VERSION,
        f"the protocol schema version must be {PROTOCOL_SCHEMA_VERSION}",
    )
    _require(
        isinstance(protocol.get("data_version"), str) and protocol["data_version"].strip(),
        "the protocol must declare the data version it was computed under",
    )
    _check_sources(protocol.get("sources"))

    entity = protocol.get("entity_rule")
    _require(isinstance(entity, dict), "the protocol must declare an entity rule")
    assert isinstance(entity, dict)
    _require(
        entity.get("grouping_unit") == "PubChem compound identifier (CID) within one assay",
        "the entity rule must name the compound-level grouping unit",
    )
    _require(
        entity.get("structure") == "PUBCHEM_EXT_DATASOURCE_SMILES, read from the archived row",
        "the entity rule must name the inline structure field",
    )

    endpoint = protocol.get("endpoint")
    _require(isinstance(endpoint, dict), "the protocol must declare an endpoint")
    assert isinstance(endpoint, dict)
    _require(
        endpoint.get("units") == "micromolar",
        "the endpoint unit must be micromolar for every declared assay",
    )
    _require(
        isinstance(endpoint.get("per_assay"), dict),
        "the endpoint must declare the endpoint of every declared assay",
    )
    assert isinstance(endpoint.get("per_assay"), dict)
    for aid in DECLARED_ASSAYS:
        spec = ASSAYS[aid]
        block = endpoint["per_assay"].get(str(aid))
        _require(isinstance(block, dict), f"assay {aid} has no endpoint block")
        assert isinstance(block, dict)
        _require(
            block.get("labels") == list(spec.endpoint_labels),
            f"assay {aid}: the declared endpoint labels are not the frozen ones",
        )
        _require(
            block.get("columns") == list(spec.endpoint_columns),
            f"assay {aid}: the declared endpoint columns are not the frozen ones",
        )
        _require(
            block.get("units") == list(spec.endpoint_units),
            f"assay {aid}: the declared endpoint units are not the frozen ones",
        )

    structure = protocol.get("replicate_structure")
    _require(
        isinstance(structure, dict),
        "the protocol must declare the replicate structure of every assay",
    )
    assert isinstance(structure, dict)
    per_assay_structure = structure.get("per_assay")
    _require(
        isinstance(per_assay_structure, dict),
        "the replicate structure must declare every assay",
    )
    assert isinstance(per_assay_structure, dict)
    for aid in DECLARED_ASSAYS:
        spec = ASSAYS[aid]
        block = per_assay_structure.get(str(aid))
        _require(isinstance(block, dict), f"assay {aid} has no replicate structure block")
        assert isinstance(block, dict)
        _require(
            block.get("recorded_column") == spec.determination_column,
            f"assay {aid}: the declared recorded column is not the frozen one",
        )
        _require(
            block.get("recorded_kind") == spec.determination_kind,
            f"assay {aid}: the declared recorded kind is not the frozen one",
        )
        _require(
            block.get("archived_declaration") == spec.replicate_declaration,
            f"assay {aid}: the declared replicate statement is not the frozen one",
        )
        _require(
            block.get("hill_fit_mode") in HILL_FIT_MODES,
            f"assay {aid}: the declared hill fit mode is not a known mode",
        )
        _require(
            block.get("hill_fit_mode") == spec.hill_fit_mode,
            f"assay {aid}: the declared hill fit mode is not the frozen one",
        )

    controls = protocol.get("control_contract")
    _require(isinstance(controls, dict), "the protocol must declare a control contract")
    assert isinstance(controls, dict)
    keyword_lists = controls.get("keyword_lists")
    _require(isinstance(keyword_lists, dict), "the control contract must declare its keyword lists")
    assert isinstance(keyword_lists, dict)
    _require(
        keyword_lists.get("control_keywords") == list(CONTROL_KEYWORDS),
        "the declared control keyword list is not the frozen one",
    )
    _require(
        keyword_lists.get("ambiguous_words") == list(AMBIGUOUS_CONTROL_WORDS),
        "the declared ambiguous word list is not the frozen one",
    )
    _require(
        keyword_lists.get("reference_keywords") == list(REFERENCE_KEYWORDS),
        "the declared reference keyword list is not the frozen one",
    )
    per_assay = controls.get("per_assay")
    _require(isinstance(per_assay, dict), "the control contract must declare every assay")
    assert isinstance(per_assay, dict)
    for aid in DECLARED_ASSAYS:
        spec = ASSAYS[aid]
        block = per_assay.get(str(aid))
        _require(isinstance(block, dict), f"assay {aid} has no control block")
        assert isinstance(block, dict)
        _require(
            block.get("regime") in CONTROL_REGIMES,
            f"assay {aid}: the declared control regime is not a known regime",
        )
        _require(
            block.get("regime") == spec.control_regime,
            f"assay {aid}: the declared control regime is not the frozen one",
        )
        _require(
            block.get("normalisation_equation") in NORMALISATION_EQUATIONS,
            f"assay {aid}: the declared normalisation equation is not a known equation",
        )
        _require(
            block.get("normalisation_equation") == spec.normalisation_equation,
            f"assay {aid}: the declared normalisation equation is not the frozen one",
        )
        _require(
            block.get("references_expected")
            == EXPECTED_REFERENCES[spec.control_regime],
            f"assay {aid}: the declared number of reference wells is not the frozen one",
        )

    equation_check = protocol.get("equation_scale_check")
    _require(
        isinstance(equation_check, dict),
        "the protocol must declare the check it runs on the archived normalisation equation",
    )
    assert isinstance(equation_check, dict)
    _require(
        equation_check.get("band_points") == EQUATION_SCALE_BAND_POINTS,
        "the declared equation-scale band is not the frozen one",
    )
    _require(
        equation_check.get("fraction_inside_required") == EQUATION_SCALE_FRACTION,
        "the declared equation-scale fraction is not the frozen one",
    )

    split = protocol.get("split")
    _require(isinstance(split, dict), "the protocol must declare a split")
    assert isinstance(split, dict)
    _require(split.get("rule") == SPLIT_RULE, "the declared split rule is not the frozen one")
    _require(split.get("seed") == SPLIT_SEED, "the declared split seed is not the frozen one")
    _require(
        split.get("grouping_unit")
        == "PubChem compound identifier (CID), across the whole declared set",
        "the split must be held out by compound, across the whole declared set",
    )

    _require(protocol.get("seed") == SPLIT_SEED, "the protocol seed is not the frozen one")

    preprocessing = protocol.get("preprocessing")
    _require(isinstance(preprocessing, dict), "the protocol must declare its preprocessing")
    assert isinstance(preprocessing, dict)
    _require(
        isinstance(preprocessing.get("fit_scope"), str) and preprocessing["fit_scope"].strip(),
        "the protocol must declare the scope of every fit it performs",
    )
    _require(
        preprocessing.get("fit_scope_uses_only_own_compound_points") is True,
        "the protocol must state that a fit uses only the archived points of its own compound",
    )

    baselines = protocol.get("baselines")
    _require(
        isinstance(baselines, list) and len(baselines) > 0,
        "the protocol must declare the cheap baseline that comes before any comparison",
    )
    metrics = protocol.get("metrics")
    _require(
        isinstance(metrics, list) and len(metrics) > 0,
        "the protocol must declare the metrics it reports",
    )
    _require(
        protocol.get("curve_tolerance_points") == CURVE_TOLERANCE_POINTS,
        "the declared curve tolerance is not the frozen one",
    )

    run_basis = protocol.get("run_basis")
    _require(
        isinstance(run_basis, dict),
        "the protocol must declare the basis of the runnable task",
    )
    assert isinstance(run_basis, dict)
    _require(
        run_basis.get("fits_a_predictive_model") is False,
        "the runnable task must declare that it fits no predictive model",
    )
    _require(
        isinstance(run_basis.get("description"), str) and run_basis["description"].strip(),
        "the runnable task must describe what it does",
    )


def run_pipeline(
    project_root: Path,
    *,
    cache_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Validate the contract, read the cache and write the descriptive result.

    The results directory is created only after the contract has passed and
    the cache has been read, so a refused contract leaves nothing behind.
    """
    protocol = load_protocol(project_root)
    validate_protocol_contract(protocol)
    resolved_cache = cache_dir or (project_root / ".cache/assay_endpoint_controls")
    resolved_output = output_dir or (project_root / "labs/assay_endpoint_controls/results")
    datasets = load_cached_assays(resolved_cache)
    profiles = {aid: assay_profile(datasets[aid], seed=SPLIT_SEED) for aid in DECLARED_ASSAYS}
    result: dict[str, Any] = {
        "protocol_id": PROTOCOL_ID,
        "assays": {
            str(aid): {
                "name": profiles[aid].name,
                "admitted_compounds": profiles[aid].admitted_compounds,
                "relation_mix": dict(profiles[aid].relation_mix.counts),
                "control_regime": profiles[aid].reference_audit.declared_regime,
                "references_declared": profiles[aid].reference_audit.references_declared,
                "curve_check_mode": profiles[aid].curve_check.mode,
            }
            for aid in DECLARED_ASSAYS
        },
        "split_counts": split_counts(datasets, seed=SPLIT_SEED),
        "split_stability": split_stability(datasets, seed=SPLIT_SEED),
    }
    resolved_output.mkdir(parents=True, exist_ok=True)
    (resolved_output / "report.json").write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


__all__ = [
    "DataContractError",
    "ProtocolContractError",
    "load_protocol",
    "run_pipeline",
    "validate_protocol_contract",
]
