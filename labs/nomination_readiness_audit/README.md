# Nomination readiness audit on ChEMBL 37

This CPU laboratory applies a declared measurement-readiness rule to the ten
parent molecules in the decision-unit cohort. It counts evidence available for
a next decision. It does not rank compounds by potency or nominate a candidate.

## Data and frozen rule

The source is the cached ChEMBL 37 activity snapshot. Fifteen seed molecules
resolve to ten parents. The decision-unit reader admits nanomolar AC50, EC50,
IC50, Kd and Ki point rows after its frozen exclusions. One independent
measurement is one distinct parent, assay, document and endpoint-type key.
The 488 admitted point rows yield 486 independent measurements.

This laboratory's protocol fixes three teaching minima before this readiness
audit is counted. A parent needs at least 5 independent measurements, 3
distinct assays and 2 distinct documents. Meeting all three gives `go`.
Meeting some gives `hold`. Meeting none gives `stop`. For each failed
condition, the output names the additional count and the field an admitted
activity record must supply. A new assay or document identifier must be
distinct for that parent. These minima are a project decision, not a
validated biological or clinical nomination rule.

## Reproduction

Mode is a fresh independent computation over the frozen protocol. Use the
project's Python 3.11 environment. `download` copies the byte-validated
snapshot from the decision-unit cache into this laboratory's own cache. If
the sibling cache is unavailable, the shared downloader fetches the declared
ChEMBL artefacts. Once cached, the recount needs no network or accelerator.

```bash
.venv/bin/python labs/nomination_readiness_audit/run_lab.py download
.venv/bin/python labs/nomination_readiness_audit/inspect_nomination_readiness_audit.py show
.venv/bin/python labs/nomination_readiness_audit/inspect_nomination_readiness_audit.py check
.venv/bin/python labs/nomination_readiness_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/nomination_readiness_audit -q
```

`download` writes only the local cache. `show` prints the rule and every
parent's state. `check` independently reloads the cached rows, recomputes
the counts, and fails on a changed contract, arithmetic or committed result.
The exporter writes only the compact summary after the same contracts pass.
Until the new cache is made, the inspector and exporter can read the validated
decision-unit cache. `--cache-dir` selects a cache explicitly.

## Observed result and limits

The 2026-10-23 recount puts 6 parents in `go`, 2 in `hold` and 2 in `stop`.
SODIUM LAURYL SULFATE is the closest non-`go` parent under the declared
tie rule. It has 4 independent measurements, 4 assays and 3 documents, so
one additional independent measurement key is missing. The committed summary
contains the full per-parent table and no activity rows.

The cohort was chosen to exercise counting rules and does not estimate a
population frequency. A count says nothing about activity, safety or
exposure. `go` does not establish candidacy, and `stop` does not establish
inactivity. A prospective experimental decision would also need endpoint
validity, independent confirmation and other evidence outside this table.

ChEMBL 37 was released on 2026-05-01. Its [licence](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE)
is Creative Commons Attribution-ShareAlike 3.0 Unported. The cached status,
licence and [schema documentation](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/schema_documentation.txt)
were read for the source snapshot on 2026-10-21. Original teaching code is
Apache-2.0 and original prose is CC BY 4.0.
