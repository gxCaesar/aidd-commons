# Entity kinds in a ChEMBL activity table

This laboratory asks which entity each identifier in an activity row names. It
reuses the ChEMBL 37 snapshot and the point-admission and measurement-grouping
rules of the decision-unit laboratory. It counts distinct molecule records,
parent molecules, assays, targets and documents over admitted rows. It also
reports the kinds for which these rows carry no identifier.

## Environment and data

Use the project's Python 3.11 environment on a CPU. The thirteen frozen
ChEMBL 37 artefacts are read from the validated decision-unit snapshot. A
download command validates that snapshot and copies it to this laboratory's
cache. Once the snapshot is present, these commands need no network. The
source data retain the ChEMBL 37 Creative Commons Attribution-ShareAlike 3.0
Unported terms. Laboratory code is Apache-2.0, and original prose is CC BY
4.0. The protocol records the source URLs and frozen artefact byte lengths.

## Fresh independent computation

Run these commands from the repository root.

```bash
.venv/bin/python labs/entity_glossary_audit/run_lab.py download
.venv/bin/python labs/entity_glossary_audit/inspect_entity_glossary_audit.py show
.venv/bin/python labs/entity_glossary_audit/inspect_entity_glossary_audit.py check
.venv/bin/python labs/entity_glossary_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/entity_glossary_audit -q
```

`download` writes only the thirteen validated artefacts to this laboratory's
cache. `show` and `check` write nothing. `check` recomputes the summary from
the cache and exits non-zero on a failed invariant or disagreement with the
committed result. The exporter overwrites only `summary.json`, after the
protocol, data contract and arithmetic checks pass. The committed summary
contains counts and rules, not activity rows or structures.

## Expected result and limits

The committed 2026-10-23 reading has 488 admitted point rows and 486
independent measurements. The admitted rows name 15 molecule records, 9
parent molecules, 481 assays, 100 targets and 221 documents. One declared
parent has no admitted point row, so the parent count over admitted rows is
smaller than the cohort's 10 resolved parents. Across the five kinds there
are 826 distinct identifiers and 2,440 row-level identifier uses. One
independent measurement group contains two molecule-record identifiers.

There are 71 admitted rows whose molecule record differs from its parent.
They involve 6 child-form identifiers. The five declared salt seeds account
for 65 of those rows. The remaining identifier is reported as a child form
without assigning it a chemical-form name from an absent molecule record.
The 100 targets include 21 measured for more than one molecule record.

Complexes, cell states, patients and therapeutic candidates have no
identifier in these cached rows. The audit names all four omissions and
counts the 488 admitted rows that lack each identifier. This does not imply
that every activity ought to be a patient or candidate record. The audit
does not merge identifiers, predict activity, equate a target with a disease,
or treat a publication identifier as proof that a measurement is correct.
