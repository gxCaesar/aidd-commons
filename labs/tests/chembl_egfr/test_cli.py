from __future__ import annotations

import importlib.util
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).parents[3]
CLI_PATH = REPOSITORY_ROOT / "labs" / "chembl_egfr" / "run_lab.py"


def load_cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("chembl_egfr_run_lab", CLI_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load ChEMBL EGFR lab CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unconfirmed_locked_cli_refuses_before_loading_any_dataset(monkeypatch, capsys) -> None:
    cli = load_cli()

    def forbidden_load(*args, **kwargs):
        pytest.fail("unconfirmed command reached the real-data loader")

    monkeypatch.setattr(cli, "load_cached_frozen_datasets", forbidden_load)
    assert cli.main(["evaluate-locked"]) == 2
    assert "explicit confirmation" in capsys.readouterr().err


def test_cli_exposes_download_pretest_and_one_paired_locked_command() -> None:
    cli = load_cli()

    assert cli.parse_args(["download"]).action == "download"
    assert cli.parse_args(["pretest"]).action == "pretest"
    locked = cli.parse_args(["evaluate-locked", "--confirm-locked-evaluation"])
    assert locked.action == "evaluate-locked"
    assert locked.confirm_locked_evaluation is True

    generated_command = cli.portable_locked_evaluation_command(
        cli.REPOSITORY_ROOT / ".cache" / "chembl_egfr",
        cli.REPOSITORY_ROOT,
    )
    generated_tokens = shlex.split(generated_command)
    action_tokens = generated_tokens[generated_tokens.index("evaluate-locked") :]
    generated = cli.parse_args(action_tokens)
    assert generated.action == "evaluate-locked"
    assert not hasattr(generated, "output_dir")

    with pytest.raises(SystemExit):
        cli.parse_args(
            [
                "evaluate-locked",
                "--output-dir",
                "labs/chembl_egfr/alternate-results",
                "--confirm-locked-evaluation",
            ]
        )

    completed = subprocess.run(
        [sys.executable, str(CLI_PATH), "--help"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "download" in completed.stdout
    assert "pretest" in completed.stdout
    assert "evaluate-locked" in completed.stdout
    assert "evaluate-primary" not in completed.stdout
    assert "evaluate-replication" not in completed.stdout
