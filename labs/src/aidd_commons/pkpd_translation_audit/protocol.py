"""Frozen contract for an illustrative PK/PD translation over ChEMBL clearance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

PROTOCOL_ID = "chembl37-pkpd-translation-audit-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.pkpd-translation-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.pkpd-translation-summary.v1"
HUMAN = "CHEMBL3301372"
RAT = "CHEMBL3301371"
MICROSOME = "CHEMBL3301370"
HEPATOCYTE_UNIT = "uL.min-1.(10^6cells)-1"
MICROSOME_UNIT = "mL.min-1.g-1"
BOUNDARY = (
    "Only intrinsic clearance is measured. Concentration, target occupancy and effect are "
    "illustrative model outputs under declared, unmeasured parameters. The within-cohort "
    "rat-to-human hepatocyte ratio interval is not validated species translation, and no "
    "clinical response or compound ranking follows."
)


class ProtocolError(ValueError):
    """The supplied protocol is not the frozen model contract."""


def _parameter(value: float, unit: str, source: str) -> dict[str, float | str]:
    return {"value": value, "unit": unit, "source": source}


def expected_protocol() -> dict[str, Any]:
    assumed = "Project assumption for an illustrative one-compartment calculation"
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": "2026-10-23",
        "source": {
            "database": "ChEMBL_37",
            "release_date": "2026-05-01",
            "document_chembl_id": "CHEMBL3301361",
            "document_doi": "10.6019/CHEMBL3301361",
            "assays": {
                MICROSOME: "Human liver microsomes",
                RAT: "Rat hepatocytes",
                HUMAN: "Human hepatocytes",
            },
            "snapshot_files_bytes": {
                "activities-CHEMBL3301370.json": 701737,
                "activities-CHEMBL3301371.json": 549808,
                "activities-CHEMBL3301372.json": 266453,
                "status.json": 231,
            },
            "snapshot_bytes": 1518229,
            "licence": "Creative Commons Attribution-ShareAlike 3.0 Unported",
            "licence_source": "ChEMBL 37 release LICENSE and README, reviewed 2026-10-21",
            "licence_scope": (
                "ChEMBL data records. An individual deposited document retains its owner's rights"
            ),
            "read_route": (
                "Cached ChEMBL REST snapshot at .cache/az_clearance_system, read and validated "
                "by aidd_commons.az_clearance_system.data.load_cached_systems"
            ),
            "snapshot_fetched_on": "2026-09-12",
        },
        "counted_unit": {
            "unit": "one admitted ChEMBL parent molecule",
            "measurements": (
                "The parent median of exact, uncensored intrinsic-clearance activities admitted "
                "by the frozen AZ clearance-system reader in each named assay"
            ),
            "modelled_if": "admitted in both human and rat hepatocyte assays",
            "excluded_from_conversion": (
                "Microsome clearance is per gram protein, not per million cells"
            ),
        },
        "model": {
            "measured_inputs": {
                "rat_hepatocyte_clearance": {
                    "value": "per admitted parent",
                    "unit": HEPATOCYTE_UNIT,
                    "source": (
                        "ChEMBL 37 assay CHEMBL3301371, admitted by the frozen "
                        "az_clearance_system reader"
                    ),
                },
                "human_hepatocyte_clearance": {
                    "value": "per admitted parent, used for peer factors and comparison",
                    "unit": HEPATOCYTE_UNIT,
                    "source": (
                        "ChEMBL 37 assay CHEMBL3301372, admitted by the frozen "
                        "az_clearance_system reader"
                    ),
                },
            },
            "derived_input": {
                "species_factor": {
                    "value": "per-parent leave-one-out median with empirical quantile bounds",
                    "unit": "dimensionless human-to-rat hepatocyte clearance ratio",
                    "source": "paired parent clearances from the two ChEMBL 37 hepatocyte assays",
                }
            },
            "equations": [
                "r_i = median(CL_h/CL_r among paired parents except i)",
                "CL_h,model = CL_r * r_i * N_cells * 60 / 10^12 L/h",
                "C_total(t) = (D/V) * exp(-CL_h,model * t/V)",
                "C_free(t) = f_u * C_total(t)",
                "occupancy(t) = C_free(t)/(K_d + C_free(t))",
                "effect(t) = E_max * occupancy(t) * (1 + EC50_occupancy) / "
                "(EC50_occupancy + occupancy(t))",
            ],
            "translation_rule": (
                "For each paired parent, derive a rat-to-human hepatocyte clearance factor "
                "from the other paired parents. Use their median for the central curve and "
                "their empirical quantiles for a variability interval. Never use the "
                "parent's own human measurement to derive its factor."
            ),
            "uncertainty_rule": (
                "Interval arithmetic propagates assumed rat-assay uncertainty, leave-one-out "
                "species-factor variability, unbound fraction, binding constant, Emax and "
                "engagement EC50 through each monotone equation. These are sensitivity bounds, "
                "not confidence or prediction intervals."
            ),
            "parameters": {
                "dose_umol": _parameter(1.0, "umol", assumed + ", instantaneous input"),
                "volume_l": _parameter(1.0, "L", assumed + ", apparent volume"),
                "interval_h": _parameter(24.0, "h", assumed + ", evaluation after one interval"),
                "effective_cells": _parameter(
                    100000000.0, "cells", assumed + ", not a physiological liver count"
                ),
                "rat_clearance_relative_error": _parameter(
                    0.2, "fraction", assumed + ", no assay error estimate is supplied"
                ),
                "translation_lower_quantile": _parameter(
                    0.1, "fraction", "Project decision for leave-one-out paired-ratio distribution"
                ),
                "translation_upper_quantile": _parameter(
                    0.9, "fraction", "Project decision for leave-one-out paired-ratio distribution"
                ),
                "fu": _parameter(0.1, "fraction", assumed + ", unmeasured plasma binding"),
                "fu_lower": _parameter(0.05, "fraction", assumed + ", sensitivity bound"),
                "fu_upper": _parameter(0.2, "fraction", assumed + ", sensitivity bound"),
                "kd_umol_l": _parameter(
                    0.2, "umol/L", assumed + ", unmeasured target binding constant"
                ),
                "kd_lower_umol_l": _parameter(0.1, "umol/L", assumed + ", sensitivity bound"),
                "kd_upper_umol_l": _parameter(0.4, "umol/L", assumed + ", sensitivity bound"),
                "emax": _parameter(
                    1.0, "fractional effect increment", assumed + ", unmeasured response scale"
                ),
                "emax_lower": _parameter(
                    0.5, "fractional effect increment", assumed + ", sensitivity bound"
                ),
                "emax_upper": _parameter(
                    1.0, "fractional effect increment", assumed + ", sensitivity bound"
                ),
                "ec50_occupancy": _parameter(
                    0.5, "occupied fraction", assumed + ", unmeasured response coupling"
                ),
                "ec50_occupancy_lower": _parameter(
                    0.25, "occupied fraction", assumed + ", sensitivity bound"
                ),
                "ec50_occupancy_upper": _parameter(
                    0.75, "occupied fraction", assumed + ", sensitivity bound"
                ),
            },
        },
        "excluded_by_design": [
            "a prediction of clinical exposure, efficacy or response",
            "an assertion that target engagement or response was measured",
            "a claim that rat-to-human species translation was externally validated",
            "a ranking of compounds by predicted response",
            "a silent conversion between microsome per-protein and hepatocyte per-cell clearance",
        ],
        "boundary": BOUNDARY,
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError(f"cannot read protocol: {error}") from error
    if document != expected_protocol():
        raise ProtocolError("protocol differs from the frozen contract")
    return cast(dict[str, Any], document)
