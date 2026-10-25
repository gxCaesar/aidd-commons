# Agent evaluation task set over committed records

This laboratory fixes one task per selected laboratory. It checks source resolution,
execution correctness, recovery, claim accuracy and action authorization separately.
The unit is one task. A task passes only if all five dimensions pass. The material
is a set of repository records, not traces of a tool attempting these tasks.

## Mode and reproduction

Mode is a fresh independent CPU computation under the frozen protocol, reading
committed local records. Python 3.11 is required. No network, download, model
server or accelerator is used. Run from the repository root. `download`, `show`
and `check` write nothing. Export overwrites only this laboratory's compact
summary after the live checks pass. The named PaperQA test may use temporary
pytest files outside the committed material. It does not run a model.

```bash
.venv/bin/python labs/agent_evaluation_taskset/run_lab.py download
.venv/bin/python labs/agent_evaluation_taskset/inspect_agent_evaluation_taskset.py show
.venv/bin/python labs/agent_evaluation_taskset/inspect_agent_evaluation_taskset.py check
.venv/bin/python labs/agent_evaluation_taskset/export_summary.py
.venv/bin/python -m pytest labs/tests/agent_evaluation_taskset -q
```

The task set checks three laboratories. The claim-chain task reads its own
committed source manifest and summary, then runs its inspector. The PaperQA task
reads the retained reviewed example, its question corpus and the notebook
builder's literal example input, then runs the existing notebook test. The EGFR
task compares its declared input files with the files the inspector actually
loads, then runs that inspector. A claimed extra source fails resolution.

## Recorded result

| Dimension | Tasks passing |
| --- | ---: |
| Source resolution | 3 |
| Execution correctness | 1 |
| Recovery | 1 |
| Claim accuracy | 2 |
| Action authorization | 0 |

No task passes all five dimensions. The claim-chain record retains 7 differences
with its independent reading, but a disagreement is not a failed artifact.
The PaperQA example retains 1 limited-retrieval abstention and 1 reviewed
extra-prose error, which fails claim accuracy. The EGFR inspector checks
the selected settings and artifact relationships, but does not recompute every
locked metric from raw observations. Its historical locked action has an explicit
confirmation boundary but the curated files do not identify a human authorization
receipt. The other two records do not state an action-authorization decision.
Those gaps remain incomplete rather than becoming passing claims.

The inspector runs each task's own named check and records its exit code. A
passing exit is necessary but not sufficient. The claim-chain summary is rebuilt
from its committed inputs. The other two checks do not regenerate their complete
observed records, so execution correctness stays incomplete for those tasks.
The exporter records the observed failure when it matches the frozen expected
state. It refuses a changed result or false passing flag without writing. The
known-bad tests introduce an unused source and falsely mark a failed task as
passing. Both are rejected.

This audit does not evaluate a tool's competence, rank laboratories or verify
the science behind a result. No passing task exists in this set. Original code
is Apache-2.0 and original guide prose is CC BY 4.0. The committed records were
read locally on 2026-10-23.
