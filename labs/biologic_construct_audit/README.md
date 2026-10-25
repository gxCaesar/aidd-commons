# Therapeutic construct-record audit

This CPU laboratory reads what real therapeutic records state about modality, product-specific construct, production host and intended function. Its counted unit is one named therapeutic entity. It preserves each source's coverage, assembly description and distinction between component parts. A modality is not a construct.

## Environment and inputs

Use the project Python 3.11 environment. No accelerator or additional dependency is needed. The frozen protocol selects named products from reviewed UniProt pharmaceutical annotations and DailyMed label passages. A native protein annotation or a target cross-reference cannot fill a therapeutic field.

The committed snapshot contains the selected source passages, exact retrieval URLs, response lengths, source versions and UTC retrieval time. It supports an offline computation. The source bodies remain outside the compact summary.

| Artifact | Location |
| --- | --- |
| Frozen protocol | `labs/biologic_construct_audit/protocol.json` |
| Committed source snapshot | `SNAPSHOT_JSON` in `labs/src/aidd_commons/biologic_construct_audit/__init__.py` |
| Compact result | `labs/biologic_construct_audit/summary.json` |

## Fresh independent computation

The mode is fresh independent computation under the frozen protocol. Run from the repository root. For a fresh network fetch, the first command requests the declared UniProt search, its individual entries and the selected DailyMed labels. It reports the fetched records and replaces the embedded source snapshot only after validation. The following commands compute from that snapshot.

```bash
.venv/bin/python labs/biologic_construct_audit/run_lab.py download
.venv/bin/python labs/biologic_construct_audit/inspect_biologic_construct_audit.py show
.venv/bin/python labs/biologic_construct_audit/inspect_biologic_construct_audit.py check
.venv/bin/python labs/biologic_construct_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/biologic_construct_audit -q
```

For an offline fresh independent computation, retain the committed snapshot and omit the download step.

```bash
.venv/bin/python labs/biologic_construct_audit/inspect_biologic_construct_audit.py show
.venv/bin/python labs/biologic_construct_audit/inspect_biologic_construct_audit.py check
.venv/bin/python labs/biologic_construct_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/biologic_construct_audit -q
```

`show` prints per-source field coverage and normalized values, assembly, distinguished multi-chain parts, definition status, coverage differences and disagreements. `check` recomputes the invariants and exits non-zero on failure. Both commands write nothing. The exporter overwrites only the compact result after the protocol and audit checks pass. A failed check produces no export. A later live fetch can change the source passages, so the observations below belong to the recorded snapshot.

## Committed observations

| Computation item | Observed value |
| --- | --- |
| Computation date | 2026-10-23 |
| Source retrieval time | 2026-10-23T14:25:57+00:00 |
| Python | 3.11.15 |
| aidd-commons-labs | 0.2.0rc1 |
| Therapeutic entities | 6 |

| Field | Stated | Unstated |
| --- | ---: | ---: |
| Modality | 6 | 0 |
| Construct | 5 | 1 |
| Expression system | 3 | 3 |
| Intended function | 4 | 2 |

Adalimumab, agalsidase-beta and etanercept have all four fields somewhere in their admitted records. Each also has a DailyMed record that independently satisfies the definition rule. Insulin-lispro and reteplase have partial coverage. Human insulin in the Humulin passage has modality alone.

UniProt states a construct without a host for etanercept, insulin-lispro and reteplase. It states a host without a construct for agalsidase-beta. DailyMed supplies the missing construct and intended-function statements for agalsidase-beta and the missing host statement for etanercept. These are coverage differences. No disagreement was found where both sources state the same field.

## Definition and interpretation

A field counts at entity level when an admitted source record states it. Definition status requires modality, product-specific construct and production host together in the same source record. Function remains a separate field. Combining omissions across records cannot create a definition. The known-bad tests enforce rejection of a modality-only record reported as defined and of a construct reported as defined without a host.

An unstated field is missing from the selected record, not necessarily from the therapeutic entity or the underlying science. The audit does not rank entities, establish developability or nominate a therapeutic candidate. The product list and selected passages are a bounded teaching cohort. Reader learning has not been observed.

The [English guide](/labs/biologic-construct-audit/) gives the entity tables, source versions and an interpretation exercise. The [construct identity lesson](/learn/biologics-design/construct-identity-and-objectives/) explains why an expression host, a construct and a downstream biological effect need separate records.

## Sources and terms

The snapshot was fetched and read on 2026-10-23. Its UniProt sources are [P00750](https://rest.uniprot.org/uniprotkb/P00750.json), [P01308](https://rest.uniprot.org/uniprotkb/P01308.json), [P06280](https://rest.uniprot.org/uniprotkb/P06280.json) and [P20333](https://rest.uniprot.org/uniprotkb/P20333.json). Its DailyMed sources are the declared description and mechanism passages for [ENBREL](https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/a002b40c-097d-47a5-957f-7a7b1807af7f.xml), [HUMIRA](https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/a06a9aec-fd5b-4c3e-a81f-eb46bb384100.xml) and [FABRAZYME](https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/988513ab-b06f-4dd0-93f7-d2d4531dcce4.xml).

Original laboratory code is Apache-2.0 and this README is CC BY 4.0. Third-party annotations retain their source terms. The protocol assigns no reuse licence to DailyMed label text. UniProt provides its [source terms](https://rest.uniprot.org/help/license).
