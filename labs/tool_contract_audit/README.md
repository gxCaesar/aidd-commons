# Laboratory return-record contract audit

This laboratory reads the committed return records of the project's own
laboratories and checks each against a six-part contract. The counted unit is
one return record. The audit reads every local return record except its own,
because its own return record is the file this audit writes, and it measures
field coverage, explicit limits, companion protocol and README presence, and
field-specific verdicts. It does not copy source records into its summary.

## Mode and commands

The mode is fresh independent CPU computation over a frozen protocol. Use the
project Python 3.11 environment and the committed local records. No download,
network or accelerator is needed. `download` verifies the material and writes
nothing. `show` and `check` write nothing. The exporter overwrites only the
compact summary after the protocol and audit invariants pass.

```bash
.venv/bin/python labs/tool_contract_audit/run_lab.py download
.venv/bin/python labs/tool_contract_audit/inspect_tool_contract_audit.py show
.venv/bin/python labs/tool_contract_audit/inspect_tool_contract_audit.py check
.venv/bin/python labs/tool_contract_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/tool_contract_audit -q
```

The committed 2026-10-23 computation audits 20 records. All 20 carry
`schema_version`, `protocol_id`, `computed_on` and `software`. Explicit limit
fields appear in 6 records and are absent from 14, under seven different
names. All 20 audited laboratories have a protocol and a README. None of them
declares `environment`, `side_effects`, `outcome_status` or
`scientific_meaning` under the full contract, so all 20 are refused on those
named fields. A missing `outcome_status` is unknown, not a successful run.

A passing return record establishes a self-describing laboratory artefact. It
does not establish that a measurement is true, that the tool ran in its named
environment, or that the result can be reproduced from the record alone. The
allowed-write declaration is checkable against an independent trace, but a
return record does not provide that trace. No reader outcome was observed.

## Sources and terms

The source is the repository's committed laboratory return records, companion
frozen protocols and laboratory READMEs, read locally on 2026-10-23. Original
code is Apache-2.0 and original prose is CC BY 4.0.
