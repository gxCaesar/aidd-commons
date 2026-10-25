from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_lab_cli_exposes_separate_pretest_and_one_time_test_commands() -> None:
    repository_root = Path(__file__).parents[3]
    result = subprocess.run(
        [sys.executable, str(repository_root / "labs" / "freesolv" / "run_lab.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "pretest" in result.stdout
    assert "evaluate-test" in result.stdout
