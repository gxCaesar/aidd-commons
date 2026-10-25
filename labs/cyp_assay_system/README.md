# CYP3A4-versus-CYP2D6 assay-system lab

This lab compares real, measured IC50 potency against two different cytochrome P450 enzymes,
CYP3A4 and CYP2D6, for every ChEMBL 37 parent molecule with an admitted record against both. It
is a descriptive read of already-published measurements: no model is fitted, no split is drawn,
and no train/test evaluation happens anywhere in this lab.

## Frozen contract

The protocol version is `chembl37-cyp-assay-system-v1`, in [`protocol.json`](protocol.json). It
reuses, unmodified, the admission rule already established by `labs/chembl_egfr/protocol.json`:
exact IC50 in nM, `standard_flag=1`, `potential_duplicate=0`, no data validity comment,
`molecule_chembl_id` equal to `parent_molecule_chembl_id`, an RDKit-valid structure, and pChEMBL
consistent with the reported nM value within a 0.011 tolerance. Unlike the EGFR lab, this reads
two whole ChEMBL targets (`CHEMBL340`, CYP3A4; `CHEMBL289`, CYP2D6) rather than two named assays,
because a single CYP target's IC50 record set is itself spread across many independent assays and
documents. Repeated admitted activities for one parent under one target are aggregated by their
median; a "clean single pair" additionally requires exactly one admitted activity per target for
that parent, from the same document, so its two pChEMBL values are not a median over multiple
studies on either side.

## Setup

From the repository root:

```bash
uv sync --group dev
```

## Running

```bash
uv run python labs/cyp_assay_system/run_lab.py download
uv run python labs/cyp_assay_system/inspect_cyp_assay_system.py show
uv run python labs/cyp_assay_system/inspect_cyp_assay_system.py check
uv run python labs/cyp_assay_system/export_summary.py
```

`download` fetches and caches the live ChEMBL status endpoint and both targets' full activity
pages to `.cache/cyp_assay_system/` (git-ignored). It re-validates the release fields on every
run, so a cache written under an older admission rule is re-checked rather than silently trusted.
`show` reports the admission audit for each target, the overlap counts, both correlation summaries
(full overlap and the clean-pair subset), and the most divergent named examples in each direction.
`check` recomputes the structural invariants (exclusion counts partition the input rows, overlap
is exactly the set intersection of the two targets' admitted parents, every clean pair is also a
full-overlap record) and exits non-zero on failure. `export_summary.py` writes the small, committed
[`summary.json`](summary.json): counts, audits, both correlation summaries and three named
examples each way, with no raw activity rows or bulk compound lists.

## What this does not show

This protocol reads only in vitro IC50 inhibition records. It says nothing about transporters,
enzyme induction, metabolite identification or a clinical drug-drug-interaction outcome for any
named drug pair, and it applies no correction for cross-study heterogeneity beyond the same-document
"clean pair" comparison it already declares. See `protocol.json`'s `excluded_by_design` for the
complete, machine-readable list.

## Results (computed 2026-09-12, live ChEMBL 37, release 2026-05-01)

| Target | Admitted parents |
| --- | ---: |
| CYP3A4 (`CHEMBL340`) | 5,251 |
| CYP2D6 (`CHEMBL289`) | 2,781 |

Parents admitted under both targets: 1,195 (1,186 sharing at least one document; 1,015 clean
single pairs). Spearman rho over the full overlap is 0.2981 (p=6.08e-26); over the clean-pair
subset, 0.3038 (p=4.10e-23). The two estimates agree with each other as a robustness check, and
both are positive and far from either 0 or 1: apparent CYP3A4 potency is a weak positive signal
for CYP2D6 potency in this real dataset, not a strong predictor and not independent noise.

Named examples from the clean-pair subset: albaconazole (`CHEMBL298817`) is markedly CYP3A4-
selective (pIC50 7.40 vs. 4.50 in the same document). Quinidine (`CHEMBL1294`) is not a clean
pair at all, which is itself the point: it carries only one admitted CYP3A4 record (pIC50 4.55)
against 32 independent CYP2D6 records spanning a pIC50 range of 4.1, that is, more than a
10,000-fold range in reported potency (median pIC50 7.37). A single-sentence claim such as
"quinidine inhibits CYP" would have to say which enzyme, which assay and which document before it
means anything at all; the full detail is in `summary.json` and reproducible with
`inspect_cyp_assay_system.py show`.
