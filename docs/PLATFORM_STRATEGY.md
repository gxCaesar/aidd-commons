# AIDD Commons platform and publication strategy

Decision date: 25 October 2026. [Public milestones](PUBLIC_ROADMAP.md) record
dated teaching delivery and scientific boundaries. This document defines the
product direction and the evidence needed to assess it.

## The intended position

AIDD Commons should become a reference destination where a learner can move
from a drug-discovery question to an explanation, a worked decision, a runnable
exercise and an informed discussion. Its scientific scope remains the project
charter's target-to-preclinical-candidate remit. Clinical, manufacturing and
regulatory material remains an interface to specialist training.

The ambition is international leadership in this defined role. A universal
claim to outperform every resource cannot be established by a page count or an
unbounded comparison. Public comparative statements must name their dimensions,
eligible comparison set, review date, uncertainty and supporting observations.
The published historical comparison and its correction window remain intact.

## What a learner should be able to do

| Need | Required experience | Evidence of delivery |
|---|---|---|
| Start with limited AIDD background | Choose an appropriate route, see prerequisites and complete an initial scientific task without installation | Observed first-reader navigation and a retained initial explanation |
| Understand a method | Connect scientific object, representation, objective, fitting, inference and assumptions to a numerical example | Complete lesson plus an independently attempted transfer task |
| Use a resource | Find a suitable tool or dataset and understand its inputs, outputs, access, licence and evaluation boundary | Task-linked Atlas record with opened sources and adjacent teaching use |
| Execute an exercise | Open a personal notebook, run the supported mode, inspect outputs and retain work | Fresh-environment execution with version, commands, output location and actual result |
| Interpret an apparent success | Compare a competent baseline, identify shift or leakage and retain adverse evidence | A decision memo grounded in a completed case |
| Ask and contribute | Reach a relevant public question or correction route with enough scientific context | Working entry point, maintained response process and actual reviewed contributions |

These outcomes extend the existing teaching standard. They do not replace its
unit requirements or create a second curriculum authority. All route and lesson
associations remain in `catalog/curriculum/tracks.yaml`.

## Product priorities

### A continuous learning route

Retain the core route and specialist routes, but make the next action visible:
prerequisite, lesson, worked example, personal exercise, interpretation and next
lesson. Prioritize the first complete learner journeys over adding isolated
chapters. Translate meaning, quantities and limitations together. Reader
confusion should lead to a specific repaired passage or task rather than
automatic expansion of every short introductory page.

### Reliable computational practice

Keep reading-only, editable student work and independent reproduction distinct.
The default path should remain usable on a CPU and should offer an offline
mode where the teaching objective permits one. Put outputs in a fresh,
discoverable learner directory and explain notebook state and file retention.
Model downloads, paid services and restricted datasets must be explicit optional
requirements. Do not promote an execution copy with changed limits into
validation of an unchanged default.

Test public artifacts from a clean environment against their own code. Preserve
the meaning of input-dependent skips and supply a useful acquisition route where
licensing permits it. Real Colab execution remains a separate observed event;
local notebook execution cannot establish it.

### A task-oriented Atlas and frontier layer

Maintain the seven separate openness dimensions. Link resources to concrete
learning questions and teach selection between alternatives, including failure
cases. Date frontier readings and explain what changed in task, mechanism,
evaluation or access. New model names alone are insufficient additions.

Preserve stable mechanism chapters as the foundation. Use current primary-source
reviews to add or revise bounded readings, then integrate a mechanism into the
core only when it has lasting prerequisite value. A source's current release
must not inherit performance measurements from an earlier checkpoint without
an explicit qualification.

### An exchange community attached to scientific objects

Attach questions to a lesson, resource or case rather than building an unrelated
social feed. Initial channels should cover learning questions, reproducibility
help, paper discussions, factual corrections and contribution proposals.
Existing GitHub Issues remain the route for actionable corrections. GitHub
Discussions is a suitable first forum implementation because the public website
can remain readable without an account and the project can avoid operating a
new authentication service.

Before opening a forum, provide categories, a question template, conduct and
moderation rules, a maintainer rota and escalation routes. A question should
name the page/resource version, intended task, observed output and a minimal
non-sensitive example where needed. Scientific answers should cite sources and
distinguish explanation from an untested suggestion. Do not invite private
datasets, credentials or patient information.

Future activities can include guided study groups, reproducibility clinics,
paper clubs and contributed case notes. Announce only events with actual
organizers and dates. Membership, partnerships, response rates, adoption and
learning outcomes remain unobserved until recorded. Prepared activities are
not an active community.

## How leadership will be measured

| Dimension | Measure and denominator | Important boundary |
|---|---|---|
| Teaching coverage | Evidence-backed depth per declared topic and track | An indexed resource is not a taught topic; unknown coverage stays unknown |
| Frontier currency | Review date and substantive task/mechanism updates for relevant sources | A newly reviewed date does not make an old experiment new |
| Learner usability | Completed, assisted, stopped, skipped and unobserved tasks for a defined reader batch | Record initial answers and assistance; do not pool two languages of one reader as independent readers |
| Computational portability | Completed fresh runs among the explicitly attempted notebook/runtime combinations | Keep actual Colab, local and fixture execution separate |
| Scientific reasoning | Retained explanations on unseen transfer cases under a stated rubric | Small formative sessions do not establish learning gains |
| Community usefulness | Substantive questions, documented answers and accepted contributions over a stated interval | Bots, prepared posts and page views do not establish a scientific community |
| Maintainability | Source-backed corrections, release integrity and review coverage | A green build does not establish scientific correctness |

Use the existing first-reader protocol for an initial formative batch spanning
biology/chemistry, AI and engineering backgrounds. Its purpose is to identify
repairable obstacles. A future educational-effectiveness study requires its
own design, independent units, assessment, consent/ethics determination and
analysis before any learning-gain claim.

Current competitor review must include strengths the project lacks. Preserve
the frozen survey as a dated artifact. Any new scored comparison needs an
explicit cohort and item-level evidence, including eligible newly identified
textbooks, course systems, resource atlases and community platforms. Raw counts
from different product types do not form a common ranking.

## Publication route

The recommended sequence is a complete scholarly report, an author-approved
preprint submission, and then a journal submission suited to the actual
contribution. Do not upload a development log as a research paper.

| Route | Role in this project | Fit and condition |
|---|---|---|
| arXiv | Versioned, citable full technical report | Prepare a refereeable scientific contribution, complete sources and figures; category suitability and moderation remain external decisions. Authors may need endorsement. |
| Journal of Cheminformatics, Educational Article | Preferred journal preparation target for the current teaching contribution | The article must explain reusable cheminformatics learning content with a fully open, reproducible required path. Required inputs must be accessible without registration. Include the journal's scientific-contribution statement and truthful declarations. |
| Journal of Cheminformatics, Software | A possible route if the platform software becomes the principal contribution | Requires a significant advance demonstrated against related software. A larger collection alone does not establish this. |
| Journal of Open Source Education | An alternative for a reusable learning module or educational tool | The short paper accompanies complete open artifacts and describes learning design and actual experience of use. It does not carry the full technical report. |
| PLOS Computational Biology, Education | A possible focused pedagogical article | Its approximately 2,000-word target and 2,500-word maximum suit a focused teaching argument rather than the complete platform report. |

These are preparation recommendations, not assurances of editorial acceptance.
Springer Nature's current [preprint policy](https://support.springernature.com/en/support/solutions/articles/6000258807-preprints)
does not treat posting a preprint as prior publication. Disclose the preprint
when preparing a later journal submission and verify the target's then-current
requirements.
Select one journal route for the actual manuscript. Do not submit substantially
the same manuscript concurrently to multiple journals. Recheck current
preprint policies, fees and article instructions before submission. Publication
fees require a separate decision; planning a route does not commit funds.

### The full report

Maintain one active manuscript under `0Paper/`; preserve the v0.1 report and
v0.2 addendum as historical publications. The new paper should explain:

1. the educational and scientific gap against the closest existing resources;
2. the coupled curriculum, source-backed Atlas, executable exercises and report;
3. teaching design, bilingual semantics, evaluation contracts and source methods;
4. dated coverage results, fair comparisons and concrete negative teaching cases;
5. observed software/reproduction checks, separated from reader outcomes;
6. limitations, maintenance, community governance and reusable artifacts.

Use existing frozen results as teaching evidence, including representation-rank
reversal, correlated physical frames and unsuccessful diversity acquisition.
Model-based content readings must be identified as such. They are not human
assessment or independent evidence of learning. Keep developer iterations out
of the scientific narrative while retaining them internally.

Generate quantity-bearing tables from canonical artifacts. Verify each adopted
citation against its primary publication and actual use. Retain editable
figures and sources, compile the native manuscript, inspect every rendered
page and keep actual language-assistance records. Missing authorship,
affiliation, funding, contribution or ethics information remains an author
query; it must not be inferred from another project.

## Execution order and acceptance

| Workstream | Next deliverable | Acceptance evidence | Owner |
|---|---|---|---|
| Reliability | Maintained text-encoding gate and repaired notebook output portability | Valid/known-defect checks, production coverage and clean fresh notebook runs | Codex, then maintainers |
| Competitive and frontier review | Current source ledger and prioritized teaching deltas | Opened sources, explicit comparison scope and retained competitor strengths | Codex; maintainers accept additions |
| Content | Integrated bilingual frontier readings and improved learner tasks | Registered routes, verified scientific claims, matched editions and actual user-facing inspection | Codex |
| Report | Independent native manuscript, checked figures/tables and PDF | Source-linked quantities, verified citations, complete prose and rendered-page QA | Codex; authors accept scientific content |
| External usability | Colab evidence and a formative reader batch | Actual runtime/session records with failures and assistance preserved | Human runtime operators and volunteer readers; maintainers organize |
| Community | Reviewable forum setup and maintainer playbook, then an operating exchange | Actual accessible routes, named maintainers and observed useful interactions | Maintainers |
| Scholarly release | Curated preprint/journal package | Author/declaration completion, exact-artifact checks and actual platform receipts | Responsible authors |

Earlier valid evidence is reused. Later phases must not be declared complete
from prepared forms, model reviews or activity plans. Public releases can
advance while evidence-dependent educational and community work remains open.

## Official publication sources checked on 25 October 2026

- [arXiv submission overview](https://info.arxiv.org/help/submit/index.html)
- [Springer Nature preprint policy](https://support.springernature.com/en/support/solutions/articles/6000258807-preprints)
- [Journal of Cheminformatics Educational Article](https://link.springer.com/journal/13321/submission-guidelines/educational-article)
- [Journal of Cheminformatics Software](https://link.springer.com/journal/13321/submission-guidelines/software)
- [JOSE author instructions](https://openjournals.readthedocs.io/en/jose/submitting.html)
- [PLOS Computational Biology other article types](https://journals.plos.org/ploscompbiol/s/other-article-types)
