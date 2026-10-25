"""Exercise the distributed local-only profile, including unsafe mutations."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/agents/check_local_profile.py"
PROFILE = ROOT / "configs/scientific-agents/paperqa-local.json"


def checker():
    spec = importlib.util.spec_from_file_location("local_profile", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile():
    return json.loads(PROFILE.read_text())


def test_shipped_profile_passes_without_model_dependencies():
    checker().validate_profile(profile())
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(PROFILE)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "inference not run" in result.stdout


@pytest.mark.parametrize(
    "path,value",
    [
        (("settings", "llm"), "gpt-4o"),
        (("settings", "summary_llm"), "gpt-4o-mini"),
        (("settings", "agent", "agent_llm"), "gpt-4o"),
        (("settings", "parsing", "enrichment_llm"), "gpt-4o"),
        (("settings", "embedding"), "text-embedding-3-small"),
        (("settings", "parsing", "use_doc_details"), True),
        (("settings", "parsing", "multimodal"), True),
        (("embedding_ndim",), 1024),
        (("paperqa_version",), "latest"),
        (("settings", "llm"), "ollama/qwen3:cloud"),
    ],
)
def test_rejects_unsafe_or_incompatible_mutations(path, value):
    data = profile()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        checker().validate_profile(data)


@pytest.mark.parametrize("role", ["llm_config", "summary_llm_config", "embedding_config"])
def test_rejects_remote_endpoint_for_each_top_level_role(role):
    data = profile()
    data["settings"][role]["model_list"][0]["litellm_params"]["api_base"] = (
        "https://api.example.com/v1"
    )
    with pytest.raises(ValueError):
        checker().validate_profile(data)


def test_rejects_fallback_and_missing_role():
    data = profile()
    data["settings"]["llm_config"]["fallbacks"] = [{"local": ["remote"]}]
    with pytest.raises(ValueError):
        checker().validate_profile(data)
    data = profile()
    del data["settings"]["summary_llm"]
    with pytest.raises(ValueError):
        checker().validate_profile(data)


def test_cli_failure_does_not_emit_settings(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"settings": {}}')
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(bad), "--settings"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "FAIL" in result.stderr
