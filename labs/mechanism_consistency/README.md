# Mechanism hypothesis and counterevidence contrast

This laboratory tests whether a compound's vehicle-corrected LINCS L1000 transcriptional response is more consistent across MCF7 and PC3 than a different compound's response. The competing explanations are a mediator-specific response through the intended target and a generic response to cellular perturbation regardless of target. The fixed different-compound profile is the discriminator. This is a signature-pattern test, not an assay of target engagement or a disease-mechanism result.

## Source and protocol

The frozen protocol uses the owning L1000 laboratory's [GSE70138](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE70138) reader and cached 2017-03-06 Level 2 snapshot. It fixes MCF7 and PC3, 10.0 um, 24.0 h and the 978 measured landmark genes. Each profile is corrected with vehicle wells on the same plate before replicate aggregation. The owning laboratory's sorted-ID rotation by 1 gives each MCF7 profile a different compound's PC3 profile as its mismatched control. No second reader, data copy, fitted model or network access is involved once the owning cache exists.

The decision threshold is a matched Spearman rho of 0.1. This is a declared teaching rule over the measured correlation, not a significance cutoff or a value fitted to the observed counts. A matched rho below 0.1 is undecided. At or above 0.1, a mismatched rho strictly greater than the matched rho favors the generic-stress side. If the mismatched rho is also at least 0.1 but no greater than the matched rho, the control is informative too and the case remains undecided. Only a matched rho at or above 0.1 with a mismatched rho below 0.1 falls on the mediator-specific side. Undecided compounds never count as support.

## Fresh independent computation

Use the project Python 3.11 environment and CPU. The first command verifies that the owning cache exists and does not write or fetch data. If it is absent, obtain the source with the owning laboratory's documented command before starting this lab. The inspection commands read the cache and do not edit the committed summary. The export command overwrites only that small summary after validating the protocol, every verdict and the count partitions.

```bash
.venv/bin/python labs/mechanism_consistency/run_lab.py download
.venv/bin/python labs/mechanism_consistency/inspect_mechanism_consistency.py show
.venv/bin/python labs/mechanism_consistency/inspect_mechanism_consistency.py check
.venv/bin/python labs/mechanism_consistency/export_summary.py
.venv/bin/python -m pytest labs/tests/mechanism_consistency -q
```

`show` prints the matched and mismatched rho, verdict and reason for every shared compound, followed by cohort and verdict counts. The committed JSON contains no compound rows. `check` independently recomputes the verdicts and count partitions from the cached snapshot and compares them with the committed summary.

## Observed counts

The local computation on 2026-10-23 found 1,725 admitted MCF7 compounds and 1,724 admitted PC3 compounds. Their union has 1,728 compounds. The test applies to the 1,721 with a response in both lines. Four are present only in MCF7 and three only in PC3, so no cross-line comparison can be made for those seven.

| Pattern verdict | Compounds |
| --- | ---: |
| Mediator-specific side under the fixed control | 678 |
| Generic-stress side because the mismatch exceeds the match | 123 |
| Undecided because matched rho is below 0.1 | 614 |
| Undecided because the mismatched control is also informative | 306 |
| Total undecided | 920 |

| Raw control comparison | Compounds |
| --- | ---: |
| Mismatch exceeds match, irrespective of threshold | 490 |
| Of these, matched rho below 0.1 and therefore undecided | 367 |

The raw comparison overlaps the verdict rows. It preserves every case in which another compound matches better, while the threshold prevents a low-correlation case from becoming a decided result.

The falsifying observation is `generic_stress_count`, the number of shared compounds with matched rho at least 0.1 and mismatched rho strictly greater than matched rho. Its observed value is 123. A result of this kind challenges the mediator-specific pattern for those compounds. It does not prove that generic stress caused their responses.

## Interpretation boundary

The one rotated mismatch is an illustrative control, not a measured stress-only intervention or a distribution of all alternative compounds. A signature correlation cannot identify an intended molecular target, demonstrate target engagement, establish a disease mechanism, or show that a compound is worth making. A target-specific claim would need target-proximal and disease-relevant perturbation controls. No reader outcome has been observed.

Original code is Apache-2.0 and original guide prose is CC BY 4.0. The [GEO disclaimer](https://www.ncbi.nlm.nih.gov/geo/info/disclaimer.html) says NCBI places no restrictions on GEO data use or distribution but warns that submitters may assert rights. The [GSE70138 accession](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE70138) and disclaimer were reviewed on 2026-10-23. The source data retain their own terms.
