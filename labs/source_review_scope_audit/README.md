# Source review and claim scope audit

This CPU-only laboratory measures how the committed Atlas binds structured claims to evidence entries. A frozen selection of four records is read directly from the catalogue. The independent reading for `t01-source-review-scope` is also read locally. No external page is opened.

## Data and protocol

The frozen protocol fixes the record identifiers, their order and four entry-level parts. A URL carries a source surface. Dedicated `version`, `reviewed_on` and `reviewed_scope` fields carry the other parts. A date or a document type named in a label is reported as `named-in-text`. A generic project or repository label does not name reviewed material. A record-level `last_verified` date is not an entry-level review date, and `supports` maps claims to an entry rather than describing the exact source material reviewed.

The claim population contains status, access, seven openness dimensions and each licence object. An `unverified` claim may have no evidence reference. Other claims need a reference to an entry of the same record. A resolving reference does not establish that the linked page supports the claim.

## Reproduction

Mode is fresh independent computation over the frozen protocol and committed records. Use the project Python 3.11 environment with PyYAML. All commands run locally without network, download or accelerator. The first three commands write nothing. The exporter overwrites only the compact committed summary after the checks pass.

```bash
.venv/bin/python labs/source_review_scope_audit/run_lab.py check
.venv/bin/python labs/source_review_scope_audit/inspect_source_review_scope_audit.py show
.venv/bin/python labs/source_review_scope_audit/inspect_source_review_scope_audit.py check
.venv/bin/python labs/source_review_scope_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/source_review_scope_audit -q
```

The inspector prints every entry's four states, claim references, per-record counts, totals, the independent reading and the routes it cannot measure. A malformed record, unresolved claim reference or changed protocol makes `check` fail. The exporter writes no summary when validation fails.

## Observed result and limits

The committed computation on 2026-10-23 examined 4 records with 12 evidence entries. All 12 carried a URL. No entry carried a dedicated version, review date or reviewed material field. Nine labels named a date and 5 named a document type in text, while 7 did not name reviewed material. None carried all four parts, carried date and surface without version, or had a name only. Of 39 structured claims, 15 had a reference, 24 had none and no claim had an unresolved reference. No claim cited an entry with a dedicated review date.

The project's own comparison record states `worked` for this topic. The earlier independent reading states `assessed` for the material it examined. This audit preserves that disagreement and does not re-score either reading. It also does not open linked pages. It cannot decide whether a page says what a record claims, whether a review was thorough, which revision a moving URL showed, or what a licence legally permits. An entry without its own date does not show that its claim is false or that the source is unreliable.

Original laboratory code is Apache-2.0 and this prose is CC BY 4.0. The catalogue, comparison record and independent reading were read locally on 2026-10-23. External resource terms remain with their sources.
