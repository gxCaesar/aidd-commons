"""The committed summary has a complete, internally consistent coverage matrix."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.multi_endpoint_tradeoff.protocol import FAMILIES, PROTOCOL_ID
from aidd_commons.multi_endpoint_tradeoff.summary import SummaryContractError, audit_summary

ROOT = Path(__file__).resolve().parents[3]
SUMMARY = json.loads((ROOT / "labs/multi_endpoint_tradeoff/summary.json").read_text())


def test_committed_summary_contract_and_partition() -> None:
    audit_summary(SUMMARY)
    assert SUMMARY["protocol_id"] == PROTOCOL_ID
    assert SUMMARY["computed_on"]
    assert SUMMARY["software"]["python"]
    assert SUMMARY["cohort"] == {"declared_seed_count": 15, "resolved_parent_count": 10}
    assert SUMMARY["admitted_measurement_count"] == 486
    assert (
        sum(SUMMARY["families"][family]["independent_measurement_count"] for family in FAMILIES)
        == 486
    )
    assert len(SUMMARY["compounds_with_empty_family"]) == 10
    assert all("activity_id" not in row for row in SUMMARY["per_compound_coverage"])


@pytest.mark.parametrize("defect", ["partition", "missingness", "spread"])
def test_corrupt_summary_is_refused(defect: str) -> None:
    altered = copy.deepcopy(SUMMARY)
    if defect == "partition":
        altered["families"]["other"]["independent_measurement_count"] += 1
    elif defect == "missingness":
        altered["compounds_with_empty_family"] = []
    else:
        altered["families"]["efficacy"]["interquartile_range"] = 0
    with pytest.raises(SummaryContractError):
        audit_summary(altered)
