# Claim-chain evidence audit

This CPU-only laboratory reads 3 committed comparison records and assembles 2 declared chains. Each chain has 8 links, one for each role from mechanism through reproducibility. The counted unit is one link in one chain. The laboratory audits what the named teaching material supports. It does not assemble evidence for one compound or verify the material behind the project's own depth labels.

## Data and method

The frozen protocol names the self record, the independent reading and the taxonomy. PyYAML reads them from this checkout. There is no network access, download, model fitting or accelerator use. A link resolves when at least one evidence entry named by its self-record topic has `access: opened` and points to a local file. An empty list or a list with no opened entry leaves the link unresolved. An undeclared reference or a missing opened file is refused.

Depth follows the comparison audit's ordinal order. An `assessed` entry with no runnable basis is compared as `worked`. A worked case or written exercise does not license a measurement. An executable or assessed runnable task licenses only the task over its declared inputs. The weakest link is the minimum effective depth, with an unresolved link taking precedence. The audit also counts links below the strongest effective depth reached in the same chain. It reports agreements and differences with the independent reading after applying the same ordinal mapping to both records.

The rule is enforced during `check` and export. A chain with any unresolved link cannot be reported as a supported claim. A chain cannot establish a biological or therapeutic conclusion. It establishes only that each named link's material exists and says what it says, within those named topic endpoints.

## Reproduction

Mode is a fresh independent computation over the frozen protocol and the repository's own committed records. Use the project Python 3.11 environment with PyYAML. Run from the repository root. `download`, `show` and `check` write nothing. The exporter overwrites only this laboratory's compact summary after every check passes.

```bash
.venv/bin/python labs/claim_chain_audit/run_lab.py download
.venv/bin/python labs/claim_chain_audit/inspect_claim_chain_audit.py show
.venv/bin/python labs/claim_chain_audit/inspect_claim_chain_audit.py check
.venv/bin/python labs/claim_chain_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/claim_chain_audit -q
```

The committed computation on 2026-10-23 used Python 3.11.15 and PyYAML 6.0.3. Both chains contain 8 resolved links and have a `worked` weakest link. The `candidate-evidence` chain has 3 disagreements with the independent reading and 6 links below its strongest state. The `decision-handoff` chain has 4 disagreements and 5 links below its strongest state. All 7 disagreements have a deeper independent reading under the comparison convention. No independent reading is shallower than its self-record link in this selection.

## Interpretation

The selected topics come from different teaching materials and do not form a dossier for a shared candidate. A local evidence path and an `opened` access label do not prove that the underlying scientific statement is correct. The independent reading is another reading of teaching depth, not biological validation or observed student learning. The summary stores counts and boundaries without copying record bodies. Original teaching code is Apache-2.0 and this prose is CC BY 4.0.
