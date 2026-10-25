"""Export the existing completed uncertainty aggregate only; never execute or repeat it."""

import json
from pathlib import Path

from aidd_commons.pool_budget_uncertainty_summary import build_public_uncertainty_summary


def main() -> None:
    lab = Path(__file__).resolve().parent
    source = lab / "uncertainty-results/uncertainty-locked-metrics.json"
    target = lab / "uncertainty-summary.json"
    if source.is_symlink() or target.is_symlink():
        raise ValueError("summary input and output must not be symlinks")
    summary = build_public_uncertainty_summary(json.loads(source.read_text(encoding="utf-8")))
    if target.exists():
        if json.loads(target.read_text(encoding="utf-8")) != summary:
            raise ValueError(
                "existing public summary differs; review the discrepancy before replacing it"
            )
    else:
        with target.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print("Verified aggregate-only uncertainty-summary.json; no campaign executed.")


if __name__ == "__main__":
    main()
