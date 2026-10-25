# AIDD Commons Project Charter

## Mission

AIDD Commons is an open, source-grounded learning and reference system for AI drug discovery. It is designed for graduate students, AI and computational-biology researchers, and engineers who need to understand, reproduce, evaluate, and extend modern AIDD workflows.

The project connects four artifacts that are often separated:

1. a structured curriculum;
2. a searchable atlas of models, datasets, software, benchmarks, and learning resources;
3. executable, evaluation-aware labs;
4. a living technical report about open development in AIDD.

The English edition is canonical. Chinese navigation, onboarding, pathway summaries, and translations of the existing lessons and lab guides provide an entry route without changing the meaning of the canonical scientific content. Numerical panels, downloadable artifacts, the Atlas, and the report retain their original format or language.

## Scope

The core scope spans target discovery through preclinical candidate nomination. Clinical development, real-world evidence, manufacturing, and regulation are included as boundary-setting overviews rather than full professional training programs.

The curriculum is organized into 18 tracks:

1. Start here, pathways, environment, and glossary
2. Drug discovery, medicinal chemistry, structural biology, and experimental foundations
3. Machine learning, geometric learning, probability, and scientific computing
4. Data, licensing, standards, cleaning, and entity alignment
5. Molecular, protein, complex, omics, and knowledge-graph representations
6. Disease mechanism, target discovery, causal inference, and perturbational omics
7. QSAR, activity prediction, and molecular properties
8. ADMET, toxicity, DMPK, and PK/PD
9. Drug-target interaction, affinity, virtual screening, and repurposing
10. Structure prediction, pockets, and co-folding
11. Docking, scoring, molecular dynamics, FEP, quantum chemistry, and ML potentials
12. Small-molecule generation, search, and multi-objective optimization
13. Protein, peptide, antibody, nucleic-acid, and multimodal design
14. Reaction prediction, retrosynthesis, synthesizability, and laboratory automation
15. Active learning, Bayesian optimization, and design-make-test-analyze loops
16. Scientific language models, retrieval, tools, and agents
17. Splits, benchmarks, uncertainty, out-of-distribution evaluation, leakage, and reproducibility
18. Candidate nomination, failure analysis, biosecurity, open science, and capstone work

## Editorial contract

Every substantive chapter should expose:

- prerequisites and learning objectives;
- scientific assumptions and a data contract;
- a strong cheap baseline before frontier methods;
- an executable lab or worked case when feasible;
- evaluation traps, leakage risks, and common failure modes;
- openness, licensing, and reproducibility constraints;
- source-level citations and a visible last-review date.

The project does not claim to be the world's most comprehensive AIDD tutorial until a documented comparison audit and coverage threshold support that statement. Until then, public language is “building the most comprehensive open AIDD learning system.”

## Scientific integrity

Tutorial results must distinguish observed measurements from expectations. Labs freeze task definitions, data splits, metrics, and selection rules before test evaluation. Benchmark tables must not imply a performance ranking unless the compared systems share a matched protocol.

Sources are evaluated at the claim level. Search snippets, inaccessible pages, and repository names do not establish a scientific or openness claim. Unknown fields stay explicitly unverified.

## Openness

Original code is released under Apache-2.0. Original prose and figures are released under CC BY 4.0. Third-party resources retain their own licences and must be attributed in the registry and adjacent content.

“Open” is not a single label. The atlas records inference code, training code, weights, architecture, data recipe, training data, and evaluation code separately, with evidence and caveats.

## Initial release criteria

Version 0.1 requires:

- a deployable bilingual documentation shell;
- a validated source registry and generated public data exports;
- at least 100 verified resource records;
- three end-to-end vertical slices: the target-to-candidate map, the open co-folding frontier, and an honest FreeSolv baseline lab;
- a living-report skeleton and a working contribution flow;
- automated schema, build, link, Python, notebook, browser, accessibility, and public-release hygiene checks.

Later milestones increase topic, lab, case-study, and source coverage without relaxing the evidence standard.
