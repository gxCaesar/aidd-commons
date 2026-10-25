# Resource expansion — 9 September 2026

This round expands the Atlas from 101 to 124 records and adds three bilingual
resource-selection guides. Learn now has 66 pages per language: 64 registered
teaching pages plus the curriculum and resource maps. All 120 existing curriculum
units retain their written destinations. These counts describe delivery, not
research-level completeness or reader learning.

The subsequent [factual corrections](RESOURCE_FACT_CHECK.md) supersede the
initial licence, CLUE-service and training-data interpretations. The verification
counts below describe the initial expansion, not the follow-up correction run.

## Scientific-agent continuation

The [new bilingual guide](../site/src/content/docs/learn/scientific-agents/agent-resource-guide.mdx)
([中文](../site/src/content/docs/zh-cn/learn/scientific-agents/agent-resource-guide.mdx))
adds worked resource selection for scientific text, document retrieval, chemistry
tools and biological data analysis. The Atlas now contains 128 records and Learn
has 69 pages per language at that date, with six bilingual resource-selection guides.

New records describe PaperQA2, LAB-Bench and BixBench. ChemCrow's code licence and
public-tool limitation were inspected. Official README, licence, dataset-card
and BixBench grading-source checks on 2026-09-09 establish the bounded metadata,
not reproduction or service availability. PaperQA2 package snapshots are not
interchangeable with paper systems. BixBench v1.5 revised its questions; its
grader writes back to the supplied CSV. Code licences do not settle all model,
paper or capsule-data terms. Some web fetches failed; the BixBench dataset card
was read from the same official raw URL with a bounded HTTP fallback.

The two original constructed packets distinguish answer passes, execution-record
passes and their intersection. They do not copy benchmark questions or claim
official benchmark metrics. No dataset capsules, containers or weights were
downloaded; no upstream agent, paid API, benchmark or wet experiment was run.
Python labs, 120 unit definitions, explicit learning routes and historical
comparison/result files were not changed. Additional references appear as track
reading, not evidence that every unit is now fully supported. Per-modality
curation, reader learning and cloud execution remain open work.

Local verification on Node 24: 128 catalog records exported, 46 unit-test files
with 174 passing tests, Astro check with no errors/warnings/hints, and 314 built
pages. Fourteen targeted desktop/mobile browser tests passed, including the
new map → guide → Atlas journey, answer expansion, table keyboard scrolling
and serious/critical accessibility checks. The new navigation test first failed
on the absent guide; its initial full run then exposed a test selector targeting
a link inside collapsed reading rather than the visible table. Scoping that
selector to the table resolved all four language/device failures without
changing page behavior. The two languages' 25 numeric inline spans agree, and
both constructed count tables and fractions were checked separately. The mobile
DOM check confirmed a 412-pixel page with 144-pixel table columns; a final manual
screenshot request was cancelled after a slow response, so no new screenshot
review is claimed. Existing empty-i18n/404 and unset-site sitemap notices remain.

## Physical-modelling and generation continuation

The follow-up adds two bilingual worked reading guides and one distinct
REINVENT 4 resource record. That delivery contained 125 Atlas records and 68 Learn
pages per language; the original expansion counts below remain its dated scope.

- [Physical-modelling guide](../site/src/content/docs/learn/physics-based-modeling/physics-resource-guide.mdx)
  separates poses, parameter assignment, dynamics, trajectory analysis,
  alchemical free energies and electronic-structure quantities. Constructed
  packets teach non-comparable docking scores, saved frames versus simulated
  time, and the missing solvent leg in a relative binding calculation.
- [Generation guide](../site/src/content/docs/learn/molecular-generation/generation-resource-guide.mdx)
  separates proposal/search software, distribution-learning tasks and
  goal-directed benchmarks. A constructed candidate funnel makes validity,
  uniqueness, novelty and proxy-passing yield denominators explicit.
- The current REINVENT course references now resolve to the version 4
  repository. The archived 3.2 record remains separately available with a legacy
  label. Version 4's source licence was inspected; its linked prior archive
  could not be opened, so weight and training-data claims remain unverified.
- GuacaMol's summary and tasks now include both benchmark families documented
  in its official repository. OpenFF's entry uses its current official docs URL;
  this change is not a claim that its older URL is universally inaccessible.

Primary documentation and source files were opened on 2026-09-09. No datasets
or weights were downloaded and no upstream calculations were executed. These
guides do not change the existing 120 unit definitions, core route, historical
comparison scores or lab results. Reader learning and per-unit resource
sufficiency remain unassessed. Agent and modality-specific curation remains
future work.

Local continuation verification (Node 24): 125 catalog records exported;
46 unit-test files / 174 tests passed; Astro check reported 0 errors, warnings
or hints; 309 pages built; internal links and citation keys resolved. The
REINVENT version-link regression failed before correction and passed afterward.
Targeted desktop/mobile Chromium acceptance passed 14 tests across the resource
map and bilingual physics/generation written-exercise routes. Existing
empty-i18n/404 notices and the unset-site sitemap warning remain.

Visual inspection at a 412-pixel mobile viewport found overly narrow table
columns despite the existing page-overflow check passing. The new minimum-column
width regression failed on both Chinese guides before a scoped table-style fix.
All 14 targeted browser tests then passed again, including keyboard horizontal
scrolling. The two new bilingual guides now keep 144-pixel minimum columns while
the page itself remains within the viewport; Astro check also passed afterward.

The two guides' 20 numeric inline examples agree across languages and their
hand calculations were checked. An initial ad-hoc text extractor incorrectly
paired backticks across prose; correcting extraction, rather than changing the
lesson, resolved the false mismatch. A deliberately changed numeric example
was rejected. This is a bounded check, not a general scientific-correctness
validator. Python lab code was unchanged and was not rerun; nothing was
published.

## Original additions and teaching use

| Area            | Added resources                                                                                                                                 | Teaching purpose                                                                                                          |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Target evidence | Open Targets Platform, GWAS Catalog, GTEx, CELLxGENE Census, Connectivity Map L1000, JUMP Cell Painting, Human Protein Atlas, PRISM Repurposing | Separate genetic association, tissue/cell context, perturbational signatures, localization and viability evidence.        |
| ADMET and PK    | OpenADMET Models, OpenADMET Demos, PK-Sim, PK-DB, CompTox Chemicals Dashboard, ToxCast                                                          | Distinguish model implementation, tutorial workflow, PK observations, PBPK assumptions and assay-level chemical evidence. |
| Biologics       | SAbDab2, OAS, Thera-SAbDab, IEDB                                                                                                                | Distinguish experimental structures, repertoire distributions, disclosed therapeutics and epitope evidence.               |
| Tutorials       | TeachOpenCADD, DeepChem tutorials, RDKit Cookbook, OpenFE tutorials, BoTorch tutorials                                                          | Provide learning entry points beyond software names; linked to relevant existing chapters.                                |

The target, ADMET and biologics tracks now register 12, 10 and 14 distinct
resources respectively, including their pre-existing references. These counts
overlap across tracks and must not be summed as independent resources.

## Navigate the resources

- [Current unit resource map](../site/src/content/docs/learn/foundations/resource-map.mdx)
  ([中文](../site/src/content/docs/zh-cn/learn/foundations/resource-map.mdx)).
- [Target evidence guide](../site/src/content/docs/learn/mechanism-targets/target-resource-guide.mdx).
- [ADMET and PK guide](../site/src/content/docs/learn/admet-pk/admet-resource-guide.mdx).
- [Biologics resource guide](../site/src/content/docs/learn/biologics-design/modality-resource-guide.mdx).

Each Atlas entry links to chapters that register it. The website exports current
associations at `/data/curriculum-resources.json`. Each row lists the unit,
chapter, chapter activities, assigned resources and separate track reading.
`unit_resource_sufficiency` remains `not_assessed`: a shared chapter reference
does not establish that every section supports every objective linked to it.

## Access and remaining gaps

Primary resource and documentation pages were opened for this curation round;
source URLs and reviewed fields are recorded beside each Atlas claim. RDKit and
DeepChem source-code licence entries were checked against their official licence
files. Source-code permission does not relicense third-party data.

109 of 124 access-category fields remain `unverified`. This is an evidence
boundary, not a claim that the resources are inaccessible. Lifecycle, code,
weights, data and licence scope remain separate fields. No upstream tutorial was
executed for this expansion, and no new dataset was downloaded or model trained.

The biologics guide covers antibody and epitope resources, not a complete primary
resource collection for oligonucleotides, ADCs or degraders. Physical-method,
generation and scientific-agent resource selection also needs further expansion.
Per-unit resource sufficiency and reader learning remain unassessed. The dated
13-system, 93-topic comparison audit has not been rescored.

## Local verification

On the delivered local tree, using Node 24:

- Catalog export: 124 validated records; curriculum references resolve.
- `npm run test:unit`: 44 files, 167 tests passed, including missing-resource,
  missing-prerequisite and future-date rejection cases.
- `npm --prefix site run check`: no errors, warnings or hints.
- `npm --prefix site run build`: 304 pages built. Existing empty-i18n/404 lookup
  notices and the unset public-site sitemap warning remain; no deployment URL
  was invented.
- `npm run links:internal` and `npm run citations:check`: passed.
- Targeted desktop/mobile Chromium acceptance: 18 tests passed across the
  resource map and target, ADMET and biologics written-exercise routes in both
  languages. Checks include JSON associations, return links, expandable answers,
  keyboard access, page overflow and serious/critical axe findings. A rendered
  Chinese mobile resource-map screenshot was also inspected.

The current-catalog tests now use the current validator date; older frontier
evidence assertions remain scoped to their original records. Fixture tests still
reject future-dated records. Python lab code and experiments were unchanged and
were not rerun for this curation round. Nothing was published.
