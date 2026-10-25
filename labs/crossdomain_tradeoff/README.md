# Cross-domain nomination decisions without a composite score

This laboratory executes the candidate-nomination workbook's own rule. The
workbook states a fictional project's teaching thresholds, five required
inputs and the three next decisions a reader may take; this laboratory runs
that rule in one place, on the workbook's own teaching table and on the
measured ChEMBL 37 cohort, and reports what each candidate's inputs support.

The rule is the rule the curriculum teaches. The thresholds are matched potency
at most 50 nM, selectivity ratio at least 20, an exposure-to-effective-
concentration ratio at least 3, an independently reviewed safety package and
interpretable functional validation. They are teaching thresholds of a fictional
project and not pharmacological criteria, and the laboratory says so in every
summary it writes.

## Frozen data and computation

The protocol is [`protocol.json`](protocol.json). It declares the three
measured sources with their frozen byte lengths, the constructed teaching
table, the five inputs with their state rules and thresholds, the next
decisions, the rules and the excluded claims. The compiled contract checks
every decision-bearing field before execution. The ChEMBL activity, intrinsic
clearance and CYP inhibition readers are reused from
`aidd_commons.multi_endpoint_integration`, so the admitted records, the parent
resolution and the family maps are the ones that laboratory already validated.

One decision is one candidate. The teaching cases are the workbook's three
rows. The measured cohort is every parent the validated integration reads that
has at least two measured endpoint families, because a cross-domain decision
cannot be posed on a single measured family. For each candidate the laboratory
resolves every input, names the input that blocks the nomination in the
rule's order, reports the next decision the evidence points to, and grades the
evidence the supplied inputs rest on. No composite, no weighted sum, no
overall desirability value and no ordering of the candidates is produced, and
the audit refuses a decision that names a domain without supplying it.

## Fresh independent computation

Use Python 3.11 in the pinned `.venv`. The `download` command validates the
existing frozen caches and writes nothing. Once cached, the remaining commands
use no network and no accelerator. They do not alter the source cache.
`export_summary.py` overwrites the small committed summary only after all
checks pass.

```bash
.venv/bin/python labs/crossdomain_tradeoff/run_lab.py download
.venv/bin/python labs/crossdomain_tradeoff/inspect_crossdomain_tradeoff.py show
.venv/bin/python labs/crossdomain_tradeoff/inspect_crossdomain_tradeoff.py check
.venv/bin/python labs/crossdomain_tradeoff/export_summary.py
.venv/bin/python -m pytest labs/tests/crossdomain_tradeoff -q
```

## What the committed summary found

The committed [`summary.json`](summary.json) was computed on 2026-10-24 from
the existing frozen ChEMBL 37 cache.

**On the workbook's own teaching table the rule discriminates, and it agrees
with the lesson.** N1 is blocked by its selectivity ratio, N2 by its
exposure ratio and N3 by its missing safety package. The laboratory's computed
answer is therefore the lesson's worked answer, arrived at by computation: no
candidate satisfies the complete requirement, two point at a candidate to
revise and one at an evidence gap to close. The laboratory also refuses to
point any candidate at changing the product profile, because changing a
threshold so that a favourite passes is a change to the requirement and not a
discovery.

**On the measured cohort the rule cannot be posed at all.** Of the five
required inputs the measured families supply one: response potency, which is
absent for 57 of the 58 candidates and indeterminate for the one that has it,
because its admitted records mix endpoint types and no single potency value is
the family's. The other four inputs are not covered for any candidate, and
each for a stated reason. A comparison between CYP3A4 and CYP2D6 is not a
selectivity ratio against an intended target; in vitro intrinsic clearance is
not an exposure and cannot form an exposure-to-effective-concentration ratio
without a declared effective concentration; the cohort holds no measured
safety material, and a safety package is a human review that no measurement
supplies; and the measured assay records in this repository classify assay
records rather than validate a compound's function. All 58 candidates are
therefore blocked at the potency input, all point at closing an evidence gap,
and none completes a nomination.

That is the measured form of the point the endpoint-counting laboratory cannot
make on its own. A census that reports 7,908 compounds, 1,120 exposure
medians and 6,837 CYP inhibition measurements describes coverage of the
measured families. It says nothing about whether the inputs a nomination
decision needs are among them, and here they are not: the two families the
cohort has in abundance are not the two the rule asks for.

## Source and limits

The [ChEMBL 37 release](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/)
is dated 2026-05-01. Its [licence](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE)
is Creative Commons Attribution-ShareAlike 3.0 Unported, read on 2026-10-21.
The release [README](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/README)
gives attribution guidance. Original prose is CC BY 4.0 and original code is
Apache-2.0. The committed summary contains no activity rows and no
structures.

The measured records carry no confidence interval, so a gate evaluated on a
family's representative value is a statement about the admitted records and not
about a quantity with an error bar. The admitted ranges describe the records
the family admitted, not an uncertainty. Response potency does not validate
mechanism or intended-target engagement, and a measured in vitro clearance
does not establish systemic exposure. The laboratory nominates nothing, and no
candidate in it is a development candidate.
