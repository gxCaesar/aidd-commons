"""Cross-artifact consistency only: no real campaign is executed here."""

import json
from pathlib import Path


def test_real_campaign_source_and_features_do_not_drift_from_t05():
    labs = Path(__file__).parents[1]
    contract = json.loads((labs / "pool_budget" / "real-protocol.json").read_text())
    t05 = json.loads((labs / "chembl_egfr" / "protocol.json").read_text())
    reference = contract["frozen_t05_reference"]
    assert reference["protocol_version"] == t05["protocol_version"]
    assert reference["entity_contract"] == t05["entity"]
    label_contract = reference["label_contract"]
    assert {
        key: value for key, value in label_contract.items() if key != "filters"
    } | label_contract["filters"] == t05["labels"]
    assert {
        assay: replay["expected_parent_count"]
        for assay, replay in reference["assay_replays"].items()
    } == t05["source"]["expected_parent_counts"]
    fingerprint = contract["acquisition_contract"]["policies"]["maxmin"]["fingerprint_reference"]
    for key, value in fingerprint.items():
        if key != "source":
            assert value == t05["representations"]["morgan_ridge"][key]
    model = contract["prediction_contract"]["model"]
    for name in ("solver", "tol", "max_iter"):
        inherited = {
            "solver": "ridge_solver",
            "tol": "ridge_tolerance",
            "max_iter": "ridge_max_iterations",
        }[name]
        assert model[name] == t05["models"][inherited]
    development = json.loads((labs / "chembl_egfr" / "development-summary.json").read_text())
    assert model["alpha"] == development["selection"]["selected_alphas"]["morgan_ridge"]
