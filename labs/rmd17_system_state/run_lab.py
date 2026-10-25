from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from aidd_commons.rmd17_system_state.pipeline import (
    LockedEvaluationError,
    PipelineContractError,
    PublicSummaryError,
    download_development,
    evaluate_locked,
    run_pretest,
    validate_protocol,
    write_development_summary,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the frozen revised-MD17 system-state teaching lab."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser(
        "validate-protocol", help="validate the frozen source and method contract"
    )
    subparsers.add_parser("download-development", help="download only ethanol and malonaldehyde")
    subparsers.add_parser("pretest", help="fit development-only baselines and write evidence")
    locked = subparsers.add_parser(
        "evaluate-locked",
        help="run the paired benzene and uracil evaluation once after approval",
    )
    locked.add_argument(
        "--confirm-run-locked-evaluation",
        action="store_true",
        help="confirm the one-time paired locked evaluation",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.action == "validate-protocol":
            validate_protocol(REPOSITORY_ROOT)
            print("Frozen rMD17 protocol is valid.")
            return 0
        if args.action == "download-development":
            paths = download_development(REPOSITORY_ROOT)
            print("Development files ready: " + ", ".join(path.name for path in paths))
            return 0
        if args.action == "pretest":
            artifact = run_pretest(REPOSITORY_ROOT)
            summary_path = write_development_summary(REPOSITORY_ROOT)
            print(f"Development pretest passed: {artifact.pretest_path}")
            print(f"Reviewed development summary written: {summary_path}")
            print("Locked benzene and uracil evaluations: not run")
            return 0
        metrics_path = evaluate_locked(
            REPOSITORY_ROOT,
            confirmed=args.confirm_run_locked_evaluation,
        )
        print(f"Paired locked evaluation completed once: {metrics_path}")
        return 0
    except (LockedEvaluationError, PipelineContractError, PublicSummaryError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
