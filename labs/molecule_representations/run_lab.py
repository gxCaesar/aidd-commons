from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from aidd_commons.representations.inspection import (
    MoleculeInput,
    RepresentationConfig,
    RepresentationInputError,
    build_report,
    render_report,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = Path("labs/molecule_representations/examples.csv")
DEFAULT_OUTPUT = Path("tmp/molecule-representations/report.json")
REQUIRED_COLUMNS = ("id", "smiles", "teaching_point")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect small-molecule representations without labels or predictive models."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    inspect = subparsers.add_parser(
        "inspect", help="parse molecules and write a versioned representation report"
    )
    inspect.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    inspect.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    inspect.add_argument("--morgan-radius", type=int, default=2)
    inspect.add_argument("--morgan-bits", type=int, default=2048)
    inspect.add_argument(
        "--ignore-chirality",
        action="store_true",
        help="omit chirality from Morgan atom invariants and record that choice",
    )
    return parser.parse_args(argv)


def load_inputs(path: Path) -> tuple[MoleculeInput, ...]:
    try:
        with path.open(newline="", encoding="utf8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(REQUIRED_COLUMNS):
                raise RepresentationInputError(
                    "input CSV header must be exactly: " + ",".join(REQUIRED_COLUMNS)
                )
            return tuple(
                MoleculeInput(
                    source_id=row["id"],
                    smiles=row["smiles"],
                    teaching_point=row["teaching_point"],
                )
                for row in reader
            )
    except OSError as error:
        raise RepresentationInputError(f"could not read input CSV: {path}") from error


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        input_path = _resolve_repository_path(args.input)
        output_path = _resolve_repository_path(args.output)
        records = load_inputs(input_path)
        if not records:
            raise RepresentationInputError("input CSV must contain at least one molecule")
        report = build_report(
            records,
            config=RepresentationConfig(
                morgan_radius=args.morgan_radius,
                morgan_bits=args.morgan_bits,
                include_chirality=not args.ignore_chirality,
            ),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_report(report), encoding="utf8")
        print(f"Representation report written: {output_path}")
        return 0
    except RepresentationInputError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


def _resolve_repository_path(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
