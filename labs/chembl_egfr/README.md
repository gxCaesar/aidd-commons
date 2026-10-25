# ChEMBL 37 EGFR representation baselines

This CPU-first lab compares two frozen, low-capacity molecular representations
for a human EGFR binding endpoint. It is a protocol and evaluation lesson, not
a leaderboard or a SOTA claim.

The public reviewed state is:

- development pretest: passed on 2026-09-05;
- primary scaffold-disjoint evaluation: completed on 2026-09-08;
- assay-level replication: completed on 2026-09-08.

## Frozen contract

The protocol version is `chembl37-egfr-representation-v1`.

- Source: ChEMBL 37, primary assay `CHEMBL5736995`, replication assay
  `CHEMBL3705421`.
- Endpoint: exact standardised IC50 measurements in nM with a non-null
  `pchembl_value`, `standard_flag=1`, `potential_duplicate=0`, and no
  `data_validity_comment`. The reported pChEMBL and nM value must agree within
  the frozen 0.011 pChEMBL tolerance.
- Entity: a ChEMBL parent molecule whose activity record already supplies the
  parent structure; repeated measurements are aggregated by their median.
- Representations: 214 frozen RDKit 2D descriptors and a 2,048-bit binary
  Morgan fingerprint with radius 2 and chirality enabled.
- Models: train mean, descriptor Ridge, and Morgan Ridge. Ridge `alpha` is
  selected from `[0.001, 0.01, 0.1, 1, 10, 100, 1000]` by validation MAE.
- Split: whole chirality-aware RDKit Bemis-Murcko scaffold groups, assigned in
  deterministic size-first order to 70% train, 15% validation, and 15% locked
  primary evaluation targets.
- Metrics: MAE, RMSE, and tied-rank Spearman correlation in pChEMBL units.

The machine-readable contract is in `protocol.json`. The aggregate-only,
reviewed development evidence is in `development-summary.json`.
The completed locked aggregate is in `locked-summary.json`; it is separate from
the unchanged historical development summary.

The additive `execution-amendment.json` (execution v1.1, 2026-09-08) supersedes
only the original contract's ambiguous "without refitting or retuning" wording.
The original protocol and development evidence are retained unchanged. The
amendment does not change the data, splits, grid, selected alphas, or metrics.

## Setup

From the repository root:

```sh
uv sync --group dev
```

The supported environment is Python 3.11 with the exact direct dependency
versions declared in `pyproject.toml`.

The source-download and development-pretest instructions below are for a fresh
workspace only. Do not use this completed author workspace to reconstruct or
rerun the study: its one-time marker remains present, so pretest and locked
evaluation reject after the completed paired result. Downloading again here
would not add evidence to that result.

## Download the frozen source snapshot in a fresh workspace

```sh
env UV_CACHE_DIR=.cache/uv uv run python labs/chembl_egfr/run_lab.py download
```

The command reads official ChEMBL JSON endpoints, checks the release and assay
metadata, verifies the frozen row counts, and writes a local cache under
`.cache/chembl_egfr/`. That cache is local execution material and is excluded
from the public release. This convenience route is intentionally time-bounded:
it refuses to continue once the live status endpoint no longer reports
`ChEMBL_37`.

### Reproduce after the live API advances

The durable source is the official, versioned
[ChEMBL 37 release directory](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/).
Acquire `chembl_37_sqlite.tar.gz` from that directory and use its adjacent
`schema_documentation.txt`, release notes, README, and licence. Query the two
frozen assay IDs and apply the endpoint, parent, structure, and median rules in
`protocol.json`; the query, retained-row, parent, and scaffold counts must match
before fitting anything.

The current CLI does not automate SQLite-archive import. If the live API has
advanced, treat `download` as unavailable until that importer is implemented;
do not weaken the version assertion or substitute a newer release while keeping
the ChEMBL 37 protocol name.

## Run the development pretest in a fresh workspace

```sh
env UV_CACHE_DIR=.cache/uv uv run python labs/chembl_egfr/run_lab.py pretest
```

The pretest constructs the scaffold split, fits preprocessing and models on
training molecules only, selects Ridge regularisation on validation scaffolds,
and writes a full local development artifact. It parses the public records to
enforce entity, count, and split contracts, but only training and validation
records enter fitted-model or metric paths. The locked targets are not scored.

The reviewed public summary intentionally omits molecule IDs, structures,
predictions, memberships, and fit traces. Validation values are model-selection
evidence only.

## Historical locked-evaluation boundary

In a fresh independently authorized workspace, the historic command required
explicit approval. Do not run it in this completed author workspace:

```sh
env UV_CACHE_DIR=.cache/uv uv run python labs/chembl_egfr/run_lab.py evaluate-locked --confirm-locked-evaluation
```

`evaluate-locked` evaluates the primary held-out scaffold partition and the
separate-assay replication in one invocation. It reconstructs the original
train-only models once by replaying the frozen development grid, then requires
exact equality with the complete stored pretest, including selected alphas,
validation predictions, memberships, and software. This is deterministic
reconstruction of an already fixed choice, not a new search or permission to
change the choice. The same reconstructed model objects are reused for both
locked evaluations. There is no train-plus-validation refit and no locked-label
feedback into selection. An unconfirmed invocation exits before loading data.
A local one-time marker prevents selective or repeated evaluation through the
provided CLI. ChEMBL labels are public, so this is a procedural workflow guard
rather than a cryptographic blind. The paired evaluation has completed once;
the marker remains and must not be removed or rerun in this workspace.

## Completed paired evaluation

[`locked-summary.json`](locked-summary.json) is the sanitized public aggregate.
It contains no parent identities, structures, prediction vectors, cache paths,
or execution receipt. Its projection command reads only the completed local
metrics and does not refit or evaluate:

```sh
uv run python labs/chembl_egfr/export_locked_summary.py
```

| Set                                  | Parents | Model            |       MAE (pChEMBL) |
| ------------------------------------ | ------: | ---------------- | ------------------: |
| Primary scaffold-disjoint evaluation |     132 | train mean       | 0.47889315075040634 |
| Primary scaffold-disjoint evaluation |     132 | descriptor Ridge |  0.4685270107977128 |
| Primary scaffold-disjoint evaluation |     132 | Morgan Ridge     | 0.41833032711934154 |
| Separate-assay replication           |     170 | train mean       |   0.898379755056597 |
| Separate-assay replication           |     170 | descriptor Ridge |    0.57926487123557 |
| Separate-assay replication           |     170 | Morgan Ridge     |  3.1316760122202343 |

Morgan Ridge is lowest on the primary evaluation but highest on the separate
assay. Descriptor Ridge is lowest on the separate assay. This is not a uniform
representation ranking, a SOTA result, or evidence of cross-assay transport.
All six MAE/RMSE/Spearman sets were recomputed from the 302 saved evaluation
rows; the public aggregate remains row-free. T15 had already accessed labels
shared with T05, so this completed run is not an untouched independent T05
confirmation. No retuning followed that exposure.

## What to inspect

1. Confirm that every learned transform and model is fit on training IDs only.
2. Compare target split sizes with realised sizes after whole-scaffold
   assignment.
3. Inspect duplicate-parent label ranges before interpreting achievable error.
4. Treat an `alpha` selected at the edge of the frozen grid as a limitation,
   not an invitation to expand the grid after seeing validation outcomes.
5. Keep the primary and replication results separate in interpretation.

## Source terms

ChEMBL 37 database content is distributed under CC BY-SA 3.0. Cite the ChEMBL
resource URL and version when using the data. Original AIDD Commons code is
Apache-2.0 and original prose is CC BY 4.0; those licences do not replace the
terms of ChEMBL or contributed upstream sources.

- [ChEMBL 37 README](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/README)
- [ChEMBL 37 SQLite archive](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/chembl_37_sqlite.tar.gz)
- [ChEMBL 37 schema documentation](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/schema_documentation.txt)
- [ChEMBL 37 licence](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE)
- [Primary assay record](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL5736995.json)
- [Replication assay record](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL3705421.json)
