# Comparison candidate discovery ledger

Review date: 2026-09-04

## Purpose and boundary

This ledger records how the first AIDD Commons comparison set was discovered
and frozen. It supports reproducibility of candidate discovery; it is not a
claim that every AIDD course, tutorial, benchmark, or reference on the web has
been found.

Search result titles and snippets were used only to discover candidate
surfaces. A positive coverage observation in
`catalog/comparisons/systems/*.yaml` requires an opened official provider page,
official documentation page, or official repository. Material that could not
be inspected remains `unverified`. A topic not found on a named reviewed
surface is not treated as globally absent.

Each record declares an explicit `coverage_default` of `unverified` for every
taxonomy topic omitted from its source-grounded observations. Generated
matrices must materialize those cells individually. This keeps unknown topics
in the upper uncertainty bound and prevents sparse records from silently
becoming absence claims.

The first set was frozen at 12 external systems so that the taxonomy and audit
code can be developed against a stable input. Later candidates remain eligible
for a versioned expansion. Gated, commercial, inactive, or institution-only
material is not excluded merely because it differs from the project's openness
model.

## Search protocol

Candidate discovery combined:

1. broad English and Chinese web searches;
2. repository-focused searches for notebooks and course material;
3. backward traversal from established tutorial, curriculum, and benchmark
   collections; and
4. direct review of named systems already identified in the project landscape
   survey.

The exact broad-search queries run for this freeze are listed below. The
`disposition` column describes their role in candidate discovery, not a
coverage judgment.

| ID  | Date       | Surface                  | Language | Exact query                                                          | Disposition                                                                 |
| --- | ---------- | ------------------------ | -------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Q01 | 2026-09-04 | General web search       | English  | `open AI drug discovery tutorial notebooks curriculum`               | Used to discover or cross-check curricula and notebook collections.         |
| Q02 | 2026-09-04 | Web search, GitHub scope | English  | `site:github.com AI drug discovery course notebooks cheminformatics` | Used to discover public repositories; repository contents required review.  |
| Q03 | 2026-09-04 | General web search       | English  | `drug discovery benchmark datasets tutorial open source AI`          | Used to discover benchmark and dataset hubs.                                |
| Q04 | 2026-09-04 | General web search       | English  | `AIDD curriculum cheminformatics molecular simulation tutorials`     | Used to check coverage across curriculum, chemistry, and simulation routes. |
| Q05 | 2026-09-04 | General web search       | Chinese  | `人工智能 药物设计 教程 课程 开源`                                   | Used to discover Chinese-language curricula and tutorial collections.       |
| Q06 | 2026-09-04 | General web search       | Chinese  | `AI 药物发现 课程 Jupyter notebook 中文`                             | Used to discover Chinese-language executable teaching material.             |
| Q07 | 2026-09-04 | General web search       | Chinese  | `机器学习 药物设计 教程 RDKit 深度学习 课程`                         | Used to discover cheminformatics and machine-learning teaching material.    |
| Q08 | 2026-09-04 | General web search       | Chinese  | `开源 AI 药物发现 教材 课程`                                         | Used to cross-check open textbooks and courses.                             |

## Frozen external comparison set

Each included system has a stable public identity, material relevant to at
least one taxonomy topic, and an item-level record with dated evidence. The
provider class describes the system's primary educational function; it does not
rank quality or openness.

| System                                              | Provider class       | Primary official surface                                                                         | Disposition                                                                                                 |
| --------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| AGIL                                                | curriculum           | [Official repository](https://github.com/dayanjan/AGIL-VIP-AI-PSCI-Public)                       | Included; public student and institution-only solution boundaries are recorded separately.                  |
| Build AI Drug Discovery Pipelines                   | curriculum           | [Official repository](https://github.com/nrflynn2/ml-drug-discovery)                             | Included; public notebooks and companion-book prose are not conflated.                                      |
| ChEMBL Quick Tour                                   | curriculum           | [EMBL-EBI Training](https://www.ebi.ac.uk/training/online/courses/chembl-quick-tour/)            | Included; observations are limited to the dated public course surfaces.                                     |
| European AIDD training network                      | curriculum           | [Official project site](https://aidd.ochem.eu/)                                                  | Included; public training materials are recorded without generalizing project-level licence terms.          |
| Machine Learning for Drug Discovery and Development | curriculum           | [Official book site](https://ml4drug-book.github.io/)                                            | Included; the currently visible tentative contents are not upgraded to executable coverage.                 |
| DeepChem Tutorials                                  | tutorial collection  | [Official repository index](https://github.com/deepchem/deepchem/tree/master/examples/tutorials) | Included; repeated titles are mapped to canonical topics rather than counted as unique coverage.            |
| OpenMM Cookbook and Tutorials                       | tutorial collection  | [Official documentation](https://openmm.github.io/openmm-cookbook/latest/)                       | Included; Cookbook CI and tutorial execution claims are kept distinct.                                      |
| Practical Cheminformatics Tutorials                 | tutorial collection  | [Official repository](https://github.com/PatWalters/practical_cheminformatics_tutorials)         | Included after notebook-index and repository review.                                                        |
| TeachOpenCADD                                       | tutorial collection  | [Official talktorial index](https://projects.volkamerlab.org/teachopencadd/all_talktorials.html) | Included after index and selected talktorial review.                                                        |
| O3DC                                                | benchmark hub        | [Official site](https://o3dc.org/)                                                               | Included; intended index design and the rendered population observed on the review date are separate facts. |
| Therapeutics Data Commons                           | benchmark hub        | [Official site](https://tdcommons.ai/)                                                           | Included; platform access and upstream dataset licences are recorded separately.                            |
| RDKit Cookbook                                      | specialist reference | [Official documentation](https://www.rdkit.org/docs/Cookbook.html)                               | Included as a recipe-oriented specialist reference, not an end-to-end curriculum.                           |

## AIDD Commons self-audit

AIDD Commons is the thirteenth record and is not counted as an external
comparator. No verified public deployment URL or Git remote was available at
freeze time, so its canonical identity and evidence use repository-relative
public paths rather than a fabricated URL.

The self-audit maps one substantiated `explained` topic in each of the 18
charter tracks and maps the frozen FreeSolv lab to its directly supported
`executable` topics. Unit tests are not treated as learner assessment. Content,
code, data, and solution availability remain `unverified` as external-access
claims until a public release surface is verified.

## Deferred discovery candidates

The following candidates appeared during the breadth check after the first set
was frozen. They are not scored in v0.2a. Their inclusion, access, licences, and
item-level depth require a separate opened-source review.

| Candidate                                                       | Discovery surface                                                                                          | Current disposition                                                                                         |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| University of Toronto CSC2541H: AI for Drug Discovery           | [Course site](https://www.cs.toronto.edu/~cmaddis/courses/csc2541_w26/)                                    | Deferred to the next curriculum expansion; item-level evidence has not been encoded.                        |
| Introduction to Deep Learning for the Life Sciences             | [Repository](https://github.com/kochgroup/intro_pharma_ai)                                                 | Deferred to the next tutorial-collection expansion.                                                         |
| DrugDiscoveryBench                                              | [Repository](https://github.com/scaleapi/DrugDiscoveryBench)                                               | Deferred to a benchmark expansion; public tasks and gated evaluation assets must be represented separately. |
| DrugOOD                                                         | [Project site](https://drugood.github.io/)                                                                 | Deferred to a benchmark expansion focused on distribution shift and affinity prediction.                    |
| NPTEL Artificial Intelligence in Drug Discovery and Development | [Course surface](https://www.nptel.ac.in/courses/103106681)                                                | Deferred; official lesson access, dates, and assessment depth need item-level review.                       |
| Fudan University Artificial Intelligence Drug Design course     | [Discovery listing](https://www.classcentral.com/course/xuetangx-534953)                                   | Deferred; the provider's canonical course surface must be opened before any coverage claim.                 |
| 计算机辅助药物设计教程                                          | [Rendered documentation](https://cadd-tutorial.readthedocs.io/zh-cn/latest/index.html)                     | Deferred to the Chinese-language tutorial expansion; provenance and licence scopes need review.             |
| ADMET Predictor AIDD tutorial series                            | [Provider surface](https://www.simulations-plus.com/resource/admet-predictor-tutorial-series-aidd-module/) | Deferred; commercial access and executable-material boundaries need review.                                 |

Deferral is not exclusion and does not imply lower quality. It preserves the
frozen input for v0.2a while making the next expansion queue explicit.

## Known limitations and update rule

- The search is a dated first pass, not a systematic review or an exhaustive
  multilingual census.
- English and Chinese were searched directly. Other language routes require
  dedicated queries and reviewers.
- Search-engine ranking and indexing can omit relevant courses, private
  classrooms, archived versions, and newly released material.
- No raw lesson count, repository star count, or promotional breadth statement
  is used as a proxy for canonical topic coverage.
- The frozen records may be corrected when an official source shows that a
  topic, depth, access state, or licence scope was encoded incorrectly.
- A versioned set expansion must add its queries, review date, evidence, and
  disposition here before its records enter generated comparisons.
