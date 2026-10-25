from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from aidd_commons.freesolv.data import DataQualityError
from aidd_commons.freesolv.evaluation import EvaluationContractError
from aidd_commons.freesolv.models import ModelContractError
from aidd_commons.freesolv.pipeline import (
    DATA_FILE_NAME,
    DataDownloadError,
    PretestValidationError,
    download_freesolv_v052,
    evaluate_test,
    load_freesolv_v052,
    portable_evaluation_command,
    run_pretest,
)
from aidd_commons.freesolv.splits import SplitContractError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = Path(".cache/freesolv")
DEFAULT_OUTPUT_DIR = Path("labs/freesolv/results")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the frozen FreeSolv v0.52 honest-baseline lab."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    download = subparsers.add_parser("download", help="download the pinned v0.52 data into a cache")
    download.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)

    for action, help_text in (
        ("pretest", "run all validation-only checks and write split membership"),
        ("evaluate-test", "perform the final test evaluation once after pretest passes"),
    ):
        command = subparsers.add_parser(action, help=help_text)
        command.add_argument(
            "--data-path",
            type=Path,
            default=DEFAULT_CACHE_DIR / DATA_FILE_NAME,
            help="pinned v0.52 database.txt downloaded by the download command",
        )
        command.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.action == "download":
            data_path = download_freesolv_v052(_resolve_repository_path(args.cache_dir))
            print(f"Downloaded or reused pinned FreeSolv data: {data_path}")
            return 0

        data_path = _resolve_repository_path(args.data_path)
        output_dir = _resolve_repository_path(args.output_dir)
        command = portable_evaluation_command(data_path, output_dir, REPOSITORY_ROOT)
        records, parse_report = load_freesolv_v052(data_path)
        if args.action == "pretest":
            artifact = run_pretest(
                records,
                parse_report,
                output_dir,
                planned_evaluation_command=command,
            )
            print(f"Pre-test gate passed; artifacts written to: {artifact.output_dir}")
            return 0

        metrics_path = evaluate_test(
            records,
            parse_report,
            output_dir,
            command=command,
        )
        print(f"Final test evaluation completed once; metrics written to: {metrics_path}")
        return 0
    except (
        DataDownloadError,
        DataQualityError,
        EvaluationContractError,
        ModelContractError,
        PretestValidationError,
        SplitContractError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


def _resolve_repository_path(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
