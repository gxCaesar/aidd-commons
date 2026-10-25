# Relative free-energy network audit

This CPU-first laboratory reads the eight OpenFE JACS-set network archives in [Zenodo record 21797903](https://zenodo.org/records/21797903). It joins each transformation to its protocol results through archive references, pairs the complex and solvent legs of the same ordered ligand transformation, and checks a deterministic fundamental cycle basis. The endpoint is relative binding free energy. The code does not calculate an absolute binding free energy or compare an assay endpoint.

## Environment and snapshot

Use the project's Python 3.11 environment. The source archives are CC BY 4.0. Original laboratory code is Apache-2.0. The record metadata, licence, file names and byte lengths were read on 2026-10-23. `download` retains the validated archives in a separate local cache. A reader who carries this cache can run the inspection and export commands without network access or an accelerator. Each file is checked against its protocol byte length and object references before it enters the cache.

## Fresh independent computation

Run from the repository root. `download` reuses validated local copies. `show` and `check` only read files. `export_summary.py` replaces the small committed summary after the archive and summary invariants pass. None of these commands replaces author results from another laboratory.

```bash
.venv/bin/python labs/free_energy_network_audit/run_lab.py download
.venv/bin/python labs/free_energy_network_audit/inspect_free_energy_network_audit.py show
.venv/bin/python labs/free_energy_network_audit/inspect_free_energy_network_audit.py check
.venv/bin/python labs/free_energy_network_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/free_energy_network_audit -q
```

For each leg, the reader selects the highest recorded generation within each of 3 distinct repeat IDs and averages those 3 estimates. A unit record without an estimate is counted separately. A binding edge uses complex minus solvent for the same ordered ligand mapping. Its uncertainty is the quadrature sum of the leg standard errors. Each leg standard error is the larger of the propagated reported error of the repeat mean and the between-repeat standard error. This rule is frozen in the protocol before inspecting cycle residuals.

A sorted spanning forest defines one fundamental cycle for each non-tree binding edge. The signed sum of its edge estimates is compared with twice the quadrature sum of its edge standard errors. A cycle with an absolute discrepancy above that tolerance is failed. It remains named and sized in the summary. This is a consistency check under an independence assumption, not a test of experimental truth or proof of convergence. The cycle basis is not the set of all simple cycles.

The committed computation on 2026-10-23 recovered 566 transformation edges and 1698 unit estimates. It found 92 fundamental cycles, of which 87 closed and 5 failed. The summary retains all 5 failed cycle names and discrepancy sizes. It also records 29 source unit records without an estimate, which are not silently promoted into estimates. The `show` command prints every cycle and its signed sum, standard error, tolerance and classification.

No reader learning outcome has been observed. The archives and this audit do not establish absolute binding free energies, experimental affinities, or a ranking of the eight systems.
