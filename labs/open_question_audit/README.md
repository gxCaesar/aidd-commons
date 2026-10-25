# Open question audit

This laboratory reads the project's self comparison record, its independent
reading, and the topic taxonomy in place. The protocol fixes a literal
vocabulary for classifying the state of each topic-level question. It reports
whether the paired explanations still name a discriminating observation or a
specific missing measurement. The rule treats a generic request for more work
as an open question without a way to settle it.

## Reproduction

Mode is a fresh independent computation over a frozen protocol and committed
records. Use the project's Python 3.11 environment with PyYAML and CPU. No
network, download, or accelerator is needed. Run from the repository root.
The first three commands write nothing. The exporter overwrites only this
laboratory's compact summary after the live checks pass.

```bash
.venv/bin/python labs/open_question_audit/run_lab.py download
.venv/bin/python labs/open_question_audit/inspect_open_question_audit.py show
.venv/bin/python labs/open_question_audit/inspect_open_question_audit.py check
.venv/bin/python labs/open_question_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/open_question_audit -q
```

## Interpretation

The unit is one taxonomy topic. The inspector lists every topic under its
record state, the open topics with and without a named falsifier, missing
measurement families, and historical lowerings. The committed summary stores
these lists and counts without copying note or reason bodies. The six families
are overlapping categories of record wording, so their counts do not sum to
the number of topics.

This is a vocabulary audit of dated explanations. A phrase naming a missing
measurement is not evidence that the measurement was made. A local laboratory
result settles only its stated local computation. This audit neither answers
the scientific question nor ranks the curriculum tracks or measures learning.

Original laboratory code is Apache-2.0. Original guide prose is CC BY 4.0.
