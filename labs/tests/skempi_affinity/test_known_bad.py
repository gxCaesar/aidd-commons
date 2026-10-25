"""Named frozen-contract edits must fail before cache access or output creation."""

import json
from pathlib import Path

import pytest
from aidd_commons.skempi_affinity import summary
from aidd_commons.skempi_affinity.protocol import ProtocolError

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "labs/skempi_affinity/protocol.json"


@pytest.mark.parametrize(
    "mutation",
    ["source_bytes", "field_alignment", "independent_unit", "secondary_group",
     "endpoint_unit", "seed", "baseline_fit_scope", "split_rule"],
)
def test_known_bad_protocol_edits_rejected_before_results(tmp_path, monkeypatch, mutation):
    protocol = json.loads(SOURCE.read_text())
    if mutation == "source_bytes":
        protocol["source"]["expected_bytes"] += 1
    elif mutation == "field_alignment":
        protocol["alignment"]["rule"] = "Assume fixed width."
    elif mutation == "independent_unit":
        protocol["split"]["independent_unit"] = "row"
    elif mutation == "secondary_group":
        protocol["entity"]["secondary_group"] = "#Pdb"
    elif mutation == "endpoint_unit":
        protocol["endpoint"]["source_unit"] = "nM"
    elif mutation == "seed":
        protocol["seed"] += 1
    elif mutation == "split_rule":
        protocol["split"]["rule"] = "Hold out rows."
    else:
        protocol["baseline"]["fit_scope"] = "Use all complexes."
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol))
    output = tmp_path / "results"

    def forbid_cache(_path):
        raise AssertionError("cache was read before contract validation")

    monkeypatch.setattr(summary, "load_cached", forbid_cache)
    with pytest.raises(ProtocolError):
        summary.build_summary(path, tmp_path / "cache", results_dir=output)
    assert not output.exists()
