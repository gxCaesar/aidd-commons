# What is one measurement of a compound?

This lab takes a declared set of real compounds and asks a question that sits underneath almost every
bioactivity table: when a database says a compound has a reported value, how many independent
measurements does that compound actually have, and which rows had to be set aside before the number
means anything? It resolves the entity hierarchy first, from a salt formulation to the parent
molecule it belongs to, then counts what survives a declared admission rule, then reports the assay,
document, target, organism, assay type, confidence score and relation behind each surviving
measurement. It is a descriptive read of already-published measurements: no model is fitted, no split
is drawn and nothing is predicted. What this does not show is any claim about how potent, selective,
safe or clinically useful any of these compounds is; a count of measurements says nothing about the
size or quality of an effect, and the protocol's `excluded_by_design` list is the machine-readable
version of that sentence.

## Data and provenance

Everything comes from one real release of one real database: ChEMBL 37, released 2026-05-01, read
through the ChEMBL REST API at `https://www.ebi.ac.uk/chembl/api/data/`. The release is confirmed
live at every download: `status.json` must report `chembl_db_version` `ChEMBL_37` and
`chembl_release_date` `2026-05-01`, and the download fails if it does not.

The cohort is declared in [`protocol.json`](protocol.json) as fifteen ChEMBL molecule identifiers,
which resolve to ten distinct parent molecules. Five of the fifteen are salt formulations whose
parent is itself in the cohort, so the declared set of molecules is deliberately larger than the set
of units of inference. Three of the seeds are formulations rather than single molecules:
`MIXTURE OF MMC AND TA` and `SODIUM LAURYL SULFATE` are stored as two-component structures that
ChEMBL keeps as their own parent, and `MINOXIDIL SULFATE` is named as a salt but is stored with a
single component. The cohort was declared before any activity row was fetched, to exercise every
branch of the counting rules. It is a teaching cohort, not a random sample, and no rate computed
over it estimates a population quantity.

The ChEMBL bulk artefacts are deliberately not used. The release directory lists a SQLite dump of
5,764,252,857 bytes, a MySQL dump of 2,101,694,224 bytes, a PostgreSQL dump of 2,088,889,426 bytes
and an SDF of 931,156,420 bytes, all measured on 2026-10-21. The REST API carries the measurement,
the entity, the assay, the document, the target and the relation in one row, which is the whole
point of this lab, so the dumps would be paid for and not used.

## Frozen protocol

The protocol version is `chembl37-decision-unit-scope-v1`, in [`protocol.json`](protocol.json). The
compiled-in contract in `labs/src/aidd_commons/decision_unit_scope/protocol.py` is the authority for
every load-bearing field, and the on-disk JSON must match it field for field or the pipeline
refuses to run.

The unit of inference is the ChEMBL parent molecule. Every activity row carries both the form that
was actually tested (`molecule_chembl_id`) and the parent entity the row is filed under
(`parent_molecule_chembl_id`), and the count is kept on the parent.

A row whose `molecule_chembl_id` differs from its parent is a salt or mixture form of that parent.
It is **admitted**, and counted separately as a salt-form measurement, because it is a real
measurement of the parent entity obtained on a different formulation, and dropping it would
silently discard part of the compound's evidence. This is a deliberate protocol decision, and it is
the opposite of the rule in `labs/chembl_egfr`, where `aidd_commons.chembl_egfr.data` raises a
contract error for any child row. That rule is right for a lab that fits one model on one parent
structure and wrong for a lab whose subject is the unit of inference, where the child row is
evidence rather than an error. The two labs therefore disagree by design, and this protocol says so
rather than hiding the difference.

The endpoint is a nanomolar potency: one of `AC50`, `EC50`, `IC50`, `Kd` or `Ki` in nM with a
relation symbol. A row with `=` is a point measurement. A row with `>`, `<`, `>=` or `<=` is a
bound, and a bound is never pooled with a point value. A row with no relation symbol is neither,
and is set aside. The exclusion reasons are applied in a declared order, so they partition the input
rows exactly: outside the endpoint family, outside nM, not curated into ChEMBL's standard fields,
flagged as a potential duplicate, carrying a data-validity comment, missing a value, missing a
structure, missing a relation.

The grouping unit is `(assay, document, endpoint type)`. Two admitted point measurements are the
same measurement when they share all three, because one experiment in one paper reporting one
endpoint is one number. The experiment unit `(assay, document)` is reported alongside it.

Nothing in this protocol is fitted, tuned, scaled or selected. The only transformations are the
declared exclusion order, the declared point/bound classification and the declared grouping key.
Because nothing is fitted, the calibration rule, the selection budget and the stop rule are all
declared as not applicable, and the protocol says why in each case: there is no score to calibrate,
no candidate to select and no number that decides whether to continue. The stop rule is simply that
the thirteen declared artefacts have been fetched and re-validated.

## Setup

From the repository root:

```bash
uv sync --group dev
```

## Reproduce

```bash
uv run python labs/decision_unit_scope/run_lab.py download
uv run python labs/decision_unit_scope/inspect_decision_unit_scope.py show
uv run python labs/decision_unit_scope/inspect_decision_unit_scope.py check
uv run python labs/decision_unit_scope/export_summary.py
```

`download` writes thirteen artefacts to `.cache/decision_unit_scope/` (git-ignored): the status
payload, the fifteen seed molecule records, the activity rows of the ten parent molecules, and the
assay records behind every admitted row. A cold run makes 41 HTTP requests and moves 9,794,036 bytes
over the wire; the cache it leaves behind is 11,883,104 bytes, because each artefact is written in
this lab's own deterministic serialisation. The download is resumable and idempotent: an artefact
whose cached byte length still matches the value frozen in the protocol is kept and not fetched
again, and a missing or mismatched one is fetched again. The ChEMBL status endpoint is contacted on
every run regardless, because the live release assertion is the point of the check; that is the one
request a complete cache still makes. A cold run takes about five minutes; a warm cache takes
seconds.

`show` prints the entity resolution, the admission funnel, the per-compound census and the named
examples. `check` recomputes the invariants and exits non-zero on any violation. It runs with no
network and no cache: the committed [`summary.json`](summary.json) is enough for the summary
invariants, and when the cache is present the census is recomputed from it and compared with the
summary. `export_summary.py` writes `labs/decision_unit_scope/summary.json`, overwriting it in
place; it is a derived artefact, and rerunning it against the same cache reproduces the file
exactly.

There is no one-time evaluation in this lab and nothing is locked. The protocol holds nothing out,
because it fits nothing and predicts nothing; the cohort is read end to end and every count is
published. The frozen part is the contract and the source release, not a single-use run.

## What to inspect

The committed result, computed 2026-10-21 against ChEMBL 37:

| Quantity | Value |
| --- | ---: |
| Declared ChEMBL molecules | 15 |
| Distinct parent molecules after resolution | 10 |
| Activity rows ChEMBL files under the ten parents | 13,305 |
| Admitted point measurements | 488 |
| Admitted bounds | 516 |
| Independent measurements, grouping unit (assay, document, endpoint) | 486 |
| Independent experiments, (assay, document) | 484 |
| Point measurements reported on the parent structure | 417 |
| Point measurements reported on a salt or mixture form | 71 |

The admission funnel, cohort-wide:

| Stage | Removed | Remaining |
| --- | ---: | ---: |
| Reported rows | 0 | 13,305 |
| Outside the endpoint family | 5,517 | 7,788 |
| Outside nM | 11 | 7,777 |
| Not curated into ChEMBL's standard fields | 6,363 | 1,414 |
| Flagged as a potential duplicate | 70 | 1,344 |
| Carrying a data-validity comment | 286 | 1,058 |
| Missing a value, or missing a structure | 0 | 1,058 |
| Missing a relation symbol | 54 | 1,004 |
| Set aside as bounds | 516 | 488 |
| Admitted point measurements | 0 | 488 |

Three findings are worth a reader's attention.

**A row count is not a measurement count.** `VALPROIC ACID` (CHEMBL109) has 6,294 activity rows in
ChEMBL 37 and 27 independent measurements under this protocol, a factor of 233.1. The rows are
mostly not potency measurements at all: 482 report a tissue severity score, 364 a bare `Activity`
outcome, 298 an ED50, 128 a body weight, 119 a TD50, and a further block reports haematology and
cell-count endpoints. Of the potency rows in the declared family, 125 survive as bounds rather than
values, and 124 of those are "greater than 10,000 nM". A reader who counted rows would have
overstated this compound's evidence base by more than two orders of magnitude.

**Half the surviving rows are bounds, not values.** Across the cohort, 516 of the 1,004 admitted rows
are censored bounds and 488 are point measurements. A bound is a real measurement and a useless
number: it cannot be averaged with a point value, and a compound whose only surviving evidence is
`IC50 > 10000 nM` has not been shown to be potent at all.

**The salt case is not an edge case.** Of the 488 admitted point measurements, 71 were reported on a
salt or mixture form of the parent rather than on the parent structure. `DARBUFELONE`
(CHEMBL275835) is the extreme: 5 of its 12 admitted measurements come from `CHEMBL109745`,
`DARBUFELONE MESYLATE`, the salt of the same compound. A reader who treated the two ChEMBL records
as two compounds would have compared a salt against its own free base and called the difference a
property of the molecules. The declared cohort contains five such pairs, which is why fifteen
declared molecules resolve to ten units of inference.

One reported value, with everything that has to travel with it. `VALPROIC ACID`, activity 495981,
`IC50 = 89000 nM`, was measured on the salt `CHEMBL433` (`VALPROATE SODIUM`), in assay
`CHEMBL646326` (binding assay, ChEMBL confidence score 8, no assay organism recorded), in document
`CHEMBL1125615` (*J. Med. Chem.*, 1991), against `CHEMBL4049` (aldo-keto reductase family 1 member
A1, *Sus scrofa*). Seven pieces of that context change what the sentence means, and a reader who
wrote "valproic acid has an IC50 of 89 µM" would have kept none of them: the form that was tested,
the assay, the document, the target, the organism, the confidence score and the relation.

One compound in the cohort has no admissible measurement at all. `MINOXIDIL SULFATE` (CHEMBL906) has
four activity rows in ChEMBL 37 and zero admitted point measurements under this protocol: two rows
are not curated into ChEMBL's standard fields, one carries a data-validity comment and one is
outside the endpoint family. ChEMBL also stores it with a single-component structure, so its name
promises a salt its record does not contain.

`summary.json` carries the same numbers as counts and audits, plus the named examples, and no raw
rows, no structures and no bulk compound list. `inspect_decision_unit_scope.py check` recomputes
every one of them.

## Source terms

ChEMBL 37 is released by the European Bioinformatics Institute under the Creative Commons
Attribution-ShareAlike 3.0 Unported licence. The licence text was read directly from the release's
own `LICENSE` file at
`https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE`, and the release
`README` in the same directory states the same licence and asks that the attribution contain the
ChEMBL URL and the release version:

> ChEMBL data is from http://www.ebi.ac.uk/chembl - the version of ChEMBL is chembl_37.

This lab redistributes no ChEMBL data: the cache under `.cache/` is git-ignored and is excluded from
the curated public export, and the committed `summary.json` carries counts, identifiers and names
rather than structures or activity rows. The code in `labs/src/aidd_commons/decision_unit_scope/` and
`labs/decision_unit_scope/` is part of this repository and carries the repository's own licence.

## Limitations

The cohort is fifteen molecules chosen to exercise the counting rules. It is not a random sample of
ChEMBL, and nothing in it estimates how salt reporting, curation or endpoint coverage is distributed
across the database.

No uncertainty interval is reported, and none should be. Every number here is an exact count of a
fully enumerated declared set, not an estimate of a population quantity, so a confidence interval
around it would describe nothing. The same applies to the 71 salt-form measurements out of 488: it
is a count of what these fifteen molecules happen to look like in ChEMBL 37, not a rate with a
sampling error around it.

The endpoint scope is one declared family of nanomolar potencies. Rows reporting `ED50`, `GI50`,
`Potency`, `Activity`, `Inhibition`, percentage inhibition or haematology counts are outside it and
are counted as such, so the measurement counts here are counts *within that family* and would change
under a different declared family.

`standard_flag = 1` is ChEMBL's own marker that a value has been curated into the standard type,
units and relation, and `potential_duplicate = 0` is ChEMBL's marker that a value is not a repeat
citation of an earlier paper. ChEMBL's own schema documentation notes that a value of zero does not
guarantee that a measurement is novel or independent. This lab counts what the markers say and does
not claim more.

The grouping unit treats two rows of the same assay, the same document and the same endpoint type
as one measurement. That is a judgement about what constitutes an independent experiment, and a
different judgement would give different counts.

The assay context comes from the assay record, not from the activity row. The ChEMBL activity
endpoint does not carry the assay organism or the confidence score, so the lab fetches the assay
records for every admitted row; an assay whose organism is not recorded is reported as not recorded
rather than guessed. In this cohort, ChEMBL's own test-occasion identifier (`toid`) is populated on
thousands of rows and on none of the admitted potency measurements, so it is reported as a count and
not used as a grouping key.

The protocol reports what ChEMBL stores. Where ChEMBL keeps a salt as its own parent, or stores a
sulfate without the sulfate, this lab does not correct it; it reports the stored structure's
component count and the resolution, and leaves the correction to the reader.
