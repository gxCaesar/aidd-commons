from __future__ import annotations

import re
from pathlib import Path


def test_environment_record_is_exact_public_safe_and_linked_to_uv_constraints() -> None:
    repository_root = Path(__file__).parents[3]
    record = (repository_root / "labs" / "freesolv" / "environment.txt").read_text(encoding="utf-8")

    for version in (
        "Python 3.11.15",
        "numpy 2.4.6",
        "pandas 2.3.3",
        "rdkit 2025.09.6",
        "scikit-learn 1.9.0",
        "nbclient 0.11.0",
        "nbformat 5.11.1",
    ):
        assert version in record
    assert "pyproject.toml" in record
    assert "uv" in record
    assert "/Users/" not in record
    assert "checksum" not in record.lower()
    assert "integrity" not in record.lower()


def test_readme_directs_readers_to_the_result_notebook_and_environment_record() -> None:
    repository_root = Path(__file__).parents[3]
    readme = (repository_root / "labs" / "freesolv" / "README.md").read_text(encoding="utf-8")

    assert "freesolv_honest_baselines.ipynb" in readme
    assert "environment.txt" in readme
    assert "reviewed-results.json" in readme
    assert "aggregate-only public summary" in readme
    assert re.search(r"reads\s+that\s+reviewed\s+summary", readme)
