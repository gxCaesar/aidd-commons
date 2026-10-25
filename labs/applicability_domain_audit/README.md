# FreeSolv applicability-domain diagnostic

This CPU-only lab asks whether a deliberately simple property model makes larger
errors for test molecules farther from its training molecules in a chosen
representation. It reports a distance and an observed error contrast. It does
not define an applicability domain or certify a new prediction.

## Data and frozen protocol

The input is `.cache/freesolv/freesolv-v0.52-database.txt`, the local copy of
[FreeSolv v0.52](https://raw.githubusercontent.com/MobleyLab/FreeSolv/v0.52/database.txt).
It was read on 2026-10-23 and is 144897 bytes. The release DOI is
[10.5281/zenodo.1161245](https://doi.org/10.5281/zenodo.1161245).
The v0.52 release metadata does not declare licence terms. Current repository
licences are not evidence of this release's terms. The loader checks byte length,
header and molecular records. A same-length alteration is beyond this guard.

`protocol.json` freezes the source, the representation, the distance, the split,
and the baseline. Both the JSON and compiled contract must match. The cohort is
the measured hydration free energy in the fourth semicolon-delimited field,
in kcal/mol. Canonical isomeric SMILES identify molecules.

The laboratory groups Bemis-Murcko scaffolds, using an individual canonical
SMILES key for each acyclic molecule. With seed `20260904`, it sorts groups by
descending size, shuffles sorted equal-size keys, and assigns whole groups to
training until the rounded 80% molecule target is reached. The remainder is
test. This is a fresh two-way split for this diagnostic, distinct from the
existing FreeSolv laboratory's frozen train/validation/test evaluation.

Ridge regression with `alpha=1.0` uses chirality-aware Morgan fingerprints of
radius 2 and 2048 bits. These choices reuse the curriculum's cheap baseline.
The diagnostic distance uses RDKit MolWt, MolLogP, TPSA, NumHDonors and
NumHAcceptors. Each absolute property difference is divided by that property's
population standard deviation in training, or by 1 if the deviation is zero.
The five values are averaged and the nearest training molecule supplies each
test molecule's distance. This representation and distance are laboratory
choices, not a chemistry-defined domain.

## Reproduce and inspect

Mode is fresh independent computation over a frozen protocol. Use the project
Python 3.11 environment and the existing local release. No network or accelerator
is needed. `check` and `show` write nothing. The exporter overwrites only the
small committed `summary.json` after validation passes.

```bash
.venv/bin/python labs/applicability_domain_audit/run_lab.py check
.venv/bin/python labs/applicability_domain_audit/inspect_applicability_domain_audit.py show
.venv/bin/python labs/applicability_domain_audit/inspect_applicability_domain_audit.py check
.venv/bin/python labs/applicability_domain_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/applicability_domain_audit -q
```

`show` prints cohort and split counts, the median and quartiles of test
distances, the most distant test molecule's nearest and farthest training
comparisons, and median absolute error in the smaller-distance and
larger-distance halves. The exporter retains aggregates and the named extreme
pair, with no per-molecule table. All observed numbers belong to this release,
split, representation and baseline.

## Interpretation and limits

The median error contrast is descriptive for this held-out scaffold sample. A
distance can miss changes in stereochemistry, charge context or other chemistry
not captured by these five properties. Some distinct structures can have very
similar computed properties. No threshold is calibrated, no better model is
fitted and the test errors do not estimate performance for a particular new
molecule. A random split would answer a different question because related
scaffolds could occur on both sides.

Original code is Apache-2.0 and original documentation is CC BY 4.0. RDKit's
recorded source-code licence is BSD-3-Clause. Third-party components retain
their own terms. Last reviewed on 2026-10-23.
