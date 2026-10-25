# Claims, evidence and unknowns audit

This CPU-only laboratory reads the committed comparison records directly. Its frozen selection is the foundations track, with 4 topics crossed with 13 audited providers. The project row supplies a strong recorded example and the AGIL row supplies a weakly resolved one. The laboratory does not rescore either provider.

## Data and method

The inputs are the provider YAML records, the topic taxonomy, the independent reading of AIDD Commons, and the generated comparison record carrying the two superlative claim fields. PyYAML reads the YAML files from their canonical locations. The protocol fixes provider filenames, track topics, state rules and claim conditions. The inspector checks all 1209 provider-topic cells against the comparison record's declared 591 direct and 618 default cells, then classifies the 52 cells in the selected track.

An explicit cell with resolvable evidence is a `direct-observation` of what the record states. An explicit `unverified` cell with a resolvable reference has a lower-upper depth interval and is a `bounded-inference`. A direct cell with no reference, an undeclared reference or a missing local evidence file is an `unsupported-claim`. An omitted topic takes the record's evidence-free `unverified` default and is an `unresolved-field`. These rules are applied in that order, so a default unknown is not counted as an unsupported assertion.

The independent reading uses the comparison's ordinal convention. Its `assessed` depth with no runnable basis is compared as `worked`. The recorded claim status is copied from the local comparison export. Numerical bound conditions are recalculated, while the public correction-window status is reported as recorded. The laboratory does not poll the public website or advance the window itself.

## Reproduction

Mode is a fresh independent computation over a frozen protocol and committed records. Use the project's Python 3.11 environment with PyYAML. No network, download or accelerator is needed. Run from the repository root. `check` and `show` write nothing. The exporter overwrites only this laboratory's compact summary after validation succeeds.

```bash
.venv/bin/python labs/claims_evidence_audit/run_lab.py check
.venv/bin/python labs/claims_evidence_audit/inspect_claims_evidence_audit.py show
.venv/bin/python labs/claims_evidence_audit/inspect_claims_evidence_audit.py check
.venv/bin/python labs/claims_evidence_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/claims_evidence_audit -q
```

The saved computation dated 2026-10-24 found 14 direct observations, 38 unresolved fields, 0 bounded inferences and 0 unsupported claims in the selected track. The project row and independent reading agree on all 4 examined topics. This snapshot records both superlative statuses as `not_established`. Their measured numerical bounds pass, and the correction-window status is `not_recorded` in that prepublication snapshot.

These dated observations are a worked example. The commands read the current committed comparison export, whose publication fields may change. The summary's `computed_on` date identifies the local calculation, while individual source-review dates remain attached to their records. When the comparison export changes, regenerate this laboratory's summary before checking it against the sources.

## Interpretation

An unresolved cell does not show that a provider lacks a topic. A recorded `absent` depth is still limited to the evidence surface reviewed by that provider record. The project row is a stated floor rather than a measure of teaching quality. This audit checks local evidence references and the saved comparison structure. It does not reopen external links, measure student learning or decide a provider's merits.

Original teaching code is Apache-2.0 and this prose is CC BY 4.0. The source records and independent reading retain their own dates and terms.
