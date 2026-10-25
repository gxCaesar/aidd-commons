# Functional validation record audit

This laboratory reads two frozen local snapshots through their existing readers. It
classifies admitted ChEMBL 37 activity rows and retained PubChem BioAssay rows by
what each record actually contains. It does not fit a model, choose an example by
its result, or infer a clinical outcome.

## Run mode

This is a fresh independent computation under a frozen protocol. Python 3.11 in
the project environment is sufficient and no accelerator is needed. The first
command copies the two already validated source caches into this laboratory's
own ignored cache. It makes no network request. The summary exporter overwrites
only the small derived count artifact, and only after validation. The cached
source bytes remain separate from the committed summary.

```bash
.venv/bin/python labs/functional_validation_audit/run_lab.py download
.venv/bin/python labs/functional_validation_audit/inspect_functional_validation_audit.py show
.venv/bin/python labs/functional_validation_audit/inspect_functional_validation_audit.py check
.venv/bin/python labs/functional_validation_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/functional_validation_audit -q
```

The source caches are `.cache/decision_unit_scope/` and
`.cache/assay_endpoint_controls/`. Obtain them using their owning laboratories
before running this laboratory. The new cache is
`.cache/functional_validation_audit/`. The `download` action only copies local
validated records. It never calls a remote downloader. `show` reads the
committed count artifact. `check` reopens both cached snapshots and recomputes
every count. The exporter refuses a changed protocol or invalid count before
writing its output.

## Measurement rule

The ChEMBL reader admits only its declared nanomolar endpoint family with a
stated point or bound relation. One activity row remains one record in this
audit. It is not silently collapsed into an independent experiment. A direct
binding claim additionally needs a ChEMBL binding assay and a Kd or Ki type.

The PubChem reader admits one compound row within each declared assay. A row
becomes a concentration response table only when it has at least five numeric
concentration values and its assay description states an activation or
inhibition response. A value with a bound qualifier licenses a bound, not an
exact point. The assay with categorical results has no numeric response series.
An endpoint whose relation is unstated does not license an exact point or a
bound. The audit retains those records and counts them as licensing no claim.

| Snapshot | Records | Point measurement | Bound | Concentration response table | No licensed claim |
| --- | ---: | ---: | ---: | ---: | ---: |
| ChEMBL 37 admitted activity rows | 1004 | 488 | 516 | 0 | 0 |
| PubChem BioAssay retained rows | 1257 | 0 | 38 | 1204 | 15 |

The counts were computed on 2026-10-23 from cached records read on 2026-10-21
with Python 3.11.15 and RDKit 2025.09.6. The PubChem endpoint labels are
counted per endpoint value. Qualifiers are also counted per row so assay 519,
which has two endpoint values on each row, is not made to look like two
independent records.

Neither table carries a clinical endpoint. The snapshots do not pair a direct
binding measurement with a matched response record, nor a response record
with an outcome record. A measurement is not promoted to a response, and a
response is not promoted to an outcome.

## Provenance and terms

ChEMBL 37 is dated 2026-05-01. Its cached activity records and release terms
were read on 2026-10-21. The [release licence](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE)
states Creative Commons Attribution-ShareAlike 3.0 Unported for ChEMBL data.
The [release README](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/README)
requests attribution to ChEMBL and the release version.

The archived [PubChem BioAssay files](https://ftp.ncbi.nlm.nih.gov/pubchem/Bioassay/CSV/)
were read on 2026-10-21. The [NCBI policy page](https://www.ncbi.nlm.nih.gov/home/about/policies/)
is the institutional reuse reference. No terms statement specific to these
archived assay records was read, so their licence remains unverified here.
Original laboratory code is Apache-2.0 and original prose is CC BY 4.0.
