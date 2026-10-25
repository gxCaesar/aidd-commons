"""Run both teaching editions offline and reject an altered real evidence chunk."""

import ast
import asyncio
import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

import nbformat
import pytest
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

LAB = Path(__file__).parents[1] / "paperqa_local"
CONTROL = Path(__file__).parents[2] / "tmp/paperqa-control"


def notebook(language):
    suffix = ".zh-CN" if language == "zh" else ""
    path = LAB / f"paperqa_local_tutorial{suffix}.ipynb"
    assert path.is_file(), "PaperQA teaching notebook is not implemented"
    return nbformat.read(path, as_version=4)


def test_editions_share_clean_executable_cells():
    english, chinese = notebook("en"), notebook("zh")
    for book in (english, chinese):
        nbformat.validate(book)
        assert all(not cell.get("outputs") for cell in book.cells)
        assert all(cell.get("execution_count") is None for cell in book.cells)
    assert [c.source for c in english.cells if c.cell_type == "code"] == [
        c.source for c in chinese.cells if c.cell_type == "code"
    ]


@pytest.mark.parametrize("language", ["en", "zh"])
def test_default_notebook_reads_real_answers_without_network(tmp_path, monkeypatch, language):
    monkeypatch.setenv("IPYTHONDIR", str(tmp_path / "ipython"))
    book = notebook(language)
    # Deny Python socket operations after the kernel exists; the default lesson
    # must not contact Ollama, download assets or make a paid service call.
    book.cells.insert(
        0,
        nbformat.v4.new_code_cell(
            "import sys\n"
            "def deny_network(event, args):\n"
            "    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:\n"
            "        raise RuntimeError('Unexpected network access in offline lesson')\n"
            "sys.addaudithook(deny_network)"
        ),
    )
    NotebookClient(book, timeout=120, kernel_name="python3").execute(cwd=str(tmp_path))
    paths = list(tmp_path.glob("paperqa-student-*/student_report.json"))
    assert len(paths) == 1
    report = json.loads(paths[0].read_text())
    assert report["mode"] == "read_saved_answers"
    assert report["saved_answer_count"] == 5
    assert report["source_copy_check"] == "passed"
    assert report["invented_chunk_rejected"] is True
    assert report["new_inference_performed"] is False


def test_invented_real_answer_context_fails_source_check(tmp_path, monkeypatch):
    monkeypatch.setenv("IPYTHONDIR", str(tmp_path / "ipython"))
    book = notebook("en")
    cell = next(c for c in book.cells if "saved-example" in c.metadata.get("tags", []))
    cell.source += (
        "\nobserved['answers'][0]['contexts'][0]['source_text'] = "
        "'This invented evidence does not appear in either supplied paper.'"
    )
    with pytest.raises(CellExecutionError, match="Source text is not present"):
        NotebookClient(book, timeout=120, kernel_name="python3").execute(cwd=str(tmp_path))


@pytest.mark.parametrize("stage", ["settings", "index", "answer"])
def test_live_cell_preserves_sdk_error_without_calling_a_model(tmp_path, monkeypatch, stage):
    monkeypatch.chdir(tmp_path)
    book = notebook("en")
    namespace = {}
    setup = next(c for c in book.cells if c.id == "setup-code")
    exec(setup.source, namespace)

    async def failing_sdk(*args, **kwargs):
        raise RuntimeError("controlled SDK failure")

    def failing_version(*args, **kwargs):
        raise RuntimeError("controlled SDK failure")

    if stage == "settings":
        monkeypatch.setattr(namespace["importlib"].metadata, "version", failing_version)

    namespace.update(
        ENABLE_LOCAL_INFERENCE=True,
        observed=json.loads((LAB / "reviewed-example.json").read_text()),
        local_docs=SimpleNamespace(aadd=failing_sdk, aquery=failing_sdk),
        local_network_events=[],
        settings=object(),
        llm=object(),
        summary_llm=object(),
        embedding=object(),
    )
    cell = next(c for c in book.cells if c.id == f"local-{stage}-code")
    compiled = compile(
        cell.source, "notebook-live-cell", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
    )
    with pytest.raises(RuntimeError, match="controlled SDK failure"):
        result = eval(compiled, namespace)
        if result is not None:
            asyncio.run(result)
    folder = namespace["OUTPUT_DIR"]
    report = json.loads((folder / "student_execution.json").read_text())
    assert report["outcome"] == "failed"
    assert report["error"] == "RuntimeError: controlled SDK failure"
    assert json.loads((folder / "student_local_answers.json").read_text()) == []
    assert json.loads((folder / "student_network_events.json").read_text()) == []
    if stage == "index":
        assert (folder / "openbabel-2011.txt").is_file()


def cell_source(book, cell_id):
    return next(cell for cell in book.cells if cell.id == cell_id).source


def function_source(text, name):
    """Return one top-level definition from a notebook cell, without importing it."""
    match = re.search(rf"^def {name}\(.*?(?=^\S|\Z)", text, re.M | re.S)
    assert match, f"{name} is not defined in this cell"
    return match.group(0)


def example_settings():
    return json.loads((LAB / "reviewed-example.json").read_text())["effective_settings"]


@pytest.fixture
def live_notebook(tmp_path, monkeypatch):
    """Execute the setup cell and the visible helpers of the settings cell."""
    monkeypatch.chdir(tmp_path)
    book = notebook("en")
    namespace = {}
    exec(cell_source(book, "setup-code"), namespace)
    exec(cell_source(book, "local-settings-code").split("if ENABLE_LOCAL_INFERENCE:")[0], namespace)
    return book, namespace


def test_runtime_profiles_change_only_transport_limits(live_notebook):
    _, namespace = live_notebook
    effective = example_settings()
    apply_budget, budget = namespace["apply_runtime_budget"], namespace["runtime_budget"]

    assert apply_budget(effective, budget("as-observed")) == effective
    extended = apply_budget(effective, budget("cpu-extended"))
    assert extended != effective
    assert namespace["scientific_settings"](extended) == namespace["scientific_settings"](effective)
    chat = extended["llm_config"]["model_list"][0]["litellm_params"]
    assert (chat["num_thread"], chat["timeout"], chat["max_retries"]) == (4, 900, 0)
    assert extended["embedding_config"]["kwargs"] == {"timeout": 600, "num_retries": 0}
    assert extended["embedding_config"]["router_kwargs"] == {"timeout": 600, "num_retries": 0}
    assert extended["answer"]["evidence_k"] == effective["answer"]["evidence_k"] == 4
    assert extended["llm"] == effective["llm"]
    with pytest.raises(ValueError, match="Unknown execution profile"):
        budget("cpu-fast")


def test_cpu_profile_matches_the_accepted_execution_copy(live_notebook):
    """The published profile must equal the settings of the one accepted CPU run."""
    copied = CONTROL / "20260910-paperqa-notebook-cpu-r2/notebook"
    if not copied.is_dir():
        pytest.skip("the private execution-copy evidence is not present in this tree")
    _, namespace = live_notebook
    executed = json.loads((copied / "input.ipynb").read_text())
    source = next(
        "".join(cell["source"])
        for cell in executed["cells"]
        if cell["cell_type"] == "code" and "def bounded_cpu_settings" in "".join(cell["source"])
    )
    reference = {"copy": copy}
    exec(function_source(source, "bounded_cpu_settings"), reference)
    effective = example_settings()
    applied = namespace["apply_runtime_budget"](
        effective, namespace["runtime_budget"]("cpu-extended")
    )
    assert applied == reference["bounded_cpu_settings"](effective)

    overrides = json.loads((copied / "runtime-overrides.json").read_text())
    budget = namespace["runtime_budget"]("cpu-extended")
    assert budget["num_thread"] == overrides["cpu_threads"]
    assert budget["chat_timeout"] == overrides["chat_timeout_seconds"]
    assert budget["max_retries"] == overrides["sdk_retries"]
    assert budget["embedding_timeout"] == overrides["embedding_config_timeout_seconds"]
    assert budget["document_timeout"] == overrides["document_timeout_seconds"]
    assert budget["question_timeout"] == overrides["question_timeout_seconds"]
    assert overrides["scientific_settings_changed"] is False


def test_a_profile_that_moves_a_scientific_field_is_rejected(live_notebook):
    """Known-bad edit: a profile that also retunes generation must be refused."""
    book, namespace = live_notebook
    source = function_source(
        cell_source(book, "local-settings-code"), "apply_runtime_budget"
    ).replace(
        'max_retries=budget["max_retries"],',
        'max_retries=budget["max_retries"], temperature=0.7,',
    )
    assert "temperature=0.7" in source
    broken = dict(namespace)
    exec(source, broken)
    with pytest.raises(ValueError, match="must not change model, retrieval or answer settings"):
        broken["apply_runtime_budget"](
            example_settings(), namespace["runtime_budget"]("cpu-extended")
        )


@pytest.mark.parametrize(
    ("profile", "document_timeout", "question_timeout"),
    [("as-observed", 150, 600), ("cpu-extended", 600, 2400)],
)
def test_live_cells_take_their_limits_from_the_selected_profile(
    live_notebook, profile, document_timeout, question_timeout
):
    book, namespace = live_notebook
    recorded = []

    async def wait_for(awaitable, timeout):
        recorded.append(timeout)
        return await awaitable

    async def aadd(*args, **kwargs):
        return "indexed"

    async def aquery(*args, **kwargs):
        return SimpleNamespace(answer="", references="", contexts=[])

    namespace.update(
        ENABLE_LOCAL_INFERENCE=True,
        EXECUTION_PROFILE=profile,
        observed=json.loads((LAB / "reviewed-example.json").read_text()),
        asyncio=SimpleNamespace(wait_for=wait_for),
        local_docs=SimpleNamespace(aadd=aadd, aquery=aquery),
        local_network_events=[],
        settings=object(),
        llm=object(),
        summary_llm=object(),
        embedding=object(),
        display=lambda value: None,
    )
    for cell_id in ("local-index-code", "local-answer-code"):
        compiled = compile(
            cell_source(book, cell_id), cell_id, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
        )
        result = eval(compiled, namespace)
        if result is not None:
            asyncio.run(result)
    assert recorded == [document_timeout, document_timeout, question_timeout]
    report = json.loads((namespace["OUTPUT_DIR"] / "student_execution.json").read_text())
    assert report["outcome"] == "stage_finished"
