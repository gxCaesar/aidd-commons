# Approved source package checklist

This checklist applies to the optional engineering session, where a reader
receives a source copy instead of a running site address. Complete it before
the package leaves your hands, and keep the completed copy with the session
notes.

## The packaging limitation to state before the session starts

The curated release excludes the dependency lockfile on purpose. A reader who
receives that release therefore resolves dependencies on their own machine from
the versions declared in the project file, and no transitive dependency is
pinned for them.

The consequence for the session is that a dependency-resolution failure cannot
be attributed. It is indistinguishable between a failure caused by the
packaging and a failure caused by the tutorial instructions. A reader who
cannot install the declared packages has not shown that the instructions are
wrong, and a reader whose install fails has not shown that the release is
broken.

Say this to the reader before they start. Do not record a resolution failure
as an instruction failure without evidence that separates them, and do not
record a setup failure as a failed task.

## What the package must contain

The reader follows the first-session instructions and runs the label-free
inspector. The package therefore has to contain all of the following.

| Item | Why the reader needs it | Present |
| ---- | ----------------------- | ------- |
| `pyproject.toml` | declares the supported Python versions, the pinned direct dependencies and the location of the importable package |  |
| `labs/src/aidd_commons/` with `representations/inspection.py` | the inspection code that the entry point imports |  |
| `labs/molecule_representations/run_lab.py` | the entry point the instructions name |  |
| `labs/molecule_representations/examples.csv` | the seven authored examples the inspector reads, under a header of exactly `id,smiles,teaching_point` |  |
| the first-session lesson pages for the edition the reader will use | the instructions the reader follows |  |
| `package.json`, `scripts/`, `catalog/` and `site/` | needed only when the reader builds the site from source instead of receiving a running address |  |

The release ships the site source and its generated data rather than the built
pages. A reader who is expected to read the lessons in a browser needs a
running site address. A reader who is expected to build the site needs every
item in the table.

## What the reader's machine must have

| Requirement | Version | Note |
| ----------- | ------- | ---- |
| Python | 3.11 or 3.12 | the project file accepts `>=3.11,<3.13` |
| `uv` | current release | the instructions point to the official installation page |
| network access | once | the declared packages are downloaded on the first sync |
| a terminal | any | the reader opens it in the folder holding the project file |

No account, graphics card, model or activity dataset is needed. The reader
must not download the ChEMBL or rMD17 data, run the pretests, change a
protocol or invoke a locked evaluation.

## Recording the failure mode

A resolution failure and an instruction failure look the same from the
reader's side, so the facilitator records which mode occurred together with
the evidence that separates it. Use one row per attempt.

| Attempt | Reader label | First useful error, verbatim and redacted | Failure mode | Evidence that separates this mode | Action taken |
| ------- | ------------ | ------------------------------------------ | ------------- | ------------------------------- | ------------ |
|  |  |  |  |  |  |

Use one of these failure modes.

| Failure mode | What the reader sees | What separates it |
| ------------ | -------------------- | ----------------- |
| package incomplete | the entry point, the examples file or the importable package is absent from the copy | the file is missing, which you can confirm before the package is handed over |
| dependency resolution | the sync or install command stops on a resolution or build error | the copy is complete and the declared versions are present, and the error names a package rather than a missing file |
| environment or tooling | the installer is absent, the Python version falls outside the supported range, or the network is unavailable | the error names the tool, the interpreter or the network |
| instruction failure | the copy is complete, the environment is sound, and the reader still cannot proceed | the reader names a step that contradicts the material, and no other mode applies |

## What this checklist does not claim

This checklist makes no claim that any command has been verified in a live
hosted runtime. The project's own position is that none of the notebook pairs
has been verified in a live Colab runtime, and that local execution and
successful cloud execution are different checks.

A reader who runs the inspector on their own machine produces a local
observation. It does not change the hosted-runtime status of any material, and
it does not make the release verified.
