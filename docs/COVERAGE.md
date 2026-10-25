# AIDD Commons measured coverage

This page is generated from `catalog/resources/`,
`catalog/curriculum/tracks.yaml`, and `catalog/comparisons/` on 2026-10-25. It
reports current measured coverage, not an exhaustive survey of AI drug discovery.

## Overall registry

228 distinct validated resource records are in the current
catalog. A source count is not proof of comprehensiveness: omitted domains,
unverified legal terms, and missing evaluation protocols remain coverage gaps.

## Coverage by curriculum track

Track counts are distinct catalog records referenced by that track's ordered
lesson nodes. One resource may support more than one track, so this table is not
summed into an overall total.

| Category                       | Records |
| ------------------------------ | ------: |
| active-learning                |       9 |
| admet-pk                       |      16 |
| biologics-design               |      28 |
| candidate-nomination           |      11 |
| data-governance                |      23 |
| drug-discovery-foundations     |       6 |
| dti-screening                  |      19 |
| evaluation-and-reproducibility |      22 |
| foundations                    |      16 |
| machine-learning               |      11 |
| mechanism-targets              |      15 |
| molecular-generation           |      27 |
| physics-based-modeling         |      18 |
| qsar-properties                |       8 |
| representations                |      39 |
| scientific-agents              |      18 |
| structure-and-pockets          |      23 |
| synthesis-and-automation       |       8 |

## Coverage by resource kind

| Category    | Records |
| ----------- | ------: |
| agent       |      11 |
| benchmark   |      26 |
| database    |      22 |
| dataset     |      14 |
| model       |      81 |
| model-asset |       1 |
| paper       |       4 |
| software    |      59 |
| standard    |       3 |
| tutorial    |       7 |

## Coverage by pipeline stage

The `unclassified` bucket means the record has no stage classification in its
source-backed metadata; it does not mean the resource is unusable.

| Category                | Records |
| ----------------------- | ------: |
| analysis                |       6 |
| analyze                 |       3 |
| benchmark-discovery     |       1 |
| biologics-design        |       6 |
| candidate-nomination    |       5 |
| data-intake             |      31 |
| design                  |      60 |
| disease-mechanism       |      11 |
| dmpk-toxicology         |      13 |
| evaluation              |     103 |
| evidence-synthesis      |       6 |
| governance              |       3 |
| hit-discovery           |      46 |
| lead-optimization       |      24 |
| make                    |      11 |
| model-development       |      33 |
| molecular-generation    |       2 |
| physics-based-modelling |      22 |
| pk-pd-modeling          |       2 |
| property-prediction     |      24 |
| representation-learning |      43 |
| repurposing             |       2 |
| structure-prediction    |      24 |
| target-discovery        |      20 |
| unclassified            |       1 |

## Coverage by access level

| Category         | Records |
| ---------------- | ------: |
| closed           |       2 |
| gated            |      10 |
| open_source      |     162 |
| open_weights     |       1 |
| research_only    |       6 |
| source_available |      41 |
| unverified       |       6 |

## Evidence-state interpretation

`metadata-supported` means the canonical source supports identity and displayed
metadata while lifecycle, access, licence, and openness remain unverified.
`claim-backed` means at least one non-unverified direct claim has adjacent
evidence in that record. Neither state establishes completeness or suitability
for a particular experimental protocol.

| Category           | Records |
| ------------------ | ------: |
| claim-backed       |     227 |
| metadata-supported |       1 |

## v0.2a measured comparison audit

The comparison audit was regenerated on 2026-10-24 from 13 validated
learning systems, including AIDD Commons. It crosses 93 topic units in all
18 curriculum tracks, producing 1,209 logical provider-topic cells.
Of these, 591 are direct observations and 618 remain explicit-default
unknowns. Unknown is not treated as absent.

The present evidence does not establish either the "world's most comprehensive"
or the "most detailed" claim. AIDD Commons has an explained-or-deeper lower
bound of 93 topics, while the strongest external upper bound is 92. Its worked lower bound is 93, and only
18 of the required 12 tracks currently contain executable or assessed
self-audit coverage.

3 candidates passed every v0.2b eligibility criterion in the frozen selection snapshot:

1. `t05-small-molecule-representation` — Small-molecule representations (completed);
2. `t11-physical-model-system-state` — Physical model and system state (completed);
3. `t15-experiment-pool-budget-feasibility` — Experiment pools, budgets, and feasibility (completed);

These are frozen selection snapshots with live implementation states, not
reported performance experiments. Their records name the data version, entity
and independent unit, split, metric, cheap baseline, independent validation
route, licence evidence, CPU estimate, safety disposition, and maintenance
burden. See [the generated comparison audit](COMPARISON_AUDIT.md) and [the
canonical candidate records](../catalog/comparisons/depth-candidates.yaml).
