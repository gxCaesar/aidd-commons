"""Compute a real trajectory observable and its convergence from committed rMD17 frames.

Reads the two development-role rMD17 files (ethanol, malonaldehyde) already used by
this lab's energy-regression protocol and asks a different question of them: what a
mass-weighted radius of gyration is under the ab initio trajectory, and how much of
the trajectory is needed to estimate it. No structure is prepared and no new
simulation is run; this is inspection of an existing, completed trajectory.

    python labs/rmd17_system_state/inspect_dynamics.py show
    python labs/rmd17_system_state/inspect_dynamics.py check

Needs the two development NPZ files already present at
`labs/rmd17_system_state/data/`. If they are not, first run:

    python labs/rmd17_system_state/run_lab.py download-development

Python 3.11 or newer and NumPy. No network access once the files are present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.rmd17_system_state.data import load_system_npz  # noqa: E402
from aidd_commons.rmd17_system_state.dynamics import (  # noqa: E402
    DynamicsContractError,
    block_standard_error,
    convergence_checkpoints,
    naive_standard_error,
    radius_of_gyration_series,
)
from aidd_commons.rmd17_system_state.protocol import SYSTEMS  # noqa: E402

LAB = Path(__file__).resolve().parent
DATA = LAB / "data"


def load_protocol() -> dict:
    return json.loads((LAB / "observable-protocol.json").read_text(encoding="utf-8"))


def compute(protocol: dict) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for system_id in protocol["systems"]:
        specification = SYSTEMS[system_id]
        path = DATA / specification.filename
        if not path.exists():
            print(
                f"ERROR: {path} is not present. Run "
                "'python labs/rmd17_system_state/run_lab.py download-development' first.",
                file=sys.stderr,
            )
            sys.exit(1)
        record = load_system_npz(path, specification)
        series = radius_of_gyration_series(
            record.coordinates, record.nuclear_charges, record.old_indices
        )
        naive_sem = naive_standard_error(series)
        blocks = {
            size: block_standard_error(series, blocks=size) for size in protocol["block_sizes"]
        }
        checkpoints = convergence_checkpoints(series, tuple(protocol["convergence_checkpoints"]))
        results[system_id] = {
            "frame_count": series.shape[0],
            "series": series,
            "full_mean": float(series.mean()),
            "full_std": float(series.std(ddof=1)),
            "minimum": float(series.min()),
            "maximum": float(series.max()),
            "naive_sem": naive_sem,
            "blocks": blocks,
            "checkpoints": checkpoints,
        }
    return results


def show(protocol: dict, results: dict[str, dict]) -> None:
    print(f"Declared question: {protocol['declared_question']}")
    print("No structure is prepared, protonated or docked, and no new simulation is run.")
    print()
    for system_id, data in results.items():
        print(f"{system_id.upper()}  ({data['frame_count']} frames, chronological order)")
        print(
            f"  Rg  mean={data['full_mean']:.6f} A  std={data['full_std']:.6f} A  "
            f"range=[{data['minimum']:.6f}, {data['maximum']:.6f}] A"
        )
        print(f"  naive (i.i.d.) standard error: {data['naive_sem']:.6f} A")
        print("  block-averaged standard error, by block count:")
        for size, estimate in data["blocks"].items():
            ratio = estimate.block_standard_error / data["naive_sem"]
            print(
                f"    blocks={size:<5} frames/block={estimate.frames_per_block:<7} "
                f"block SEM={estimate.block_standard_error:.6f} A  "
                f"({ratio:.2f}x the naive estimate)"
            )
        print("  cumulative mean vs. frames included (chronological order):")
        for checkpoint in data["checkpoints"]:
            print(
                f"    frames={checkpoint.frames_included:<7} "
                f"mean={checkpoint.cumulative_mean:.6f} A  "
                f"diff from full trajectory={checkpoint.difference_from_full_trajectory:+.6f} A"
            )
        print()
    print("What this does not show, by the frozen protocol's own declaration:")
    for item in protocol["excluded_by_design"]:
        print(f"  - {item}")


def check(protocol: dict, results: dict[str, dict]) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {message}")
        if not condition:
            failures.append(message)

    for system_id, data in results.items():
        print(f"{system_id}:")
        specification = SYSTEMS[system_id]
        require(
            data["frame_count"] == 100_000,
            f"frame count is 100000 (found {data['frame_count']})",
        )
        require(
            data["minimum"] > 0.0 and data["maximum"] < float(specification.expected_atoms),
            "radius of gyration stays within a physically sane range for this molecule",
        )
        for size, estimate in data["blocks"].items():
            # Whether block averaging reports a larger or smaller SEM than the naive
            # i.i.d. formula depends on the series' correlation structure; it is not
            # a computational invariant, so it is reported in 'show', not asserted
            # here. What is a structural invariant is that using every frame in
            # equal blocks reproduces the direct trajectory mean exactly.
            require(
                estimate.frames_used == data["frame_count"],
                f"block size {size} divides the frame count with no dropped remainder",
            )
            require(
                abs(estimate.block_mean - data["full_mean"]) < 1e-9,
                f"block mean at {size} blocks reproduces the full-trajectory mean "
                "when every frame is used",
            )
        full_checkpoint = next(
            c for c in data["checkpoints"] if c.frames_included == data["frame_count"]
        )
        require(
            abs(full_checkpoint.difference_from_full_trajectory) < 1e-9,
            "the full-trajectory checkpoint reproduces the full-trajectory mean exactly",
        )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    protocol = load_protocol()
    try:
        results = compute(protocol)
    except DynamicsContractError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    if action == "show":
        show(protocol, results)
        print()
        print("Run 'check' to recompute these relationships.")
        return
    print("DYNAMICS OBSERVABLE CHECKS")
    failures = check(protocol, results)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print(
        "All checks passed. This verifies the arithmetic on the committed trajectory, "
        "not that a mass-weighted radius of gyration is the right observable for every question."
    )


if __name__ == "__main__":
    main()
