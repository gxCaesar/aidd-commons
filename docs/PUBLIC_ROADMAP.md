# Public milestones and scientific limits

Source version 0.3.1, 25 October 2026. Dated source packages are listed on the
[release page](https://github.com/gxCaesar/aidd-commons/releases). This document
records teaching delivery and scientific boundaries. It does not report
human learning outcomes or an established global ranking.

## Teaching delivery

The following quantities describe different objects and are not additive.
Counts come from `catalog/curriculum/tracks.yaml`, `catalog/resources/`, the
English/Chinese content directories and the generated static build.

- Tracks: 18.
- Declared teaching units: 120.
- Catalogued lesson records, including source-reading paths: 127.
- English Learn pages: 111.
- Chinese Learn pages: 111.
- Lab guides per language, excluding the shared notebook guide: 56.
- Lab directories: 53.
- Atlas records: 232.
- Built HTML pages: 602.

The 109 canonical teaching chapters in each language now offer continuation
links. A chapter appearing in several declared learning routes retains a
separate previous/next step for each route. Other chapters offer neighboring
chapters within their track. These links work without JavaScript. The
[curriculum map](https://gxcaesar.github.io/aidd-commons/learn/foundations/curriculum-map/)
explains the routes and prerequisites.

Four editable exercises provide paired English/Chinese notebooks with identical
code cells. Atlas entries and historical report downloads retain their
canonical English content. Local software acceptance and isolated notebook
execution do not establish actual Colab portability or human understanding.

## Comparison and frontier reading

The historical comparison retains 13 providers, including AIDD Commons, and
93 topics. External observations are frozen on 11 September 2026; this
project's observations extend through 24 October 2026. Lower and upper bounds
preserve unverified content and execution basis. Both comparative leadership
claims remain `not_established`; the public correction window and its actual
start are described in [PUBLICATION.md](PUBLICATION.md).

The [current resource review](CURRENT_RESOURCE_COMPARISON.md) is a separate
qualitative observation dated 25 October 2026. It preserves other resources'
strengths and does not rescore the frozen matrix. Dated frontier readings
explain changes in task, mechanism, evaluation or access. A source announcement
or constructed calculation is not a reproduced upstream result.

## Completed teaching cases

The ChEMBL EGFR representation case retains a ranking reversal between assays.
Morgan Ridge performs best in the primary comparison and worst in the
separate-assay comparison. The T05/T15 cases share labels and development
choices, so they do not provide untouched independent confirmation. See the
[EGFR lab](../labs/chembl_egfr/README.md) for the frozen protocol and outputs.

The experiment-pool case retains MaxMin losing to all five fixed random
policy instances in both retrospective assay replays. The second pool contains
one scaffold group. Recovery and scaffold coverage are different objectives;
the replay is not prospective discovery evidence. See the
[pool-budget lab](../labs/pool_budget/README.md).

## rMD17 system state

The teaching case `t11-physical-model-system-state` is `completed`. Its
energy-only development comparison uses n=2 development systems. Frozen Ridge
MAE is 2.4810026728771484 kcal/mol for ethanol and 2.74979407419567 kcal/mol for
malonaldehyde. Those values are reported separately rather than pooling frames
as independent molecular systems. The source is the retained
[development summary](../labs/rmd17_system_state/development-summary.json).

The paired within-system evaluations use benzene and uracil, each with 600
training, 200 validation and 200 evaluation frames and the frozen Ridge penalty
of 100. Their results do not establish zero-shot transfer to another molecule.
Frames within a trajectory are correlated. The retained output lacks per-frame
Ridge predictions, so later checks could recompute baseline and target-range
quantities but could not independently recompute the Ridge scores or a new
paired frame-level comparison. See the [lab guide](../labs/rmd17_system_state/README.md)
and [retained evaluation summary](../labs/rmd17_system_state/locked-summary.json).

## PK source screening 2026-09-12

This is a historical record of the data-access and licence screening that
narrowed the intrinsic-clearance teaching lab. It does not claim that every
source's current terms or access behavior are unchanged.

Three candidate parameter sources were not admitted because that screening
could not independently verify the open licence implied by an aggregator's
blanket CC BY 4.0 tag. They were Obach and colleagues' 2008 half-life data
(DOI [10.1124/dmd.108.020479](https://doi.org/10.1124/dmd.108.020479)), Lombardo and
Jing's 2016 volume-of-distribution data (DOI
[10.1021/acs.jcim.6b00044](https://doi.org/10.1021/acs.jcim.6b00044)), and Ma and
colleagues' 2008 oral-bioavailability data (DOI
[10.1016/j.jpba.2008.03.023](https://doi.org/10.1016/j.jpba.2008.03.023)). A
subscription or text-and-data-mining route was not treated as permission to
redistribute extracted measurements under CC BY 4.0. The aggregator's code
licence did not establish the source data's terms.

The same historical screening reached PK-DB study metadata and dosing records
without authentication, while attempts to retrieve the measured parameter
outputs and time courses anonymously returned no records. This observation did
not establish that the database contained no measurements or that every study
had the same access rights. Metadata availability and an open platform licence
did not supply the measured values needed by this no-account teaching path.

The selected AZ intrinsic-clearance lab instead uses actual ChEMBL dataset
deposition `CHEMBL3301361`. It compares human liver microsomes, rat hepatocytes
and human hepatocytes. Its scope is intrinsic clearance. It does not measure
absorption, distribution or oral bioavailability and cannot stand for the full
PK-exposure topic. The [lab guide](../labs/az_clearance_system/README.md),
[frozen protocol](../labs/az_clearance_system/protocol.json) and
[observed summary](../labs/az_clearance_system/summary.json) retain the admission
rules, assay identities, units, overlaps and scientific limitations.

## Evidence still to collect

Actual Colab execution, formative human-reader sessions and useful community
interactions remain unobserved. Reader assessment should preserve initial
answers, assistance, stopped tasks and unseen transfer reasoning under an
appropriate ethics/privacy determination. Prepared forms and passing programs
are not evidence of learning gain or an active community.

Useful contributions include a source-backed correction, an accurately reported
reproduction attempt, a repaired explanation and an independent teaching case.
The [contribution guide](../CONTRIBUTING.md) and
[exchange process](../GOVERNANCE.md#learning-questions-and-exchange) explain how
to participate. Public statements should remain within the evidence actually
collected.
