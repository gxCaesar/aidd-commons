# Specificity margin coverage audit

This CPU-first lab counts which protein labels have measurements with more than one distinct partner in the cached SKEMPI 2.0 mirror. It does not estimate a selectivity margin or infer that a protein is selective. The protocol freezes the counting unit and exclusions before the summary is regenerated.

## Environment and source

Use the project's Python 3.11 environment. The new cache is separate from the affinity lab's cache. The download command reuses the validated local copy when available. Network access is needed only if neither cache contains the snapshot. The reader checks the snapshot length and row alignment. It leaves mirror overflow fragments uninterpreted. The upstream [SKEMPI terms](https://life.bsc.es/pid/skempi2/info/terms) state CC BY 4.0. The [LiteFold mirror card](https://huggingface.co/datasets/LiteFold/SKEMPI2) labels its licence `other`. These source statements were checked on 2026-10-23.

## Fresh independent computation

Run these commands from the repository root. `download` writes only the separate cache copy. `show` and `check` do not write results. `export_summary.py` overwrites the small committed summary only after validation. It does not write archive rows.

```bash
.venv/bin/python labs/specificity_margin_audit/run_lab.py download
.venv/bin/python labs/specificity_margin_audit/inspect_specificity_margin_audit.py show
.venv/bin/python labs/specificity_margin_audit/inspect_specificity_margin_audit.py check
.venv/bin/python labs/specificity_margin_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/specificity_margin_audit -q
```

The source reader supplies validated row order and parsed affinities. This lab extracts only the `Protein 1` and `Protein 2` labels from the same validated primary values. A row counts for a pair when at least one parsed affinity exists and both labels are present. Exact labels are kept apart, so aliases are not silently merged. Pair order is ignored. The per-protein count is a row count, while partner count deduplicates the opposite labels.

The committed summary records archive counts, the partner distribution, comparable pairs and a complete per-protein table. `show` prints the same table. A pair is called comparable only when both proteins have more than one observed partner. This is a coverage test, not a margin estimate. The table does not supply measurements for unobserved alternatives or justify a ranking by row count.

Original lab code is Apache-2.0 and original guide prose is CC BY 4.0. The upstream data retain their own terms. No reader outcome has been observed.
