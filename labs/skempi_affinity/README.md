# SKEMPI affinity table structure

This CPU-only lab counts rows and independent complexes in a public SKEMPI 2.0 mirror, audits partial JSONL records, and compares two fixed affinity predictors on held-out complexes. It does not establish prospective predictive performance or any therapeutic result.

## Data and provenance

The canonical source is [SKEMPI 2.0](https://life.bsc.es/pid/skempi2/). The publicly downloadable [LiteFold mirror](https://huggingface.co/datasets/LiteFold/SKEMPI2) carries the table as JSONL. The upstream [terms](https://life.bsc.es/pid/skempi2/info/terms) say Creative Commons Attribution 4.0 International Public License. The mirror card labels its own licence field `other`. Its primary value is ragged because comma-split overflow fragments appear in additional `column_N` keys. The reader records those fragments and right-pads the primary semicolon-delimited value. It never treats overflow text as verified field reconstruction.

## Frozen protocol

The frozen contract names the snapshot byte length, source fields, positional alignment, complete affinity pair rule, complex-level holdout, fixed seed, group-only training median, observed-mutant comparator and log10(M) absolute-error metrics. All fitting uses training complexes. The row split is a diagnostic for overlap, not the evaluation split.

## Setup

Use the project Python 3.11 environment. The first download needs network access. Analysis and tests need only the local cache, and all calculations run on CPU.

## Reproduce

Mode is fresh independent computation under the frozen protocol. Run from the repository root.

```bash
.venv/bin/python labs/skempi_affinity/run_lab.py download
.venv/bin/python labs/skempi_affinity/inspect_skempi_affinity.py show
.venv/bin/python labs/skempi_affinity/inspect_skempi_affinity.py check
.venv/bin/python labs/skempi_affinity/export_summary.py
```

The download writes the 6,148,969-byte snapshot under `.cache/skempi_affinity/`. A repeat validates the cached byte length and keeps the same file. The export writes `labs/skempi_affinity/summary.json` and overwrites that summary on every successful run. No results directory is created by these commands. A contract failure exits before the summary is written.

## What to inspect

Compare row counts with distinct complexes, then inspect field-count distribution and complete affinity pairs. The five largest complexes account for 347 of 830 AB/AG rows in the observed 2026-10-21 run. The row-split diagnostic counts test rows whose complex is also in training. The held-out metrics use disjoint complexes and report both row-weighted and complex-mean absolute error. An independent exercise is to explain why a 51-complex subset cannot support an interval with 830 independent units.

## Source terms

Attribute SKEMPI 2.0 and the Barcelona Supercomputing Center when redistributing the source or derived material. Read the [upstream licence terms](https://life.bsc.es/pid/skempi2/info/terms) and the [mirror card](https://huggingface.co/datasets/LiteFold/SKEMPI2) separately.

## Limitations

The primary-value rule deliberately does not reconstruct overflow fragments, so a partial mirror record is not evidence that an upstream measurement was never made. The split demonstrates the independent-unit issue for this table, while two simple comparators do not establish model superiority. No reader outcomes have been observed.
