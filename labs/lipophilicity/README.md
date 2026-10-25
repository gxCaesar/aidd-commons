# Lipophilicity: notebook-first student lab

[中文说明](README.zh-CN.md)

This is the real-data continuation of the [synthetic modelling sandbox](../student_modelling/README.md).
The standalone teaching notebook implements data inspection, scaffold splitting,
features, training, selection, paired error comparison, plots, and report export.
It has executed in fresh local kernels on a constructed 20-molecule fixture.
The English notebook also completed one local CPU run on the real 4,200-row
dataset on 9 September 2026. **Execution in Colab has not been verified.**
The intended lesson is to compare simple molecular representations on measured
logD at pH 7.4, then explain errors without changing the test protocol.
This is an educational exercise, not a new method, prospective discovery, or SOTA result.

## Start with the notebook

Open the [English notebook](lipophilicity_tutorial.ipynb) or
[Chinese notebook](lipophilicity_tutorial.zh-CN.ipynb). Download one file, open
[Google Colab](https://colab.research.google.com/), sign in, and choose
**File → Upload notebook**. Save your own copy and use a CPU runtime. Each notebook
contains its dependencies, download step and visible core functions; no auxiliary
Python-file upload, repository clone, API key or Drive mount is required.
There is no published repository link yet, so this is an upload route, not a
verified one-click Colab badge. Google describes temporary runtimes and variable
resource availability in the [Colab FAQ](https://research.google.com/colaboratory/faq.html).

For local Jupyter, select the project's Python kernel:

```sh
uv sync --python 3.11
uv run jupyter lab labs/lipophilicity/lipophilicity_tutorial.ipynb
```

The setup cell installs missing or mismatched pinned packages into the active
environment. Use a dedicated local environment; if a changed dependency was already
imported, restart as instructed. Full notebook execution creates a fresh temporary
output directory. Re-running export cells replaces files only within that directory.
Download `summary.json`, `split-membership.csv`, `test-predictions.csv`, and
`prediction-errors.png` before the runtime expires. The notebook does not write to
any existing lab result directory.

English and Chinese use identical executable cells. `tutorial.py` owns the small
tested functions; `build_notebooks.py` embeds their source into the teaching cells
so readers can inspect and edit them. For maintainers, rebuild both editions after
editing those sources:

```sh
uv run python labs/lipophilicity/build_notebooks.py
uv run pytest labs/tests/test_lipophilicity_tutorial.py labs/tests/test_lipophilicity_notebook.py -q
```

## Source and reuse

- Original deposit: AstraZeneca physicochemical data, [ChEMBL document CHEMBL3301361](https://www.ebi.ac.uk/chembl/api/data/document/CHEMBL3301361.json), DOI [10.6019/CHEMBL3301361](https://doi.org/10.6019/CHEMBL3301361).
- Relevant original measurement: [CHEMBL3301363](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL3301363.json), octanol/water distribution at pH 7.4, shake-flask measurement, reported experimental range −1.5 to 4.5.
- Teaching table: `Lipophilicity.csv` at the URL used by the [DeepChem 2.8.0 loader](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/molnet/load_function/lipo_datasets.py). Columns are `CMPD_CHEMBLID`, `exp`, and `smiles`; `exp` is logD, **not** binding affinity, pChEMBL, logP, or solubility.
- ChEMBL's [dataset licence](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/LICENSE) declares CC BY-SA 3.0. Attribute the original deposit and the MoleculeNet/DeepChem curation. The repository code licence does not relicense third-party data. This package supplies download instructions, not a redistributed data copy.

Verified on 9 September 2026: the download was 0.283 MB and the server reported
`Last-Modified: Fri, 10 Jul 2020 06:42:23 GMT`. The loader source is versioned;
the CSV URL is not an immutable data release. Keep your dated local download.
Do not replace it silently if the server changes. The current ChEMBL API also
reports 4,200 activities for this assay, but a full record-by-record join between
that API and the historical teaching CSV has **not** been performed. Do not call
the CSV a newly exported ChEMBL release.

## Run the preparation stage

From the repository root, use the existing Python 3.11 environment described in
the [main README](../../README.md). No DeepChem installation is needed; the
inspector uses RDKit from the pinned project environment.

```sh
uv sync --python 3.11
intake_dir=$(mktemp -d "${TMPDIR:-/tmp}/aidd-lipo.XXXXXX")
curl --fail --location --max-time 60 \
  https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/Lipophilicity.csv \
  --output "$intake_dir/Lipophilicity.csv"
uv run python labs/lipophilicity/inspect_data.py "$intake_dir/Lipophilicity.csv"
uv run pytest labs/tests/test_lipophilicity_intake.py -q
```

Keep the download command and local directory with your own working notes. The
inspector only reads the named CSV and prints JSON. It neither downloads nor
writes files, excludes records, assigns splits, constructs training features,
or fits a model. Missing fields, duplicate compound IDs, invalid structures,
non-finite labels, and an empty dataset fail explicitly. Repeated canonical
structures are counted, not silently merged.

## Observed intake

The command above was run on the dated download with RDKit 2025.09.6.

| Quantity                                        |      Observed |
| ----------------------------------------------- | ------------: |
| Rows / unique ChEMBL IDs                        | 4,200 / 4,200 |
| Unique canonical isomeric SMILES                |         4,200 |
| Repeated canonical structure groups             |             0 |
| Nonempty nonchiral Bemis–Murcko scaffold groups |         2,407 |
| Largest nonempty scaffold group                 |       76 rows |
| Acyclic molecules with an empty scaffold        |             5 |
| Multicomponent structures                       |             1 |
| Target range                                    |   −1.5 to 4.5 |

These counts do not establish 4,200 independent experimental replicates.
Compounds share chemistry and assay conditions; the CSV has no replicate,
batch, or experimental uncertainty columns. Canonical SMILES identity also
does not establish parent-compound, tautomer, or protonation-state equivalence.

The multicomponent record is `CHEMBL3545252` and includes three disconnected
water fragments. Inspection preserves it as supplied. Removing fragments would
change the representation and must be an explicit preprocessing decision.
There is one value at −1.5 and four at 4.5. The CSV has no inequality/qualifier
field; sampled ChEMBL endpoint records have a null relation. Neither fact
proves these measurements are exact uncensored values. Keep them and state this
limitation rather than dropping them after seeing prediction errors.

## Implemented teaching protocol

These choices define the notebook's default exercise. Constructed-fixture
execution verifies the engineering flow, not performance on the real assay.

1. **Question:** how do simple 2D representations compare when held-out molecules
   have scaffolds absent from training? Keep the supplied labels and structures,
   including the multicomponent record. No salt stripping, tautomer merging,
   target clipping, or error-dependent exclusion in the primary exercise.
2. **Split:** reproduce the nonchiral scaffold grouping and deterministic group
   ordering of the [DeepChem 2.8.0 `ScaffoldSplitter`](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/splits/splitters.py), with requested fractions
   0.8/0.1/0.1 in original CSV order. Keep all empty-scaffold rows in one group.
   Actual row fractions may differ because groups stay intact. Before any fit,
   save assignments and test ID, exact-structure, and scaffold disjointness.
   Implementing merely a similarly named splitter is not recipe parity.
3. **Baselines:** train mean; eight-descriptor Ridge (`MolWt`, `MolLogP`, `TPSA`,
   `NumHDonors`, `NumHAcceptors`, `RingCount`, `NumRotatableBonds`, `FractionCSP3`);
   and 2,048-bit radius-2 Morgan Ridge without chirality. `MolLogP` is only a
   feature, not a physical logD prediction. All preprocessing is fitted on
   training data only. Descriptor scaling centers and scales; bit scaling uses
   training variances without centering. The representation comparison includes
   these stated preprocessing differences; it is not an isolated causal ablation.
4. **Selection:** for each Ridge representation, compare alpha values
   `[0.1, 1, 10, 100]` using validation RMSE; ties choose the larger alpha.
   Use the existing scikit-learn environment, `solver="lsqr"`, `tol=1e-6`,
   `max_iter=10000`, and an intercept. Keep the selected training-only fit; do not
   refit on train plus validation. A convergence failure is reported, not hidden.
5. **Evaluation:** RMSE is primary, MAE secondary, both in logD units. Read the
   test once after selection. Compare methods on the same test molecules;
   uncertainty uses whole test-scaffold groups rather than treating model
   repetitions as samples. With seed 20260909, resample G groups G times with
   replacement for 2,000 draws and recompute molecule-weighted RMSE differences.
   Report the 2.5th/97.5th percentile interval for each Ridge minus the train mean
   and descriptors minus Morgan. These are fixed-model conditional intervals,
   assuming exchangeable scaffold groups, with no multiplicity-adjusted
   significance claim. They omit training-set and assay variation. Fewer than
   two groups yields no interval; no rows or groups are silently dropped.
6. **Error explanation:** predeclare checks of endpoint records, the retained
   multicomponent record if held out, scaffold-group size, and train-neighbour
   similarity. These are descriptive diagnostics, not a route to retuning the
   same test. Report negative and worse-than-constant results.

The eight candidate fits and three final method evaluations are a bounded
CPU-first exercise, not a search over architectures. The local execution below
is not a controlled runtime benchmark. Data inspection is not model training.
Do not import or execute the existing frozen ChEMBL EGFR, FreeSolv, rMD17, or
pool-budget runners to start this lab.

## Scope decisions and next deliverables

- **Data fit:** feasible for the stated educational regression task;
  structure, ID, and target coexist in all 4,200 rows. Batch-level independence
  and assay-to-assay validation are not supported by this CSV.
- **Existing work:** the prediction task is already a public benchmark, so no
  task or method novelty is claimed. No exhaustive new-method novelty search
  was performed.
- **Contribution:** teaching infrastructure within AIDD Commons, not a standalone
  top-CS or Nature-family scientific result.

## Observed local notebook execution

On 9 September 2026, all 12 English code cells completed in a fresh local Python
3.11 kernel with the pinned dependencies and a single-threaded BLAS configuration.
The unchanged protocol assigned 3,360 training, 420 validation and 420 test rows,
with no exclusions. Both Ridge representations selected alpha 100 on validation.

| Method           | Test RMSE | Test MAE |
| ---------------- | --------: | -------: |
| Train mean       |  1.122067 | 0.930171 |
| Descriptor Ridge |  0.976236 | 0.777160 |
| Morgan Ridge     |  1.243239 | 0.940115 |

These logD errors describe one fixed split and recipe, not a general ranking of
molecular representations. Morgan Ridge was worse than the constant baseline;
the alpha grid was not expanded after viewing the test. All test scaffolds were
singleton groups. Three test molecules had a 2,048-bit Morgan fingerprint identical
to a training molecule despite different canonical structures and scaffolds:
`CHEMBL1807872`, `CHEMBL1682822`, and `CHEMBL1732699`. Scaffold isolation does not
guarantee representation isolation or dissimilar chemistry.

The runner exited with code 0; all cells had execution counts and no cell errors.
Recalculation from exported predictions matched every RMSE and MAE. ID, canonical
structure and scaffold isolation, label alignment and the train-only mean passed
post-run checks. The prediction plot and molecule SVG rendered. Code-cell timestamps
span about 20 seconds, including imports and plotting; this is not training-only
timing. The local sandbox emitted font-cache warnings and a kernel shutdown
process-enumeration permission error after cell execution. No rerun was performed.
Actual Colab execution, the cloud download/install path, and peak training memory
were not measured by this run.

The notebook's tests use invented labels on 20 molecular structures, execute both
languages in fresh kernels, and change held-out labels to check that validation
selection and predictions remain invariant while errors change. This is an
engineering test, not a second experimental result. Actual Colab validation and
external publication remain separate next steps.
