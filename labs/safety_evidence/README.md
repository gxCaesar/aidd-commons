# Safety evidence teaching lab

This lab separates the five kinds of safety evidence that a tox profile prints in
one column. It reads one committed JSON file and uses RDKit for substructure
matching.

**No outcome here is a real result**, no compound was tested, and nothing in this
lab is a safety assessment of any substance.

```bash
python labs/safety_evidence/inspect_safety.py show
python labs/safety_evidence/inspect_safety.py check
```

## The design decision

The record stores **findings that required an experiment**, and never stores an
alert. Alerts are computed from the structure every time. Storing an alert beside
a measured outcome is precisely the collapse the lab is about, so a check refuses
a record that does it and a known-bad test performs it.

## Observed on the committed record

**7 of 12** compounds match at least one alert. **5 of those carry no measured
finding at all** — their entire safety record is a pattern match. One compound
matches two alerts while carrying no finding: the alert count rose, the evidence
did not.

The levels disagree in both directions, and two of those directions are not the
same thing:

| situation                                | compounds               |
| ---------------------------------------- | ----------------------- |
| alert fired, a measurement said negative | c01                     |
| alert fired, nobody measured anything    | c03, c04, c05, c06, c07 |
| no alert, something measured positive    | c08, c09                |

An alert a measurement contradicted has been tested and lost. An alert nobody
checked has not been tested at all. Printing them the same way is how an alert
keeps authority it never earned.

**Dose context.** 2 of 7 assay outcomes carry no concentration, so they cannot be
compared with the ones that do, and recorded concentrations span a factor of four.
No exposure is declared anywhere, and the record says why that matters rather than
leaving the gap silent.

**The top of the pyramid.** 1 of 12 compounds carries any organism-level evidence.
That is the ordinary shape of a safety record and not a defect in this one. Alerts
are free, assays are cheap, organisms are expensive, and a profile page gives all
three the same amount of space.

## What it does not do

It assesses nothing. It also does not say alerts are useless: an alert is a cheap
prompt to look, and looking is what the other four levels are. The failure is
printing a prompt to look in the same column as the result of having looked.

## What the checks lock

Fourteen checks. Tests are in `labs/tests/test_safety_evidence.py`; seven are
known-bad edits, including writing an alert into a compound record and recording a
finding against an alert name rather than an assay system.

The bilingual lesson is at `site/src/content/docs/labs/safety-evidence.mdx` with
its Chinese edition under `zh-cn/`.
