# PK/PD translation assumption audit

This lab computes an illustrative exposure, target occupancy and effect curve for real ChEMBL parent molecules with intrinsic clearance measured in both rat and human hepatocytes. It reuses the validated ChEMBL 37 snapshot and admission reader of the AZ clearance-system lab. The only measured inputs are in vitro clearance values. Dose, effective cell count, apparent volume, unbound fraction, binding and effect parameters are explicit project assumptions.

## Reproduce the result

Use Python 3.11 and the repository's pinned environment. The mode is a fresh independent CPU computation over a frozen protocol and the existing local cache. No network or accelerator is used once that cache is present. `download` validates and reuses the cache without writing it. `show` and `check` write nothing. `export_summary.py` replaces only this lab's `summary.json` after all checks pass.

```bash
.venv/bin/python labs/pkpd_translation_audit/run_lab.py download
.venv/bin/python labs/pkpd_translation_audit/inspect_pkpd_translation_audit.py show
.venv/bin/python labs/pkpd_translation_audit/inspect_pkpd_translation_audit.py check
.venv/bin/python labs/pkpd_translation_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/pkpd_translation_audit -q
```

The source cache contains the status response and three assay activity responses totaling 1,518,229 bytes. The ChEMBL 37 snapshot was fetched on 2026-09-12. The source document is [CHEMBL3301361](https://www.ebi.ac.uk/chembl/explore/document/CHEMBL3301361), deposited by AstraZeneca. ChEMBL 37 data records carry [Creative Commons Attribution-ShareAlike 3.0 Unported](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE), reviewed on 2026-10-21. Individual deposited documents retain their owners' rights. Original code is Apache-2.0 and original prose is CC BY 4.0.

## Frozen model

The model uses the rat hepatocyte clearance of each paired compound and a leave-one-out median of human-to-rat clearance ratios from the other paired compounds. Its 0.1 and 0.9 empirical ratio quantiles define the species-factor range. The rat assay value receives an assumed 0.2 relative uncertainty. The per-million-cell clearance is multiplied by an assumed 100000000 effective cells and converted from µL/min to L/h. A one-compartment 1 µmol input and 1 L apparent volume then produce a concentration at 24 h. A 0.1 unbound fraction produces free concentration. An assumed 0.2 µmol/L binding constant gives occupied fraction, and an assumed Emax response function maps engagement to a fractional effect increment. The full protocol supplies units, sources, and sensitivity bounds for every parameter.

The interval is recomputed after each uncertain step. It widens from rat assay error through species-factor variation, unbound fraction, binding constant, Emax and engagement EC50. These are deterministic sensitivity bounds, not calibrated confidence intervals. The same compound's human hepatocyte measurement is shown for contrast and is never used to set its own translation factor.

## Cohort and boundary

The reader admits 743 human microsome, 592 rat hepatocyte and 288 human hepatocyte parent records, giving 1120 distinct parents. The paired hepatocyte cohort contains 106 parents, of which 37 have at least a threefold difference between species. The model cannot carry 1014 parents. Of these, 182 lack a rat hepatocyte record, 486 lack a human hepatocyte record, and 346 occur only in the microsome assay. Microsome clearance is per gram protein, while hepatocyte clearance is per million cells. No unsupported conversion is applied.

Target-site concentration is assumed equal to free compartment concentration, binding is at instantaneous equilibrium, and response is immediate. None was measured in the source. The model has no measured unbound fraction, binding constant, target engagement, volume, in vivo clearance or response. Its effect is a predicted response under project assumptions, not a measured response or clinical benefit. Its species step is a within-cohort illustration, not validated translation, and the compounds must not be ranked by predicted effect.
