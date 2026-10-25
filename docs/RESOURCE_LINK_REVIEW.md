# Resource links and content coverage

Reviewed 8 September 2026 for the unpublished 0.2.0-rc.1 candidate.

The counts below describe that review snapshot. The 9 September
[resource expansion](RESOURCE_EXPANSION.md) brings the Atlas to 124 records;
the [current resource map](../site/src/content/docs/learn/foundations/resource-map.mdx)
shows current chapter associations without rewriting these historical counts.

## What was missing

The review covered all 101 Atlas records, 18 curriculum tracks, 21 registered
English lessons, 18 core-source paths and five lab pages. It also checked
links in the documentation and report. This was a resource and navigation
review, not a new scientific evaluation or an exhaustive literature review.

| Reader-facing issue                                                                      | Correction                                                                                                                             |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Atlas cards had no external entry point                                                  | Every card has a Visit resource link, including after filtering and without JavaScript.                                                |
| Useful links were scattered across detail-page evidence                                  | Resource links collects distinct primary, paper, documentation and asset URLs at the top.                                              |
| Only five additional linked identifiers were registered                                  | Added 120 links across 89 records, bringing the total to 125. No access or licence claim was upgraded.                                 |
| 31 of 81 registered lesson/resource pairs had no source or Atlas link in the lesson text | Every lesson now exposes its registered resources and its pathway's core-source reading, using the curriculum catalog.                 |
| Core-source paths existed only in the catalog                                            | All 18 are surfaced on their corresponding lessons; they are reading lists, not additional taught chapters.                            |
| Lab files appeared only as repository paths                                              | Five lab pages now offer 14 curated protocol, notebook, example and aggregate-result downloads.                                        |
| ChemCrow and BioNeMo links used moved repositories                                       | Updated the scientific-agents lesson to the current repository targets.                                                                |
| The comparison report still called T05 evaluation not run                                | Corrected the report generator. Historical candidate-selection and development snapshots remain unchanged and are labelled as history. |

The merged lesson and core-source lists expose 155 lesson/resource associations.
Links are sourced from official project pages, repositories or documentation.
Background papers, dependency citations and archive badges were not labelled
as software papers. Resource-link evidence has its own review date; the older
metadata review dates do not imply that asset permissions were re-reviewed.

## Availability and remaining limits

Some publisher pages reject automated requests, and some resources require
JavaScript, browser verification or separate access. A project README can
establish the identity of a cited paper even when its full text cannot be
read. Such links are not claims that the paper was fully reviewed, that a
model was reproduced, or that weights may be freely used. Request failures
are not automatically classified as broken links.

Ten records still have one distinct external entry point:

- GNINA model assets, O3DC, the AlphaFold 3 paper, FAIR principles and the
  Open Source AI Definition already point to their primary artifact or page.
- DepMap and UniProt need further browser-based access review before extra
  documentation or download paths can be claimed as checked.
- GROVER, BioNeMo Recipes and RetroSim retain their canonical repository
  entry. Additional paper or asset links need exact identity checks; generic
  model papers, background datasets and unchecked binary downloads are not
  substitutes.

This does not make all 18 tracks complete courses. Deeper worked lessons and
labs in the other tracks and independent reader feedback remain substantive
work. The subsequent [Chinese edition update](CHINESE_EDITION.md) supplies
translations of the 39 Learn pages current at that date and the five lab guides then translated, including the
cross-lab split/leakage and metric/uncertainty exercises and the T15 feedback bridge. Numerical panels,
downloaded files, the Atlas and report are not translated by that update.

The 9 September layered-textbook tranche adds a catalog-derived bilingual map,
four modelling lessons and four mechanism readings. A follow-up adds three
biological-evidence readings on assays, genetic target evidence and PK/PD.
Two further research-decision cases connect existing cross-assay failure to
diagnosis and constructed measurements to a validation plan.
Their source reviews and
constructed examples do not upgrade the historical resource counts or comparison
scores above. The student sandbox is separate from frozen empirical results.

The lab downloads are a small, explicit selection of teaching files. Raw
experiment directories are not served. Full source setup remains in the
repository distribution; no public repository address or deployed site is
invented before publication.
