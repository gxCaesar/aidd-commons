# Asset openness audit

This CPU-only laboratory reads the committed AIDD Commons resource catalogue and checks seven separate openness claims per record. It examines a frozen set of 24 records while counting the seven-field structure across the whole catalogue. It neither downloads resources nor tests their usability.

## Data and protocol

The source is the 228 YAML records in `catalog/resources/` in the local snapshot recomputed on 2026-10-25. The frozen protocol names the examined identifiers in order, the seven fields, the allowed claim values and a calendar-date rule for `last_verified`. The catalogue remains in its canonical location. No source snapshot is copied into this laboratory.

Each non-`unverified` status, access or openness claim must name an evidence entry in its own record. Every licence must have a name, a verbatim scope and a resolving evidence reference. The inspector flags a scope as limiting when its text contains the whole words `only`, `not`, `no separate terms` or `does not`, without inferring the legal effect of those words.

## Reproduction

Mode is a fresh independent computation under the frozen protocol. Use the project's Python 3.11 environment with PyYAML installed. All commands read local files, need no network or accelerator, and run from the repository root.

```bash
.venv/bin/python labs/asset_openness_audit/run_lab.py check
.venv/bin/python labs/asset_openness_audit/inspect_asset_openness_audit.py show
.venv/bin/python labs/asset_openness_audit/inspect_asset_openness_audit.py check
.venv/bin/python labs/asset_openness_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/asset_openness_audit -q
```

The first three commands write nothing. `show` prints the seven claims, their evidence identifiers, licences with verbatim scopes, access evidence, caveats and dates for each examined record. `check` exits non-zero for a collapsed dimension, an unsupported claim or a missing licence scope. The exporter writes only the compact `summary.json` after validation succeeds. A later catalogue edit changes the fresh audit; regenerate the committed summary only after reviewing that change.

## Interpretation and limits

The committed computation on 2026-10-25 used Python 3.11.15 and PyYAML 6.0.3. It found 57 `available`, 26 `not_applicable`, 83 `unverified` and 2 `not_available` cells among the same 24 examined records. Licences appear on 22 records, 0 access levels remain `unverified`, and 9 licence scopes contain a listed limiting phrase. All 228 catalogue records carry seven separate dimensions. These are counts of recorded claims under the stated procedure, not claims that artefacts were independently downloaded, executed or legally assessed. An `unverified` entry describes the review recorded in the catalogue; it does not establish that an asset does not exist.

Original teaching code is Apache-2.0 and this prose is CC BY 4.0. Source records retain their own terms. Their cited URLs, evidence labels and review dates travel with the per-record inspector output.
