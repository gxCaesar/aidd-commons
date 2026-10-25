# Split and leakage audit on ChEMBL 37

This laboratory counts which identities cross a random row split of a declared
ChEMBL activity cohort. It reuses the decision-unit laboratory's ChEMBL 37
reader, entity resolution, admission rule and frozen artefact lengths. It fits
no model and reports no predictive performance.

## Data and measurement unit

The cohort contains 15 seed molecules resolved to 10 parents. The reader
admits point measurements in the declared nanomolar potency endpoint family.
The decision-unit laboratory counts one independent measurement for each
unique parent, assay, document and endpoint type. This audit splits those
486 measurement units. The 488 admitted point activity rows include two
repeated keys. A measurement with multiple source rows retains the union of
their route groups, including different tested forms.

The source is ChEMBL 37, released 2026-05-01. The cached snapshot contains
13 deterministic JSON artefacts. Each is checked against the frozen byte
length in `protocol.json`. The local cache is
`.cache/split_leakage_audit/`. `download` copies the validated snapshot from
the decision-unit cache when it is present. Otherwise it uses the sibling
downloader and verifies the resulting artefacts. A complete local snapshot
requires no network for `show`, `check` or `export_summary.py`.

## Frozen protocol and run

The protocol ID is `chembl37-split-leakage-routes-v1`. The compiled contract
checks the cohort, endpoint, split, route fields, software version, source,
artefact lengths, and excluded claims before computation. The row split
sorts measurement keys and shuffles with Python `random.Random(20261023)`.
It assigns `floor(0.8 × 486)` measurements to training. The grouped split
shuffles the 10 parent identifiers with the same seed, keeps 8 in training,
and assigns every measurement of the other parents to test.

```bash
.venv/bin/python labs/split_leakage_audit/run_lab.py download
.venv/bin/python labs/split_leakage_audit/inspect_split_leakage_audit.py show
.venv/bin/python labs/split_leakage_audit/inspect_split_leakage_audit.py check
.venv/bin/python labs/split_leakage_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/split_leakage_audit -q
```

`download` writes only the cache. `show` reads the committed summary. `check`
recomputes it from the cached snapshot and checks the arithmetic. The
exporter validates the frozen protocol and all counts before overwriting
`summary.json`. If the new cache has not yet been made, the inspector and
exporter can use the already validated decision-unit cache. Use
`--cache-dir` to select a cache explicitly.

## Observed result

The committed summary was computed on 2026-10-23 with Python 3.11.15 and
RDKit 2025.09.6. The row split has 388 training and 98 test measurements.

| Route group | Test rows sharing training group | Shared groups | Training rows a route-aware holdout would remove |
| --- | ---: | ---: | ---: |
| Parent molecule | 98 | 6 | 381 |
| Bemis-Murcko scaffold | 98 | 6 | 379 |
| Assay | 1 | 1 | 1 |
| Target identifier | 81 | 19 | 285 |
| Standard tested form | 98 | 11 | 379 |

All 98 row-split test measurements share at least one tested group with
training, and all 5 tested routes contribute. Parent, scaffold and standard
form tie for the highest test overlap. `highest_overlap_route` is `parent`
because it is first in the frozen route order. The parent-grouped split has
133 training and 353 test measurements, with 353 test measurements unseen by
parent. Its uneven row counts follow the whole-parent assignment.

The scaffold is chirality aware and uses an explicit acyclic key for ring-free
structures. Scaffold overlap is only a proxy for analogue overlap. The target
route uses an exact target identifier, not a biological target family. Standard
form is RDKit canonical isomeric SMILES of the tested structure. It does not
audit fitted preprocessing. Duplicate source rows are collapsed before the
split, and ChEMBL's potential-duplicate flag is handled by the source
admission rule.

## Boundaries and source terms

The table has no measurement date, donor, patient or collection site field.
Temporal, donor, patient and site leakage cannot be measured from it. A
parent-disjoint split only establishes parent disjointness. The cohort was
chosen to exercise counting rules and is not a random sample of ChEMBL.
No performance estimate or new-compound prediction follows from this audit.

ChEMBL 37 is published by EMBL-EBI under Creative Commons
Attribution-ShareAlike 3.0 Unported. The release
[licence](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE)
and [status](https://www.ebi.ac.uk/chembl/api/data/status.json) were read
for the sibling snapshot on 2026-10-21. The [RDKit source licence](https://github.com/rdkit/rdkit/blob/master/license.txt)
was recorded as BSD 3-Clause on 2026-09-09. This repository's original code
is Apache-2.0 and original prose is CC BY 4.0. The summary contains counts
and no activity rows.
