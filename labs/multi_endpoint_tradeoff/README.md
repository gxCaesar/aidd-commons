# Multi-endpoint coverage without a composite score

This laboratory reads the fifteen declared ChEMBL 37 seed molecules, resolves them to ten parent molecules, and reuses the decision-unit laboratory's admission and measurement-key rules. Its frozen protocol maps `AC50`, `EC50` and `IC50` to an efficacy-related response-potency proxy. `Kd` and `Ki` belong to `other` because binding affinity does not establish efficacy. The admitted standard types contain no type-specific toxicity or exposure measurement. These families are shown as missing rather than filled by interpretation.

## Frozen data and computation

The protocol is [`protocol.json`](protocol.json). It declares the source, each of the thirteen cached artefacts with its frozen byte length, the cohort, the point and bound relations, exclusion order, family map and descriptive statistics. The compiled contract checks every decision-bearing field before execution. The ChEMBL reader, parent resolver and admission classifier are reused from `aidd_commons.decision_unit_scope`. No model is fitted and no score or ranking is produced.

One independent point measurement has a unique parent, assay, document and standard type. Repeated activity rows at the same key contribute their median once. The summary gives the count of these independent measurements, distinct documents and assays, median, linear-quartile interquartile range and missing-parent count for each family. It repeats the counts and spread for each parent. The medians pool heterogeneous assays within the declared response-potency proxy and therefore describe the table, not a target-independent property of a compound.

## Fresh independent computation

Use Python 3.11 in the pinned `.venv`. The `download` command requests the ChEMBL 37 status endpoint and caches the source records under `.cache/multi_endpoint_tradeoff/`. It produces no summary. A cold cache needs network access. Once cached, the remaining commands use no network and no accelerator. They do not alter the source cache. `export_summary.py` overwrites the small committed summary only after all checks pass.

```bash
.venv/bin/python labs/multi_endpoint_tradeoff/run_lab.py download
.venv/bin/python labs/multi_endpoint_tradeoff/inspect_multi_endpoint_tradeoff.py show
.venv/bin/python labs/multi_endpoint_tradeoff/inspect_multi_endpoint_tradeoff.py check
.venv/bin/python labs/multi_endpoint_tradeoff/export_summary.py
.venv/bin/python -m pytest labs/tests/multi_endpoint_tradeoff -q
```

The committed [`summary.json`](summary.json) was computed on 2026-10-23 from the existing frozen ChEMBL 37 cache. Its 486 admitted independent point measurements agree with the decision-unit census. They partition into 462 response-potency measurements, zero toxicity measurements, zero exposure measurements and 24 affinity measurements in `other`. All ten parents lack at least one named family. This is a complete census of a deliberately chosen teaching cohort, not an estimate of coverage in ChEMBL or a clinical inference.

## Source and limits

The [ChEMBL 37 release](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/) is dated 2026-05-01. Its [licence](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE) is Creative Commons Attribution-ShareAlike 3.0 Unported, read on 2026-10-21. The release [README](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/README) gives attribution guidance. Original prose is CC BY 4.0 and original code is Apache-2.0. The committed summary contains no activity rows or structures.

The activity endpoint's `standard_type` does not identify therapeutic efficacy, toxicity biology, pharmacokinetic exposure or clinical safety. Censored bounds are excluded from value summaries. A missing family is not a negative result and does not mean a compound is safe, clean or bioavailable. The laboratory does not combine families, fit a model, estimate performance or rank compounds.
