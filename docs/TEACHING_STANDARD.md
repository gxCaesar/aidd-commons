# Layered graduate-textbook standard

Adopted 2026-09-09. Core scope: target discovery through preclinical candidate
nomination. Clinical development, CMC, manufacturing and regulation are interfaces
and boundary-setting overviews, not complete professional training programs.

## One authoritative map, three layers

`catalog/curriculum/tracks.yaml` owns the 18 tracks, ordered learning paths and
granular units. The website renders its English/Chinese map from that catalog.
Core paths explicitly list stable lesson IDs; adding an advanced lesson to a
track does not automatically add it to the core requirements.

- Core: scientific question, intuition, necessary mathematics and a worked case.
- Research: derivation, mechanism comparisons, reproduction analysis and reading.
- Practice: hand calculation, executable exercise or a scoped capstone.

A mapped historical topic connects a unit to the existing 93-topic audit, without
changing its evidence or score. Several units may map to one historical topic.
Planned units have no fabricated page, completion credit or taught-coverage claim.

## Formal teaching units

State learning objectives and prerequisites. Explain the mechanism before giving
a command. Identify the object, representation, target, objective, fitting/selection
procedure and inference output where relevant. Give a complete example and an
independent task with an answer or observable output. Keep limitations close to
the claim; avoid repeated generic checklists throughout chapters.

Define mathematical symbols, units, normalization and direction, then work a step
numerically. Connect code functions to conceptual steps and show actually produced
outputs. Clearly distinguish constructed examples from empirical observations.

Capability tags independently describe orientation, explanation, worked example,
exercise, or a locally verified runnable exercise. A resource link is not an
explanation. A runnable lab is not evidence of reader learning. Tags are not a
difficulty ordering or quality score. Completion is self-reported local progress.

## Three experiment modes

Before commands, name the mode: editable student exercise; fresh independent
reproduction; or reading existing results. State prerequisites, data/network needs,
compute expectations, output location and overwrite behavior. Keep student output
separate from frozen author results. A missing dependency is not permission to
run a different scientific experiment.

The first modelling line uses the original synthetic standard-library exercise
in `labs/student_modelling/`, then contrasts it with existing FreeSolv and ChEMBL
material. It is not a new real-assay training protocol. Such a lab still needs an
explicit endpoint, data version, grouping unit, split, baselines and evaluation.

For editable computational exercises, including label-free inspection, synthetic
modelling and real-data training, make the notebook the teaching entry rather
than a CLI wrapper. It must lead the reader through the question, data and
molecules, grouping or scaffold split, representation, train-only fitting and
validation selection, plots and errors, then an independent exercise and report.
Default hosted execution may use a downloaded notebook uploaded through Colab's
`File > Upload notebook`; local Jupyter remains an alternative. State network,
runtime and overwrite limits, and distinguish the reader's fresh local outputs
from any frozen author results.

Teach execution state explicitly: a saved cell edit is not an executed variable
update, and a saved notebook is not a backup of separately exported files. Show
fitting, validation selection and final evaluation in distinct readable steps.
Use the shared notebook guide for environment recovery instead of duplicating
long installation instructions in every scientific chapter. CLI entry points
remain optional engineering alternatives, with their own overwrite rules.

## Bilingual teaching and assessment

English is canonical. Preserve formulas, numbers, qualifiers, links, commands,
source dates and lesson identity across editions. Translation is not a second
experiment. Check navigation separately from understanding. Use an unseen transfer
question in a formative session; record assistance and initial answers. No reader
outcomes have yet been collected for this tranche.

## Written capstone workbook

The [five-case workbook](../site/src/content/docs/learn/candidate-nomination/capstone-workbook.mdx)
and its Chinese counterpart now provide complete constructed cases, worked
answers, transfer questions and a memo rubric. They require no execution or
laboratory access. The rows below describe the broader learning destinations;
their empirical components remain separate from this written workbook.

| Capstone                     | Required inspectable reasoning                                                                                                             |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Target evidence              | Connect disease, genetics/perturbation and tractability; compare alternative explanations and propose independent validation.              |
| Property prediction          | Build a stated endpoint table, reproduce strong cheap baselines, diagnose shift, and distinguish predictive utility from assay validity.   |
| Structure-led selection      | Compare target states and poses, identify energetic assumptions, and state what a structure score cannot decide.                           |
| Design and experiment choice | Propose candidates under synthesis/measurement constraints, compare a competent fixed policy, and account for budget and failed feedback.  |
| Candidate nomination         | Integrate potency, selectivity, exposure and safety; retain missing ADMET and validation fields instead of declaring successful discovery. |

These are not five completed empirical labs. The written cases exercise the
decision reasoning; existing notebooks separately teach fitting and reproduction.
The 120-unit map now has written destinations throughout, without claiming
research-level exhaustiveness, professional qualification or measured reader learning.
