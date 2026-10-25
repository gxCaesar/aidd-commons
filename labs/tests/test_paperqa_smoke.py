"""Test corpus intake, reference separation and fail-closed network policy."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "labs/paperqa_local/run_smoke.py"


def module():
    spec = importlib.util.spec_from_file_location("paperqa_smoke", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def article(license_url="http://creativecommons.org/licenses/by/2.0/"):
    return f'''<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta>
    <article-id pub-id-type="pmc">3198950</article-id>
    <title-group><article-title>Open Babel: An open chemical toolbox</article-title></title-group>
    <permissions><license><ext-link xlink:href="{license_url}"/></license></permissions>
    <abstract><p>Open Babel interconverts <bold>over 110</bold> formats.</p></abstract>
    </article-meta></front><body><sec><title>Methods</title><p>Conformer searching.</p></sec>
    </body><back><ref-list><ref><p>Unrelated cited abstract.</p></ref></ref-list></back>
    </article>'''


def document():
    return {
        "pmcid": "PMC3198950",
        "title": "Open Babel: An open chemical toolbox",
        "license_url": "https://creativecommons.org/licenses/by/2.0/",
        "citation": "O'Boyle et al. (2011).",
    }


def test_extracts_article_text_without_reference_list_or_duplicate_inline_text():
    text = module().article_text(article(), document())
    assert "Open Babel interconverts over 110 formats." in text
    assert "Methods" in text
    assert "Unrelated cited abstract" not in text
    assert text.count("Conformer searching.") == 1


def test_rejects_noncommercial_license_and_wrong_article():
    with pytest.raises(ValueError, match="license"):
        module().article_text(
            article("https://creativecommons.org/licenses/by-nc/3.0/"), document()
        )
    wrong = document() | {"pmcid": "PMC9999999"}
    with pytest.raises(ValueError, match="identity"):
        module().article_text(article(), wrong)


def test_outgoing_questions_do_not_include_reference_answers():
    questions = [{"id": "q1", "question": "What formats?", "reference_answer": "secret answer"}]
    assert module().inference_questions(questions) == [("q1", "What formats?")]


def test_effective_settings_remain_local_and_have_bounded_generation():
    profile = json.loads((ROOT / "configs/scientific-agents/paperqa-local.json").read_text())
    settings = module().smoke_settings(profile)
    assert settings["llm"] == "ollama_chat/qwen3:8b"
    params = settings["summary_llm_config"]["model_list"][0]["litellm_params"]
    assert params["api_base"] == "http://127.0.0.1:11434"
    assert params["max_tokens"] == 1024
    assert params["think"] is False
    assert settings["answer"]["evidence_k"] == 4
    profile["settings"]["llm"] = "gpt-4o"
    with pytest.raises(ValueError):
        module().smoke_settings(profile)


def test_network_hook_rejects_external_connection_before_connecting():
    # The hook is permanent for its process, so exercise it in a disposable child.
    code = f"""import importlib.util, socket
spec = importlib.util.spec_from_file_location("smoke", {str(SCRIPT)!r})
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
events = []
m.install_network_guard(events)
try:
    socket.create_connection(("198.51.100.1", 443), timeout=0.1)
except PermissionError:
    print("blocked", len(events))
else:
    raise AssertionError("External request escaped")
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "blocked 1" in result.stdout


def test_run_refuses_to_overwrite_existing_outputs_before_importing_sdk(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "run", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_sdk_import_failure_leaves_failed_summary_and_network_record(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for name in ["openbabel-2011", "cmms-gcl-2023"]:
        (data / f"{name}.txt").write_text("Input exists; failure occurs before indexing.")
    output = tmp_path / "result"
    code = f"""import asyncio, builtins, importlib.util
spec = importlib.util.spec_from_file_location("smoke", {str(SCRIPT)!r})
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.importlib.metadata.version = lambda name: "2026.8.12"
original_import = builtins.__import__
def fail_lmi(name, *args, **kwargs):
    if name == "lmi":
        raise ImportError("forced SDK import failure")
    return original_import(name, *args, **kwargs)
builtins.__import__ = fail_lmi
asyncio.run(m.run(m.Path({str(data)!r}), m.Path({str(output)!r})))
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode != 0
    report = json.loads((output / "summary.json").read_text())
    assert report["execution"] == "failed"
    assert report["question_count"] == 0
    assert "forced SDK import failure" in report["error"]
    assert json.loads((output / "network-events.json").read_text()) == []
