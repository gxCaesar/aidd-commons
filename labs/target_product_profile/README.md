# A falsifiable target product profile over cached ChEMBL measurements

This laboratory applies an illustrative profile to real, admitted ChEMBL 37 measurements. The profile is declared in the frozen protocol before the cached records are read. Its thresholds are teaching decisions, not cutoffs estimated or tuned from these compounds. A measured mandatory gate failure contradicts the profile. A missed preference remains a miss. An unmeasured requirement is never counted as a pass.

## Sources and counted unit

The [decision-unit laboratory](../decision_unit_scope/README.md) admits independent exact response-potency points with their assay and document context. The [clearance laboratory](../az_clearance_system/README.md) admits intrinsic-clearance medians by parent and named assay system. The [CYP laboratory](../cyp_assay_system/README.md) admits exact IC50-derived pChEMBL medians by parent and target. The [multi-endpoint integration laboratory](../multi_endpoint_integration/README.md) joins those records solely by validated ChEMBL parent identifier. This laboratory reuses its join and selects its 58 parents with at least two measured families from the 7,908-parent source union. The other 7,850 parents have one measured family and are outside this task's cohort.

The response-potency proxy mixes assays and does not establish efficacy in the intended population. The clearance records are in vitro intrinsic clearance, not systemic exposure. CYP inhibition potency is not a clinical interaction outcome. Human liver microsomes report `mL.min-1.g-1`, while hepatocytes report `uL.min-1.(10^6cells)-1`. Their denominators differ and the laboratory never divides them into a fold change.

## Frozen profile

The profile describes an illustrative adult advanced solid-tumour setting with an oral route. It does not nominate a compound or claim that the source compounds were developed for this setting. Each rule compares all matching admitted values with a threshold declared before computation. A requirement with no matching endpoint is unmeasured.

| Requirement | Class | Family and matched measurement | Rule |
| --- | --- | --- | --- |
| `response_ic50` | Gate | Efficacy proxy, exact response `IC50` | Every point at most 1000 `nM` |
| `human_microsome_clearance` | Gate | Exposure proxy, human liver microsomes | At most 50 `mL.min-1.g-1` |
| `cyp3a4_inhibition` | Gate | Interaction proxy, CYP3A4 | At most 5 `pChEMBL (dimensionless)` |
| `rat_hepatocyte_clearance` | Preference | Exposure proxy, rat hepatocytes | At most 30 `uL.min-1.(10^6cells)-1` |
| `cyp2d6_inhibition` | Preference | Interaction proxy, CYP2D6 | At most 5 `pChEMBL (dimensionless)` |
| `clinical_response` | Gate | Clinical efficacy, no measurement | At least 30 `%` objective response rate |
| `immunogenicity` | Preference | Immunogenicity, no measurement | At most 5 `%` treatment-emergent anti-drug antibody incidence |

The `response_ic50` rule is an intentionally strict assay-agnostic screen over the available response points. It is not a target-specific efficacy threshold. A parent satisfies the full profile only if every mandatory gate passes. Missing a preference does not cause a gate failure. A compound with a failed gate cannot be reported as profile-satisfying, and a requirement without a measurement cannot be reported as satisfied.

## Fresh independent computation

The mode is a fresh independent computation over the frozen profile and the owning laboratories' existing caches. Use Python 3.11 in the project environment. Once those snapshots are cached, these commands use no network and no accelerator. The `download` command validates the caches and writes nothing. The export command writes only the small summary after all checks pass.

```bash
.venv/bin/python labs/target_product_profile/run_lab.py download
.venv/bin/python labs/target_product_profile/inspect_target_product_profile.py show
.venv/bin/python labs/target_product_profile/inspect_target_product_profile.py check
.venv/bin/python labs/target_product_profile/export_summary.py
.venv/bin/python -m pytest labs/tests/target_product_profile -q
```

`show` prints the declared requirements and, for each parent in the joined cohort, the gates passed or failed, preferences missed and requirements unmeasured. `check` recomputes the results from the owning readers and the integration join, then audits the committed summary. It exits non-zero if the frozen contract, cache, counts or satisfaction rule fails.

## Observed contradictions

The cached computation on 2026-10-23 finds 21 parents with at least one failed mandatory gate. Another 37 have no observed gate failure. None satisfies the full profile because clinical response is unmeasured for all 58. A compound with no observed gate failure is not a development candidate.

| Mandatory gate | Pass | Fail | Unmeasured |
| --- | ---: | ---: | ---: |
| Response `IC50` | 0 | 1 | 57 |
| Human liver microsome clearance | 24 | 5 | 29 |
| CYP3A4 inhibition | 19 | 20 | 19 |
| Clinical response | 0 | 0 | 58 |

CYP3A4 is the most frequent failing gate. Its 20 failing parents are listed by identifier in the committed summary and the `show` output. `CHEMBL1276308`, `CHEMBL17157`, `CHEMBL205807`, `CHEMBL296419` and `CHEMBL6966` fail the human liver microsome gate. `CHEMBL1144` fails the response `IC50` gate. A parent may fail more than one gate, so the per-gate failures are not added to obtain the 21-parent contradiction count.

| Preference | Met | Missed | Unmeasured |
| --- | ---: | ---: | ---: |
| Rat hepatocyte clearance | 15 | 12 | 31 |
| CYP2D6 inhibition | 11 | 19 | 28 |
| Immunogenicity | 0 | 0 | 58 |

The 12 rat-hepatocyte and 19 CYP2D6 misses are separate from the mandatory failures. They do not disqualify a parent. Clinical response and immunogenicity have no measurement in this joined material. Neither requirement can be declared satisfied. A profile passed by every measured compound would have no observed discriminating failure in this cohort, and the audit requires that outcome to be stated if it occurs.

## Interpretation and exercise

The analysis uses an observed, selected overlap of records rather than a prospective panel. The source laboratories' admission rules differ, and absence of an endpoint is not a favourable result. Thresholds illustrate how a declared requirement can be contradicted when measurements are subsequently inspected. They do not validate the threshold values for a therapeutic program. No compound is ranked by the number of gates passed.

Inspect `CHEMBL1232461` in the `show` output. Identify its measured gate and preference outcomes and explain why its human-microsome and rat-hepatocyte values cannot form one clearance fold change.

<details>
<summary>Worked answer</summary>

Its human-microsome clearance gate passes and its rat-hepatocyte clearance preference is met. Its CYP3A4 gate is unmeasured, and its CYP2D6 preference is missed. The microsome result is per gram of protein and the hepatocyte result is per million cells. Their quotient is not a clearance fold change. The clinical response gate and immunogenicity preference remain unmeasured.

</details>

## Sources and licences

| Cached snapshot | Source and licence | Read on |
| --- | --- | --- |
| Response potency | [ChEMBL 37 release](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/) under [CC BY-SA 3.0](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE) | 2026-10-21 |
| Intrinsic clearance | [AstraZeneca dataset CHEMBL3301361](https://www.ebi.ac.uk/chembl/explore/document/CHEMBL3301361) in ChEMBL 37 under [CC BY-SA 3.0](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE) | 2026-09-12 |
| CYP inhibition | [ChEMBL 37 release](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/) under [CC BY-SA 3.0](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE) | 2026-09-12 |

Original laboratory code is Apache-2.0 and original guide prose is CC BY 4.0. Last reviewed 2026-10-23.
