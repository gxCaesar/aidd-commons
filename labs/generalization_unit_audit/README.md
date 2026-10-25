# Generalization-unit audit

This CPU laboratory recounts a fixed ChEMBL 37 teaching cohort under six candidate units. The cohort was selected to exercise the admission rule, not to estimate a population rate. One independent measurement is an admitted point row after collapsing repeated parent, assay, document and endpoint keys. Bound rows and excluded rows do not enter the unit counts.

## Reproduction

Mode is fresh independent computation over a frozen protocol. Use the project Python 3.11 environment. The first command copies the already validated local snapshot into this laboratory's separate cache. It needs no network or accelerator. It only updates that cache. `show` and `check` write nothing. The exporter overwrites the committed compact summary only after its checks pass.

```bash
.venv/bin/python labs/generalization_unit_audit/run_lab.py download
.venv/bin/python labs/generalization_unit_audit/inspect_generalization_unit_audit.py show
.venv/bin/python labs/generalization_unit_audit/inspect_generalization_unit_audit.py check
.venv/bin/python labs/generalization_unit_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/generalization_unit_audit -q
```

The source cache comes from the decision-unit laboratory. The reader validates its frozen artifact lengths, source release and row contract before any count is made. The copy is validated again. If the source cache is absent, the download command refuses to fabricate a replacement. The inspector and exporter can read the validated source cache when this laboratory's copy has not yet been made.

## Counting rule

For each candidate unit, the audit counts distinct values and the independent measurements assigned to them. It reports the median, first and third quartiles of measurements per value, using inclusive linear interpolation, and the number of singleton values. A repeated measurement can carry two tested molecule IDs, so molecule membership totals can exceed the distinct measurement count. A singleton value loses its only same-value observation under leave-one-measurement-out. A split that holds out a whole unit leaves every held-out value without same-value training observations by construction.

The table cannot name measurement time point, collection site or patient. The audit fits no model, scores no prediction and does not decide which unit is right. It only shows what information each declared unit carries in this selected cohort.

Original teaching code is Apache-2.0 and this prose is CC BY 4.0. The ChEMBL 37 snapshot retains Creative Commons Attribution-ShareAlike 3.0 Unported terms. The RDKit source licence is BSD 3-Clause.
