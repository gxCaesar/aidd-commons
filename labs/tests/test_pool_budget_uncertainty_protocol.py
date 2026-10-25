"""Cross-artifact consistency only: no campaign is executed here."""

import json
from pathlib import Path


def test_uncertainty_protocol_inherits_the_same_partition_and_model_as_the_real_campaign():
    labs = Path(__file__).parents[1]
    protocol = json.loads((labs / "pool_budget" / "uncertainty-protocol.json").read_text())
    frozen = json.loads((labs / "pool_budget" / "real-protocol.json").read_text())

    assert protocol["frozen_reference"]["protocol_id"] == frozen["protocol_id"]
    assert protocol["frozen_reference"]["path"] == "labs/pool_budget/real-protocol.json"
    # The new policy must not point its output at the completed campaign's directory.
    assert protocol["output_contract"]["directory"] != "labs/pool_budget/results/"
    assert "uncertainty" in protocol["output_contract"]["directory"]
    # The runner's own model params must match the frozen contract's, byte for byte,
    # so this test fails if either the protocol prose or the runner code drifts.
    from aidd_commons.pool_budget_uncertainty import RIDGE_PARAMS

    frozen_model = frozen["prediction_contract"]["model"]
    assert RIDGE_PARAMS == {
        "alpha": frozen_model["alpha"],
        "fit_intercept": frozen_model["fit_intercept"],
        "solver": frozen_model["solver"],
        "tol": frozen_model["tol"],
        "max_iter": frozen_model["max_iter"],
    }


def test_new_output_files_are_committed_separately_from_the_completed_campaign():
    labs = Path(__file__).parents[1]
    assert (labs / "pool_budget" / "uncertainty-protocol.json").is_file()
    assert (labs / "pool_budget" / "uncertainty-summary.json").is_file()
    # uncertainty-results/ is local execution state (gitignored); only assert that
    # if it exists locally, it never collides with the completed campaign's own.
    local = labs / "pool_budget" / "uncertainty-results"
    if local.exists():
        assert local != labs / "pool_budget" / "results"
        assert not any(local.glob("locked-*.json"))
