from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from rdkit import Chem

V052_HEADER = (
    "#Hydration free energy datbase v0.52, 6/11/17.",
    "#Semicolon-delimited text file with fields in the following format:",
)


@dataclass(frozen=True)
class MoleculeRecord:
    source_id: str
    input_smiles: str
    canonical_smiles: str
    target_kcal_mol: float


@dataclass(frozen=True)
class ParseReport:
    total_lines: int
    noncomment_lines: int
    parsed_rows: int
    continuation_lines: int


class DataQualityError(ValueError):
    def __init__(self, message: str, report: ParseReport) -> None:
        super().__init__(
            f"{message}; parsed_rows={report.parsed_rows}; "
            f"continuation_lines={report.continuation_lines}; "
            f"noncomment_lines={report.noncomment_lines}"
        )
        self.report = report


def parse_freesolv_v052(text: str) -> tuple[tuple[MoleculeRecord, ...], ParseReport]:
    lines = text.splitlines()
    if tuple(lines[:2]) != V052_HEADER:
        raise DataQualityError(
            "unexpected v0.52 header",
            ParseReport(
                total_lines=len(lines),
                noncomment_lines=0,
                parsed_rows=0,
                continuation_lines=0,
            ),
        )

    records: list[MoleculeRecord] = []
    source_to_canonical: dict[str, str] = {}
    canonical_to_source: dict[str, str] = {}
    continuation_lines = 0
    noncomment_lines = 0

    for line in lines[2:]:
        if not line.strip() or line.startswith("#"):
            continue

        noncomment_lines += 1
        fields = [field.strip() for field in line.split(";")]
        if len(fields) == 1:
            raise _data_error(
                "malformed non-comment data row",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )
        if len(fields) < 4:
            raise _data_error(
                "missing source ID or fourth target field",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )

        source_id, input_smiles, _, target_text = fields[:4]
        if not source_id:
            raise _data_error(
                "missing source ID",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )

        molecule = Chem.MolFromSmiles(input_smiles)
        if not input_smiles or (molecule is not None and molecule.GetNumAtoms() == 0):
            raise _data_error(
                f"empty or zero-atom molecule for source ID {source_id}",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )
        if molecule is None:
            raise _data_error(
                f"unparseable molecule for source ID {source_id}",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )
        canonical_smiles = Chem.MolToSmiles(molecule, isomericSmiles=True)

        try:
            target = float(target_text)
        except ValueError as error:
            raise _data_error(
                f"non-finite target for source ID {source_id}",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            ) from error
        if not isfinite(target):
            raise _data_error(
                f"non-finite target for source ID {source_id}",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )

        prior_canonical = source_to_canonical.get(source_id)
        if prior_canonical is not None and prior_canonical != canonical_smiles:
            raise _data_error(
                f"source ID {source_id} maps to multiple canonical molecules",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )
        prior_source = canonical_to_source.get(canonical_smiles)
        if prior_source is not None:
            raise _data_error(
                f"duplicate canonical molecule {canonical_smiles}",
                lines,
                noncomment_lines,
                records,
                continuation_lines,
            )

        source_to_canonical[source_id] = canonical_smiles
        canonical_to_source[canonical_smiles] = source_id
        records.append(
            MoleculeRecord(
                source_id=source_id,
                input_smiles=input_smiles,
                canonical_smiles=canonical_smiles,
                target_kcal_mol=target,
            )
        )

    report = ParseReport(
        total_lines=len(lines),
        noncomment_lines=noncomment_lines,
        parsed_rows=len(records),
        continuation_lines=continuation_lines,
    )
    return tuple(records), report


def _data_error(
    message: str,
    lines: list[str],
    noncomment_lines: int,
    records: list[MoleculeRecord],
    continuation_lines: int,
) -> DataQualityError:
    return DataQualityError(
        message,
        ParseReport(
            total_lines=len(lines),
            noncomment_lines=noncomment_lines,
            parsed_rows=len(records),
            continuation_lines=continuation_lines,
        ),
    )
