# ROSETTA cross-modality agreement lab

This lab asks one question about real data: for a genetic perturbation measured in two
readouts at once, the L1000 transcriptomic profile and the Cell Painting imaging profile,
how strongly do the two readouts agree, and how much of that agreement survives when the
plate and batch structure of the measurement is accounted for? It joins the two readouts
for 528 real perturbations, measures the agreement, and then repeats the measurement with
the whole batch or the whole plate held out of the training side, next to a control that
has the same training and test sizes but no structural separation, so that a reader can
tell a design effect from a smaller training set. It is a descriptive read of
already-published measurements: no target is nominated, no phenotype is predicted, and no
model is offered for use.

**What this does not show.** It does not show that a perturbation signature is a mechanism.
It does not show that the imaging readout can be predicted for a perturbation the model has
never seen in any real deployment, because the holdouts here are holdouts inside one
published experiment. It does not separate the batch's nuisance effect from the fact that a
batch-homogeneous training set covers less of the perturbation space, and it says nothing
about any gene, any patient, or any clinical outcome. The named perturbations at the ends
of the agreement distribution are the ends of a distribution, not evidence about biology.

## Data and provenance

Both objects come from one study of the Broad Cell Painting Gallery, `cpg0003-rosetta`, and
from one batch of it, `LUAD-BBBC041-Caicedo`: A549 lung adenocarcinoma cells carrying
engineered genetic perturbations, read out 96 hours after the perturbation.

| Readout | Object | Bytes | Entity tag |
| --- | --- | ---: | --- |
| Transcriptome | `L1000/replicate_level_l1k.csv.gz` | 11,448,797 | `cca1d0129f0a8f94f322d0fded461225` |
| Imaging | `CellPainting/replicate_level_cp_normalized_variable_selected.csv.gz` | 15,858,878 | `c79982a1d6eca9480e707c8d64c50b43` |

Total: 27,307,675 bytes. The byte lengths and entity tags were read from the bucket's own
object listing on 2026-10-21 and are re-verified on every download and every load. The
transcriptomic file carries 4,232 wells on 16 assay plates and the imaging file 6,144 wells
on 16 assay plates drawn from two plate maps, which are the two batches of this batch of the
study.

The gallery also publishes a full-feature imaging release for the same batch
(`replicate_level_cp_normalized.csv.gz`, 84,400,417 bytes). This protocol does not use it:
every imaging feature in the variable-selected release has a finite value in every well, so
the feature set needs no further selection rule of its own, and the smaller object keeps the
lab inside a CPU-first budget. The lab makes no claim that its numbers transfer to the full
feature set.

The perturbation identifiers are the study's own. The transcriptomic file's `allele` column
names the edit (`STK11_p.G56W`), `pert_mfc_desc` names the gene (`STK11`), and the imaging
file's `Metadata_x_mutation_status` and `Metadata_Transcript` columns carry the same
perturbation under its own annotations.

## Frozen protocol

The protocol version is `cpg0003-rosetta-luad-cross-modality-v1`, in
[`protocol.json`](protocol.json). The parts a reader has to know before believing a number:

- **Entity.** One genetic perturbation that has at least one treated well in each readout,
  joined on the perturbation identifier both readouts carry (`pert_iname` and
  `Metadata_pert_name`). Control wells are read, counted and reported, and are never
  entities.
- **Profile.** One row per perturbation per readout: the median across that perturbation's
  replicate wells in that readout. Every perturbation therefore appears exactly once per
  readout, so no replicate of a perturbation can be split across a training and a test side.
- **Features.** The transcriptomic features are the 978 Affymetrix landmark probe sets, found
  by the naming rule `^\d+(?:_[a-z])?_at$`; the imaging features are the 291 Cell Painting
  features, found by the compartment prefixes `Cells_`, `Nuclei_` and `Cytoplasm_`. Every
  other column is annotation. Features are found by name, never by position, so a release
  that adds or drops a column is either read correctly or rejected.
- **Endpoint.** Cross-modal agreement: how well the transcriptomic profile of a perturbation
  predicts its imaging profile. Primary metric: the mean over held-out perturbations of the
  Pearson correlation between the predicted and the observed imaging profile. Secondary
  metric: the mean over imaging features of the correlation between predicted and observed
  values across the held-out perturbations of a fold.
- **Model and fit scope.** A multi-output ridge map, with the penalty chosen from a fixed
  grid by an inner five-fold cross-validation on the training rows of each fold. The
  standardisation and the penalty are fitted on training rows only; no held-out row
  influences its own map.
- **Split and grouping unit.** The unit of inference is one perturbation. The grouping units
  are the imaging assay plate, the imaging batch (the plate map) and the L1000 assay plate.
  Because each perturbation is measured on 8 of the 16 plates in each readout, a plate
  cannot be held out at the level of one perturbation; the blocked evaluations hold out
  every perturbation measured on a plate and train on every perturbation never measured on
  it.
- **Seed.** 20261021, which fixes every partition and every permutation.

## Setup

From the repository root:

```bash
uv sync --group dev
```

The lab needs NumPy, which is already in the pinned environment, and nothing else: the
ranking, the correlation and the ridge map are all written out rather than imported.
It reads two published objects over the network exactly once, into a cache that is
git-ignored.

## Reproduce

```bash
uv run python labs/rosetta_cross_modality/run_lab.py download
uv run python labs/rosetta_cross_modality/inspect_rosetta_cross_modality.py show
uv run python labs/rosetta_cross_modality/inspect_rosetta_cross_modality.py check
uv run python labs/rosetta_cross_modality/export_summary.py
```

`download` fetches the two published objects into `.cache/rosetta_cross_modality/`
(git-ignored) and re-validates their byte lengths against the frozen protocol on every run,
so a cache written under an older contract is re-checked rather than silently trusted. A
cache that is already the right size is not re-downloaded, and a download that was
interrupted resumes from the bytes already on disk instead of starting over.

`show` prints the committed summary readably and needs no data. `check` re-reads the cached
objects, recomputes the whole frozen evaluation set, and exits non-zero if any structural
invariant fails or if the committed summary no longer matches what the cached data produce.
It needs the cache present.

`export_summary.py` writes two files. `results/computed-summary.json` (git-ignored) is the
full run artefact and carries the agreement value of every individual perturbation.
[`summary.json`](summary.json) is the small committed projection: counts, the variance
attribution of plate and batch, the eight evaluations, the survival ratios and three named
examples at each end of the agreement distribution. It contains no raw well rows, no
per-perturbation values and no bulk lists of perturbation identifiers.

**Overwrite behaviour.** `download` overwrites a cached file only when the cached file is
missing or the wrong size; `export_summary.py` overwrites both of its outputs in place, and
it writes nothing at all if the contract or the data is refused. The summary is a one-time
evaluation: it was computed once from the cached objects and committed, and the protocol is
frozen at that state. The `check` subcommand exists so that a later reader can confirm the
committed summary still matches the cached data; it recomputes rather than updates, and a
mismatch is a failure rather than a silent refresh.

## What to inspect

The committed numbers, computed 2026-10-21 from the objects above:

| Evaluation | Perturbation r | Feature r | Folds | Perturbations tested |
| --- | ---: | ---: | ---: | ---: |
| Apparent (random five-fold) | 0.816 | 0.826 | 5 | 528 |
| Null, pairing destroyed within batch | 0.132 | 0.003 | 5 | 528 |
| Batch blocked (one whole batch held out) | 0.689 | 0.633 | 2 | 509 |
| Size-matched random, same sizes | 0.792 | 0.788 | 2 | 509 |
| Imaging plate blocked | 0.692 | 0.652 | 16 | 528 |
| Size-matched random, same sizes | 0.793 | 0.801 | 16 | 528 |
| Transcriptome plate blocked | 0.704 | 0.669 | 16 | 528 |
| Size-matched random, same sizes | 0.797 | 0.809 | 16 | 528 |

The counts first: 4,232 transcriptomic wells (4,224 treated, 8 control) over 528
perturbations and 16 plates; 6,144 imaging wells (5,824 treated, 320 control) over 593
perturbations and 16 plates drawn from 2 batches. 528 perturbations carry both readouts.
65 imaging perturbations have no transcriptomic counterpart and are excluded. 509 of the
admitted perturbations sit in one batch and 19 span both.

Then the agreement. The two readouts agree strongly: with a random split, the imaging
profile of a held-out perturbation is predicted from its transcriptomic profile at a
correlation of 0.816 per perturbation and 0.826 per imaging feature. That number is not a
design artefact: replacing each perturbation's imaging profile with another perturbation's
imaging profile from the same batch, which keeps the plate and batch structure and destroys
only the pairing, drops the agreement to 0.003 per feature. A model-free check agrees with
the fitted one without fitting anything or drawing a split: the median Spearman correlation
between the transcriptomic and the imaging similarity rankings is 0.745, against 0.001 for
the same statistic under the permuted pairing.

Then the design. What the plate and the batch do to the measured variance is small: the
imaging plate accounts for 2.71% of the imaging feature variance, the L1000 plate for 1.56%
of the transcriptomic feature variance, and the imaging batch for 0.36%. Small variance
share does not mean small effect on a prediction, so the agreement is measured again with
the structure held out. Holding out one whole batch drops the per-feature agreement from
0.826 to 0.633, and a random split of exactly the same training and test sizes, drawn from
the same population, reaches 0.788. The batch separation therefore costs about 0.155 of
per-feature agreement that a smaller training set does not explain. Holding out one imaging
assay plate costs about 0.150 and holding out one transcriptomic assay plate about 0.139, by
the same comparison. Expressed as the share of the above-null agreement that survives, 76.5%
survives a held-out batch, 78.8% a held-out imaging plate and 81.0% a held-out
transcriptome plate.

That is the teaching point, and it is narrower than "a signature is a mechanism". Three
quarters of the agreement between two readouts of the same perturbation survives an
evaluation in which the model never sees the batch the perturbation came from. The other
quarter does not, and a design-blind analysis would have reported all of it.

Named examples at the ends of the apparent agreement distribution: `LAP3_WT.o` (0.986),
`NFE2L2_WT.c` (0.985) and `NFE2L2_p.T80K` (0.984) at the top, and `MDM2_p.E421Q` (-0.153),
`RBM15B_WT.o` (-0.080) and `NUP88_WT.o` (-0.012) at the bottom. A negative correlation means
the transcriptomic profile of that perturbation points the wrong way for its imaging
profile. These six rows are where to start reading if you want to know which entity the
number is about; they are not evidence about the genes.

## Source terms

- **Licence.** All data in the Cell Painting Gallery is released under CC0 1.0 Universal.
  The "Citation/license" section of the Cell Painting Gallery README states: "All the data
  is released with CC0 1.0 Universal (CC0 1.0)." CC0 removes the legal requirement to
  attribute; it does not remove the scholarly expectation to cite the dataset.
- **Dataset publication.** Haghighi et al. (2022), <https://doi.org/10.1038/s41592-022-01667-0>
  (preprint <https://doi.org/10.1101/2021.09.08.459417>); associated data repository
  <https://github.com/carpenter-singh-lab/2022_Haghighi_NatureMethods>.
- **Gallery publication.** Weisbart et al. (2024), "Cell Painting Gallery: an open resource
  for image-based profiling", *Nature Methods*, <https://doi.org/10.1038/s41592-024-02399-z>.
- **Hosting.** The objects are read from `s3://cellpainting-gallery/`, the Cell Painting
  Gallery's Registry of Open Data entry. The gallery asks that the Registry of Open Data
  program be acknowledged for hosting the data.
- **Data.** <https://cellpainting-gallery.s3.amazonaws.com/cpg0003-rosetta/broad/workspace/preprocessed_data/LUAD-BBBC041-Caicedo/>

## Limitations

- One batch of one study, one cell line, one timepoint, one set of engineered edits. The
  study's other four batches, the other 46 gallery studies and the JUMP pilot are outside
  this protocol, and nothing here transfers to them without being re-measured.
- The agreement is measured between two readouts of the same perturbation. It is not
  evidence about mechanism, about the gene, about a target hypothesis, or about any
  clinical outcome.
- The blocked evaluations hold out structure inside one published experiment. A batch or
  plate held out here is still a batch or plate the laboratory has seen before; this is not
  a deployment setting.
- The design-cost columns compare a blocked fold with a random fold of the same training
  and test sizes drawn from the same population. They isolate the cost of the structural
  separation at a fixed training-set size; they do not separate the batch's nuisance effect
  from the fact that a batch-homogeneous training set covers less of the perturbation space.
- The transcriptomic readout carries plate-matched negative controls on only 6 of its 16
  plates, so no control-based baseline can be computed for it without silently covering
  part of the design. The protocol therefore adds no baseline subtraction of its own and
  uses the gallery's published normalisation as published.
- The imaging feature set is the gallery's variable-selected release, 291 features. The
  gallery's full-feature release for the same batch was not used, and this lab does not
  claim its numbers transfer to it.
- The model is a ridge map, not a state-of-the-art cross-modal predictor. Its penalty is
  selected inside each training fold, but the architecture is not tuned, so the numbers
  bound this simple map's agreement, not the agreement that is achievable.
- No reader outcomes have been collected for this lab. The committed summary records what
  the pipeline computes, not whether anyone has learned anything from it.
