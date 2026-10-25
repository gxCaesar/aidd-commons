from __future__ import annotations

import importlib.util
import shlex
from pathlib import Path
from types import ModuleType

import pytest
from aidd_commons.rmd17_system_state.pipeline import portable_locked_evaluation_command

REPOSITORY_ROOT = Path(__file__).parents[3]
CLI_PATH = REPOSITORY_ROOT / "labs" / "rmd17_system_state" / "run_lab.py"


def _load_cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rmd17_system_state_run_lab", CLI_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load the rMD17 system-state CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_has_only_fixed_actions_and_a_portable_confirmed_locked_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _load_cli()

    assert cli.parse_args(["validate-protocol"]).action == "validate-protocol"
    assert cli.parse_args(["download-development"]).action == "download-development"
    assert cli.parse_args(["pretest"]).action == "pretest"
    locked = cli.parse_args(["evaluate-locked", "--confirm-run-locked-evaluation"])
    assert locked.action == "evaluate-locked"
    assert locked.confirm_run_locked_evaluation is True

    command = portable_locked_evaluation_command()
    tokens = shlex.split(command)
    assert not any(token.startswith("/") for token in tokens)
    assert "--output-dir" not in tokens
    action_tokens = tokens[tokens.index("evaluate-locked") :]
    generated = cli.parse_args(action_tokens)
    assert generated.action == "evaluate-locked"
    assert generated.confirm_run_locked_evaluation is True

    assert cli.main(["evaluate-locked"]) == 2
    assert "explicit confirmation" in capsys.readouterr().err

    for forbidden in (
        "--output-dir",
        "--data-dir",
        "--system",
        "--alpha",
        "--split",
        "--summary-path",
    ):
        with pytest.raises(SystemExit):
            cli.parse_args(["pretest", forbidden, "alternate"])
