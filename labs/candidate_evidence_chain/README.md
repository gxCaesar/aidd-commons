# Candidate evidence chains over cached ChEMBL measurements

This laboratory assembles one eight-link chain for each declared ChEMBL parent. It reads the same validated activity, intrinsic-clearance and CYP inhibition snapshots used by the multi-endpoint integration laboratory. Each link is measured, absent, constructed or not covered. The first link outside measured evidence stops a candidate claim, even when later links contain observations.

The three examples were fixed to expose different available measurements. `CHEMBL1144` has response-potency and clearance records. `CHEMBL1232461` has clearance and one CYP target, which is insufficient for a paired selectivity link. `CHEMBL1963249` has clearance and a same-document CYP3A4/CYP2D6 pair. All three stop at mechanism because no compound-specific mechanism validation is available. Their different downstream states remain visible and are not converted into an ordering.

## Source and state contract

The measured snapshots are ChEMBL 37, released 2026-05-01 under [CC BY-SA 3.0](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE). The activity snapshot was read on 2026-10-21. The clearance and CYP snapshots were read on 2026-09-12. Clearance traces to [dataset CHEMBL3301361](https://www.ebi.ac.uk/chembl/explore/document/CHEMBL3301361). The owning readers validate admission and parent identity. This laboratory uses only their parent-level outputs and checks their frozen snapshot lengths through the integration reader.

Measured means a real value for this parent in the named family, with unit, assay or target, and document. Absent means that the measurable family has no qualifying record for the parent. Not covered means that this repository has no compound-matched material for the family. Constructed means only a teaching case supplies the link. No constructed case is joined to a ChEMBL parent in this run. The [safety teaching laboratory](/labs/safety-evidence/) and [route-recovery laboratory](/labs/retro-disconnection/) contain constructed records, not measured safety or synthesis for these parents.

The selectivity link has a deliberately narrow operational definition. It requires one admitted CYP3A4 and one CYP2D6 inhibition measurement from the same document, each based on one activity. It describes differential inhibition of those two enzymes and does not establish selectivity for an intended therapeutic target. An intrinsic-clearance value is a measured in vitro proxy within the exposure link. It does not establish systemic exposure.

## Fresh independent computation

The mode is a fresh independent computation under the frozen protocol. Use the pinned Python 3.11 environment. The snapshots must already be cached. Every command below runs without network or accelerator use. `download` validates existing caches and writes nothing. `show` prints each link and its source measurements. `check` recomputes the chain and compares the committed summary. The export overwrites only the small committed summary after every check passes.

```bash
.venv/bin/python labs/candidate_evidence_chain/run_lab.py download
.venv/bin/python labs/candidate_evidence_chain/inspect_candidate_evidence_chain.py show
.venv/bin/python labs/candidate_evidence_chain/inspect_candidate_evidence_chain.py check
.venv/bin/python labs/candidate_evidence_chain/export_summary.py
.venv/bin/python -m pytest labs/tests/candidate_evidence_chain -q
```

## Observed chains

| Parent | Measured | Absent | Constructed | Not covered | First non-measured link | Supports a claim |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `CHEMBL1144` | 2 | 1 | 0 | 5 | mechanism | no |
| `CHEMBL1232461` | 1 | 2 | 0 | 5 | mechanism | no |
| `CHEMBL1963249` | 2 | 1 | 0 | 5 | mechanism | no |

Across these three declared parents, mechanism is the first non-measured link in 3 chains. The number of chains reaching a bounded claim is 0. A later measurement cannot repair the earlier gap. Different compounds retain different downstream evidence even though this source set makes their formal first stop identical.

The chain carries eight links in order. Mechanism and intended-target validation are not covered. Activity is an admitted response-potency observation or absent. Selectivity is the narrow same-document CYP pair or absent. Exposure carries in vitro clearance or is absent. Safety, synthesis and independent chain reproducibility are not covered for these parents. A constructed example cannot be counted as a measured link, and any absent, constructed or not-covered link bars a claim. A fully measured chain could carry no claim broader than its first measured link's scope.

The summary retains the selected parent chains and their admitted measurements. It contains no archive rows or cohort-wide compound table. `show` displays every measurement in the selected chains, including the assay and document identifiers that make each reported value traceable.

## Interpretation boundary

These chains do not establish that any compound is a development candidate, that its mechanism is correct, or that missing links are fillable. Response potency does not prove target engagement. A CYP pair does not imply broad selectivity or clinical interaction. Intrinsic clearance does not measure systemic exposure. There is no measured safety, synthesis or clinical outcome here. The selected ChEMBL datasets are differently sampled, and no ranking by chain length is meaningful.

Original laboratory code is Apache-2.0. Original prose and constructed teaching material are CC BY 4.0. Last reviewed 2026-10-23.
