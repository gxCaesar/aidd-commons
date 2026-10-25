# Multi-endpoint profiles across cached ChEMBL 37 measurements

This laboratory joins three independently curated sets of measurements by the ChEMBL parent molecule identifier. It reports each admitted endpoint beside its assay or target, unit and observed spread. It never calculates a score or fills an absent family. The [frozen protocol](protocol.json) names every source file and its expected byte length.

## Source and measurement contract

The decision-unit reader supplies 486 independent point measurements from 15 declared seeds resolved to 10 parents. Its existing endpoint map assigns 462 `AC50`, `EC50` and `IC50` measurements to an efficacy-related response-potency proxy. The remaining 24 `Kd` and `Ki` affinity measurements are counted outside that family. The clearance reader supplies 1,623 admitted parent-by-assay records across human liver microsomes, rat hepatocytes and human hepatocytes. The CYP reader supplies 8,032 admitted parent-by-target records against CYP3A4 and CYP2D6. These counts use each owning reader's admission and duplicate-median rules.

All source data come from [ChEMBL 37](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/), released 2026-05-01 under [Creative Commons Attribution-ShareAlike 3.0 Unported](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE). The decision-unit snapshot was read on 2026-10-21. The clearance and CYP snapshots were read on 2026-09-12. The clearance records belong to [dataset CHEMBL3301361](https://www.ebi.ac.uk/chembl/explore/document/CHEMBL3301361). The owning readers validate source rows and release fields. This laboratory additionally checks the frozen file lengths before joining.

## Fresh independent computation

The mode is a fresh independent computation over the frozen protocol and existing caches. Use Python 3.11 in the pinned environment. The commands require no accelerator. The `download` command validates the three existing snapshots without network access or writes. The `show` and `check` commands read the same caches. The export command overwrites only the small committed summary after every audit passes.

```bash
.venv/bin/python labs/multi_endpoint_integration/run_lab.py download
.venv/bin/python labs/multi_endpoint_integration/inspect_multi_endpoint_integration.py show
.venv/bin/python labs/multi_endpoint_integration/inspect_multi_endpoint_integration.py check
.venv/bin/python labs/multi_endpoint_integration/export_summary.py
.venv/bin/python -m pytest labs/tests/multi_endpoint_integration -q
```

The [committed summary](summary.json) lists all parents with one measured family and full profiles for the parents with at least two. A profile retains individual response-potency assay and document identifiers, clearance assay systems and their physical units, and CYP targets with their contributing assays and documents. Ranges describe the admitted values. A range of zero from one observed value is not evidence of zero measurement error.

## Observed coverage

The cached computation on 2026-10-23 covers 7,908 distinct parents. Of these, 7,850 carry one family, 58 carry two, and none carry all three measured families. The 58 profiles comprise one response-potency plus clearance parent and 57 clearance plus CYP parents. No parent joins response potency to CYP. Toxicity has no measured snapshot.

| Measured family combination | Parent count |
| --- | ---: |
| Efficacy proxy only | 8 |
| Intrinsic clearance only | 1,062 |
| CYP inhibition only | 6,780 |
| Efficacy proxy and intrinsic clearance | 1 |
| Efficacy proxy and CYP inhibition | 0 |
| Intrinsic clearance and CYP inhibition | 57 |
| All three measured families | 0 |

The efficacy proxy has 462 independent points across 9 parents. Clearance has 1,623 parent-by-assay records across 1,120 parents. CYP inhibition has 8,032 parent-by-target records across 6,837 parents. The count gaps from efficacy are 1,161 and 7,570 records, respectively. These are different observation units, so the gaps describe record availability rather than comparative assay precision. Among the 7,908 parents, 7,899 lack efficacy proxy measurements, 6,788 lack clearance and 1,071 lack CYP inhibition, even though those families are measured elsewhere in the union.

## Interpretation boundary

The response-potency records do not establish therapeutic efficacy. Intrinsic clearance is one in vitro component of exposure rather than a systemic exposure measurement. CYP IC50 is an inhibition measurement rather than a clinical interaction outcome. The [safety teaching laboratory](/labs/safety-evidence/) uses constructed data and has no measured toxicity for these parents. A parent with one family measured cannot be assigned any value for the others.

Human liver microsomes report `mL.min-1.g-1`, while hepatocytes report `uL.min-1.(10^6cells)-1`. Their physical bases differ, so the two numbers cannot be divided to claim a fold change. The output groups clearance spread by unit and keeps each assay system visible. No cross-family composite or overall ranking is permitted because the measurements differ in meaning, context, coverage and uncertainty. A profile with two families supports an inspection of those measured axes and explicitly names the third as absent.

Original laboratory code is Apache-2.0 and original prose is CC BY 4.0. Last reviewed 2026-10-23.
