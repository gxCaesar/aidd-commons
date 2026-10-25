# Resource corrections — 9 September 2026

This follow-up corrects factual and evidence-scope errors in the resource
expansion. It does not certify the entire catalog or execute upstream software.
The catalog and the English/Chinese resource guides are updated together.

| Resource or field          | Correction and primary source                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLUE / LINCS L1000         | CLUE tools retired on 31 January 2026 according to the [official notice](https://assets.clue.io/resources/CLUE_Software_License_T_and_C.pdf). The entry now points to public L1000 archives, distinguishing Phase I GSE92742 and Phase II GSE70138 using the [Broad GEO guide](https://clue.io/connectopedia/guide_to_geo_l1000_data). The old catalog ID is retained so teaching links continue to resolve. An accessible legacy interface is not evidence of a working query service. |
| OpenADMET Models           | The repository [LICENSE](https://github.com/OpenADMET/openadmet-models/blob/main/LICENSE) is Apache-2.0, not the MIT licence previously recorded. Its README contains a conflicting MIT sentence; the discrepancy is retained as a caveat.                                                                                                                                                                                                                                              |
| PK-DB                      | The current source [LICENSE](https://github.com/matthiaskoenig/pkdb/blob/develop/LICENSE) is MIT. The earlier LGPL-3.0 entry came from conflicting API metadata. Neither label establishes permission for all imported data.                                                                                                                                                                                                                                                            |
| PK-Sim                     | Its [GPL-2.0 source licence](https://github.com/Open-Systems-Pharmacology/PK-Sim/blob/develop/LICENSE) includes a clarifying addendum; that qualification is now explicit.                                                                                                                                                                                                                                                                                                              |
| Open Targets               | The [official terms](https://platform-docs.opentargets.org/licence) distinguish CC0 Platform data from Apache-2.0 code and list upstream terms. These assets are no longer left together under unknown licence scope.                                                                                                                                                                                                                                                                   |
| GTEx                       | The [download overview](https://gtexportal.org/home/downloads/adult-gtex/overview) separates open portal files from protected raw DNA/RNA sequences and full donor metadata, with a separate AnVIL application. The guide no longer describes only an API surface.                                                                                                                                                                                                                      |
| SAbDab2                    | Its [homepage](https://sabdab.opig.stats.ox.ac.uk/) states CC BY 4.0 for data and explicitly links preprocessed AI/ML training data with standard train/test splits through [Zenodo](https://doi.org/10.5281/zenodo.20083994). The curated training release is distinguished from broad unprocessed downloads.                                                                                                                                                                          |
| OAS and TeachOpenCADD      | Added the respective CC BY 4.0 statements for [OAS data](https://opig.stats.ox.ac.uk/webapps/oas/) and [TeachOpenCADD tutorial material](https://projects.volkamerlab.org/teachopencadd/license.html), without extending them to third-party assets.                                                                                                                                                                                                                                    |
| Thera-SAbDab               | Replaced an unresolved therapeutic-ID URL template with the [official About page](https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/therasabdab/about). Removed a relation specifically to SAbDab2 because the cited page describes SAbDab, not that exact version.                                                                                                                                                                                                                    |
| Training-data availability | Corrected 11 generic database/download entries from `available` to `unverified` for the ML training-data field. Downloadable records alone do not establish a declared training corpus. SAbDab2 retains `available` because its homepage explicitly provides a training release. Retrieval links remain available in the entries.                                                                                                                                                       |

The bilingual resource map also adds a six-collection tutorial chooser with
suggested prerequisites and first reading outputs. BoTorch's stated BO/PyTorch
prerequisites are explicit. These are study suggestions, not executed results.

## Verification scope

Official pages and source licence files were inspected on the date above;
SAbDab2 and GTEx required rendered-page inspection. GEO itself returned a
reCAPTCHA during this check, so accession identity rests on the opened Broad
guide. No challenge was bypassed. No archive or training release was downloaded,
and no external notebook, PBPK simulation or model training was run.

Six targeted catalog regressions first failed on the erroneous records, then
passed after correction. They cover licence identities and evidence URLs,
training-data scope, SAbDab2's explicit release, and the retired CLUE entry.
They protect these corrected cases; they do not prove all upstream information
correct or guarantee that future releases retain the same terms.

Local verification on Node 24 after the corrections:

- Catalog export validated 124 records. The coverage report was regenerated
  with `--today 2026-09-09`; historical comparison scores were not revised.
- `npm run test:unit`: 45 files and 173 tests passed.
- `npm --prefix site run check`: 0 errors, warnings or hints.
- `npm --prefix site run build`: 304 pages built. Existing empty-i18n/404
  notices and the unset-site sitemap warning remain.
- `npm run links:internal` and `npm run citations:check`: passed.
- Desktop/mobile Chromium acceptance: 18 tests passed for the resource map
  and bilingual target, ADMET and biologics written-exercise routes. This checks
  links, JSON associations, answers, keyboard access, overflow and serious/
  critical axe findings. The rendered Chinese map and mobile screenshot were
  also inspected.

The first browser command failed before page assertions because Chrome aborted
inside the sandbox (`SIGABRT`, with `kill EPERM`). The same tests passed after
an approved sandbox-external Chrome launch. The invocation was
`npx playwright test --config tmp/resource-facts-20260909/playwright.config.ts resource-map.spec.ts written-curriculum.spec.ts --grep 'current resource map|Atlas resources|mechanism-targets written|admet-pk written|biologics-design written'`.
No application workaround or browser installation was needed. Existing Python
labs were unchanged and were not rerun. Nothing was published.
