from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.freesolv.data import MoleculeRecord
from aidd_commons.freesolv.models import FitTrace
from aidd_commons.freesolv.pipeline import (
    PretestValidationError,
    validate_model_pretest,
    validate_split_pretest,
)
from aidd_commons.freesolv.splits import SplitMembership, SplitTargets


def source_records() -> tuple[MoleculeRecord, ...]:
    return (
        MoleculeRecord("mobley_1", "CCO", "CCO", -1.0),
        MoleculeRecord("mobley_2", "CCN", "CCN", -2.0),
        MoleculeRecord("mobley_3", "CCC", "CCC", -3.0),
    )


def valid_membership(split_kind: str = "random") -> SplitMembership:
    return SplitMembership(
        split_kind=split_kind,  # type: ignore[arg-type]
        targets=SplitTargets(train=1, validation=1, test=1),
        train_ids=("CCO",),
        validation_ids=("CCN",),
        test_ids=("CCC",),
        grouping_keys={"CCO": "acyclic:CCO", "CCN": "acyclic:CCN", "CCC": "acyclic:CCC"},
    )


def valid_trace() -> FitTrace:
    return FitTrace(
        model_fit_ids={
            "train_mean": ("CCO",),
            "morgan_ridge": ("CCO",),
            "morgan_random_forest": ("CCO",),
        },
        feature_fit_ids=("CCO",),
    )


def test_pretest_validators_accept_frozen_train_and_validation_artifacts() -> None:
    validate_split_pretest(source_records(), valid_membership())
    validate_split_pretest(source_records(), valid_membership("scaffold"))
    validate_model_pretest(
        train_ids=("CCO",),
        fit_trace=valid_trace(),
        validation_predictions={
            "train_mean": np.array([-1.5]),
            "morgan_ridge": np.array([-1.2]),
            "morgan_random_forest": np.array([-1.1]),
        },
        conformal_radii={"morgan_ridge": 0.8, "morgan_random_forest": 0.7},
    )


def test_split_pretest_rejects_canonical_overlap() -> None:
    membership = SplitMembership(
        split_kind="random",
        targets=SplitTargets(train=1, validation=1, test=1),
        train_ids=("CCO",),
        validation_ids=("CCO",),
        test_ids=("CCC",),
        grouping_keys={"CCO": "acyclic:CCO", "CCC": "acyclic:CCC"},
    )

    with pytest.raises(PretestValidationError, match="canonical"):
        validate_split_pretest(source_records(), membership)


def test_split_pretest_rejects_scaffold_leakage() -> None:
    membership = SplitMembership(
        split_kind="scaffold",
        targets=SplitTargets(train=1, validation=1, test=1),
        train_ids=("CCO",),
        validation_ids=("CCN",),
        test_ids=("CCC",),
        grouping_keys={"CCO": "shared", "CCN": "shared", "CCC": "third"},
    )

    with pytest.raises(PretestValidationError, match="grouping key"):
        validate_split_pretest(source_records(), membership)


@pytest.mark.parametrize(
    ("trace", "predictions", "radii", "error"),
    [
        (
            FitTrace(
                model_fit_ids={"morgan_ridge": ("CCO", "CCN")},
                feature_fit_ids=("CCO", "CCN"),
            ),
            {"morgan_ridge": np.array([-1.0])},
            {"morgan_ridge": 0.5, "morgan_random_forest": 0.5},
            "outside train",
        ),
        (
            valid_trace(),
            {
                "train_mean": np.array([-1.0]),
                "morgan_ridge": np.array([np.nan]),
                "morgan_random_forest": np.array([-1.0]),
            },
            {"morgan_ridge": 0.5, "morgan_random_forest": 0.5},
            "non-finite",
        ),
        (
            valid_trace(),
            {
                "train_mean": np.array([-1.0]),
                "morgan_ridge": np.array([-1.0]),
                "morgan_random_forest": np.array([-1.0]),
            },
            {"morgan_ridge": np.nan, "morgan_random_forest": 0.5},
            "non-finite",
        ),
    ],
)
def test_model_pretest_rejects_each_bad_mutation(
    trace: FitTrace,
    predictions: dict[str, np.ndarray],
    radii: dict[str, float],
    error: str,
) -> None:
    with pytest.raises(PretestValidationError, match=error):
        validate_model_pretest(
            train_ids=("CCO",),
            fit_trace=trace,
            validation_predictions=predictions,
            conformal_radii=radii,
        )
