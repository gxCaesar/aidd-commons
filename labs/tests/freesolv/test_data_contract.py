from __future__ import annotations

import pytest
from aidd_commons.freesolv.data import DataQualityError, parse_freesolv_v052

HEADER = """#Hydration free energy datbase v0.52, 6/11/17.
#Semicolon-delimited text file with fields in the following format:
"""


def row(
    source_id: str,
    smiles: str,
    experimental_value: str,
    calculated_value: str = "999.0",
) -> str:
    return (
        f"{source_id}; {smiles}; fixture name; {experimental_value}; 0.10; "
        f"{calculated_value}; 0.01; experimental ref; calculated ref; note"
    )


def parse_rows(*rows: str):
    return parse_freesolv_v052(HEADER + "\n".join(rows) + "\n")


def test_uses_canonical_isomeric_smiles_and_the_fourth_field_as_target() -> None:
    records, report = parse_rows(
        row("mobley_fixture_1", "C(C)O", "-5.01"),
        row("mobley_fixture_2", "C[C@H](O)F", "-3.25"),
    )

    assert [record.source_id for record in records] == [
        "mobley_fixture_1",
        "mobley_fixture_2",
    ]
    assert [record.canonical_smiles for record in records] == ["CCO", "C[C@H](O)F"]
    assert [record.target_kcal_mol for record in records] == [-5.01, -3.25]
    assert report.parsed_rows == 2
    assert report.continuation_lines == 0


@pytest.mark.parametrize(
    ("rows", "error"),
    [
        (
            (
                row("mobley_fixture_1", "CCO", "-5.01"),
                row("mobley_fixture_2", "OCC", "-5.01"),
            ),
            "duplicate canonical molecule",
        ),
        ((row("mobley_fixture_1", "not-a-smiles", "-5.01"),), "unparseable"),
        ((row("mobley_fixture_1", "CCO", "nan"),), "non-finite"),
        ((row("", "CCO", "-5.01"),), "missing source ID"),
        (
            (
                row("mobley_fixture_1", "CCO", "-5.01"),
                row("mobley_fixture_1", "CCN", "-4.01"),
            ),
            "multiple canonical molecules",
        ),
    ],
)
def test_rejects_each_data_quality_mutation(rows: tuple[str, ...], error: str) -> None:
    with pytest.raises(DataQualityError, match=error):
        parse_rows(*rows)


def test_rejects_an_unexpected_dataset_header() -> None:
    with pytest.raises(DataQualityError, match="header"):
        parse_freesolv_v052("#Hydration free energy datbase v0.51, 6/11/17.\n")


def test_rejects_a_noncomment_single_field_row_after_valid_data_without_dropping_it() -> None:
    with pytest.raises(DataQualityError, match="malformed non-comment data row") as error:
        parse_rows(row("mobley_fixture_1", "CCO", "-5.01"), "orphaned-text")

    assert error.value.report.parsed_rows == 1
    assert error.value.report.noncomment_lines == 2
    assert error.value.report.continuation_lines == 0


def test_rejects_an_empty_smiles_that_rdkit_parses_as_zero_atoms() -> None:
    with pytest.raises(DataQualityError, match="empty or zero-atom molecule") as error:
        parse_rows(row("mobley_fixture_1", "", "-5.01"))

    assert error.value.report.parsed_rows == 0
    assert error.value.report.noncomment_lines == 1
    assert error.value.report.continuation_lines == 0
