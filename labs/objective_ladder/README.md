# Objective ladder for public records

This CPU-only lab reads public records for six examined entities against six distinct objectives. It names the record that carries evidence at each level and gives a reason when a cell is empty. It does not predict a value, rank entities, or establish a reader outcome.

## Data and provenance

The lab reads UniProtKB sequences and annotations, RCSB Protein Data Bank structures and coordinates, AlphaFold Protein Structure Database model metadata, and measured-affinity rows from SKEMPI 2.0. The RCSB search returns candidate structures. An affinity row is used only when the entry itself links its structure to the examined accession. Sequence recovery is counted over the archive-aligned deposited region, not over the whole reference.

The SKEMPI input is the public [LiteFold mirror](https://huggingface.co/datasets/LiteFold/SKEMPI2) of the [upstream table](https://life.bsc.es/pid/skempi2/). Its snapshot is 6148969 bytes and holds 7085 rows. The shared positional reader handles the mirror's partial records, and the snapshot's byte length is checked on every run. A row without a parsed affinity value is not treated as a measured value.

The committed reading was computed on 2026-10-22 from records read on 2026-10-22 on a machine with Python 3.11.15, numpy 2.4.6, and scipy 1.17.1.

## Frozen protocol

The contract fixes the six objectives, six accession and structure pairs, source routes, and coordinate-audit tolerances. The structural audit uses a 2.0 angstrom clash distance, a 0.45 angstrom bond-length tolerance, and a minimum of 500 coordinate rows. It counts all audited rows and the subset belonging to the examined entity. The sequence audit compares deposited and reference positions only within the archive alignment. The binding cell needs a measured value in a row whose structure is linked to the accession. A model prediction, a bound component, and an annotation cannot replace evidence at a different objective.

## Setup

Use the project Python environment from the repository root. The first download requires network access to the public archives. Subsequent analysis uses `.cache/objective_ladder/`, with the affinity snapshot under `.cache/objective_ladder/skempi/`. All reading and tests run on CPU. A successful export overwrites the committed small summary, so use it only when refreshing that artifact intentionally.

## Reproduce

Mode is fresh independent computation under the frozen protocol. The download fetches and caches the declared records. The inspector displays every objective, then checks a fresh reading against the committed summary. Export writes the summary after the checks, and the final command runs the laboratory tests. Run the commands in order.

```bash
.venv/bin/python labs/objective_ladder/run_lab.py download
.venv/bin/python labs/objective_ladder/inspect_objective_ladder.py show
.venv/bin/python labs/objective_ladder/inspect_objective_ladder.py check
.venv/bin/python labs/objective_ladder/export_summary.py
.venv/bin/python -m pytest labs/tests/objective_ladder -q
```

The download cache is reused when its records are present. The inspector and tests do not replace the committed summary. The export writes `labs/objective_ladder/summary.json` after a successful reading.

## What to inspect

The committed summary resolves 36 cells across six entities and six objectives. A record occupies 31 cells and 5 are empty. Sequence recovery, folding, structural plausibility, binding, catalysis, and function have records for 6, 6, 6, 3, 4, and 6 entities respectively. Inspect the position counts beside sequence fractions, the examined-entity row count beside each full coordinate audit, and the reason attached to every empty cell. The single DHFR clash belongs to the entry's NADPH cofactor, not to the examined entity. The ABCD1 accession has 7 catalytic-activity annotations but 2 distinct catalogue numbers.

## Source terms

UniProtKB is CC BY 4.0. RCSB Protein Data Bank is CC0 1.0. AlphaFold Protein Structure Database is CC BY 4.0, allows academic and commercial use, and expects attribution to EMBL-EBI. Its catalogue record is `db-alphafold-db`. The [SKEMPI 2.0 upstream terms](https://life.bsc.es/pid/skempi2/info/terms) state CC BY 4.0. The [LiteFold mirror card](https://huggingface.co/datasets/LiteFold/SKEMPI2) labels its own licence field `other`. Attribute SKEMPI 2.0 and the Barcelona Supercomputing Center when redistributing source or derived material. Original guide prose is CC BY 4.0 and original lab code is Apache-2.0.

## Limitations

The reading describes public records available on the stated date. A match fraction covers only the aligned region, a deposited structure observes one experimental state, and a geometry audit checks the coordinate file rather than the depicted fold. A model output is a prediction, a bound component is not a measured affinity, and a catalytic or functional annotation is not a measured rate or a substitute for the other objectives. The lab predicts or scores no value and does not rank entities. No reader outcomes have been observed.
