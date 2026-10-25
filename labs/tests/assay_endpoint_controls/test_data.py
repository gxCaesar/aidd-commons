"""The data contract of the PubChem BioAssay reader.

These tests build a small archived record in the PubChem CSV format and check
that the reader admits exactly the rows the protocol admits, and that it
refuses a record the protocol does not allow.
"""

from __future__ import annotations

import pytest
from aidd_commons.assay_endpoint_controls.data import (
    DataContractError,
    control_mentions,
    parse_assay_csv,
)
from aidd_commons.assay_endpoint_controls.protocol import ASSAYS, CONTROL_KEYWORDS

SPEC = ASSAYS[548]

HEADER = (
    "PUBCHEM_RESULT_TAG,PUBCHEM_SID,PUBCHEM_CID,PUBCHEM_EXT_DATASOURCE_SMILES,"
    "PUBCHEM_ACTIVITY_OUTCOME,PUBCHEM_ACTIVITY_SCORE,PUBCHEM_ACTIVITY_URL,"
    "PUBCHEM_ASSAYDATA_COMMENT,Activity Qualifier,IC50,LogIC50,Hill Coefficient,"
    "Hill S0,Hill Sinf,Hill dS,Curve Chi2,Curve R2,Excluded Points,Number of Datapoints,"
    "Inhibition at 3.0 nM,Inhibition at 9.1 nM,Inhibition at 27.4 nM,"
    "Inhibition at 82 nM,Inhibition at 246 nM,Inhibition at 740 nM,"
    "Inhibition at 2.2 uM,Inhibition at 6.6 uM,Inhibition at 20 uM,Inhibition at 60 uM"
)
METADATA = (
    "RESULT_TYPE,,,,,,,,STRING,STRING,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,INTEGER,INTEGER,"
    "FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT,FLOAT"
)
ROW = (
    "1,7970106,5056270,C1C(OC2=CC=CC=C2O1)C(=O)NC3=NC(=CS3)C4=CC=NC=C4,"
    "Active,100,,,=,0.682,-6.17,1.16,5.228,101.663,96.435,8.82,1,,30,"
    "4.1,5.7,9.3,10.8,25.2,51.7,83.2,95.8,106.8,105.2"
)


def _record(rows: list[str]) -> str:
    return "\n".join([HEADER, METADATA, *rows]) + "\n"


def test_a_well_formed_record_is_admitted_with_its_archived_values() -> None:
    rows, audit = parse_assay_csv(_record([ROW]), SPEC)
    assert audit.input_rows == 1
    assert audit.retained_rows == 1
    assert audit.admitted_compounds == 1
    assert audit.exclusion_counts == {}
    row = rows[0]
    assert row.compound_id == "5056270"
    assert row.outcome == "Active"
    assert row.activity_score == 100.0
    assert row.qualifier == "="
    assert row.endpoints == {"IC50": 0.682}
    assert row.replicate_count == 30
    assert row.numeric_point_count == 10
    assert row.distinct_concentration_count == 10
    assert row.points[0].concentration_um == pytest.approx(0.003)
    assert row.points[-1].concentration_um == pytest.approx(60.0)
    assert row.points[-1].value == pytest.approx(105.2)
    assert row.extra_numbers["Hill Coefficient"] == pytest.approx(1.16)
    assert row.extra_numbers["Hill Sinf"] == pytest.approx(101.663)


def test_the_metadata_rows_are_never_admitted() -> None:
    rows, audit = parse_assay_csv(_record([METADATA, ROW]), SPEC)
    assert audit.input_rows == 1
    assert audit.retained_rows == 1
    assert len(rows) == 1


def test_a_row_without_a_structure_is_excluded_and_counted() -> None:
    broken = ROW.replace("C1C(OC2=CC=CC=C2O1)C(=O)NC3=NC(=CS3)C4=CC=NC=C4", "")
    rows, audit = parse_assay_csv(_record([broken]), SPEC)
    assert audit.retained_rows == 0
    assert audit.exclusion_counts == {"missing_or_invalid_inline_structure": 1}
    assert rows == ()


def test_a_row_without_an_outcome_is_excluded() -> None:
    broken = ROW.replace(",Active,100,", ",,100,")
    _, audit = parse_assay_csv(_record([broken]), SPEC)
    assert audit.exclusion_counts == {"no_activity_outcome": 1}


def test_a_row_without_a_compound_identifier_is_excluded() -> None:
    broken = ROW.replace(",5056270,", ",,")
    _, audit = parse_assay_csv(_record([broken]), SPEC)
    assert audit.exclusion_counts == {"no_compound_identifier": 1}


def test_a_row_without_an_endpoint_value_is_excluded() -> None:
    broken = ROW.replace("=,0.682,-6.17,", "=,,-6.17,")
    _, audit = parse_assay_csv(_record([broken]), SPEC)
    assert audit.exclusion_counts == {"no_endpoint_value": 1}


def test_a_repeated_compound_is_excluded() -> None:
    rows, audit = parse_assay_csv(_record([ROW, ROW]), SPEC)
    assert audit.retained_rows == 1
    assert audit.exclusion_counts == {"repeated_compound": 1}
    assert len(rows) == 1


def test_a_record_without_the_qualifier_column_is_refused() -> None:
    header = HEADER.replace("Activity Qualifier,", "")
    body = ROW.replace("=,0.682", ",0.682")
    with pytest.raises(DataContractError, match="qualifier column"):
        parse_assay_csv("\n".join([header, METADATA, body]) + "\n", SPEC)


def test_a_record_without_an_endpoint_column_is_refused() -> None:
    header = HEADER.replace("Activity Qualifier,IC50,", "Activity Qualifier,")
    body = ROW.replace("=,0.682,-6.17,", "=,-6.17,")
    with pytest.raises(DataContractError, match="endpoint column"):
        parse_assay_csv("\n".join([header, METADATA, body]) + "\n", SPEC)


def test_a_record_without_enough_concentrations_is_refused() -> None:
    columns = HEADER.split(",")
    kept = [column for column in columns if not column.startswith("Inhibition at")]
    kept.extend(["Inhibition at 3.0 nM", "Inhibition at 9.1 nM"])
    header = ",".join(kept)
    with pytest.raises(DataContractError, match="per-concentration columns"):
        parse_assay_csv("\n".join([header, METADATA, ROW]) + "\n", SPEC)


def test_control_mentions_are_found_only_in_the_frozen_keyword_list() -> None:
    text = "The vehicle was added and the positive control was read."
    assert control_mentions(text, CONTROL_KEYWORDS) == ("control", "vehicle")
    assert control_mentions("Nothing was normalised here.", CONTROL_KEYWORDS) == ()
