# Publication and corrections

The canonical publication record is
[`catalog/comparisons/publication.json`](../catalog/comparisons/publication.json).
Null publication fields mean that first publication has not been recorded.
A local build, a release export and an intended public address do not start the
correction window.

After the release content is publicly accessible, record its actual first
publication time in `first_published_at`, using an ISO UTC timestamp ending in
`Z`. Record the working public repository, site and correction URLs in the same
change. The correction URL should open the repository's correction issue form
(`issues/new?template=correction.yml`). Verify that readers can open all three
URLs before recording them. Do not substitute a planned date or a local build
time for the first public availability of the release content.

The correction window lasts 30 full days from that timestamp. Its end is
calculated by the exporter; it is not a separate editable field. Regenerate the
comparison JSON, CSV and audit after recording publication:

```bash
PATH=/opt/homebrew/opt/node@24/bin:$PATH node node_modules/tsx/dist/cli.mjs scripts/comparisons/export.ts
```

The exporter accepts `--publication <file>` for an alternate record and
`--now <UTC timestamp>` for reproducible window checks. Normal builds use the
current time. The generated `status_checked_on` date identifies when the static
window status was checked; rebuild to refresh it. The comparison's scientific
`as_of` date remains the date of the source audit, rather than the publication
date.

The window status is `not_recorded` before publication, `open` for the first
30 days, and `elapsed` from the exact end of the interval. The export rejects
partial publication records, future publication timestamps, non-HTTPS public
URLs and any duration other than 30 days. These checks validate the record's
consistency; maintainers must verify actual public availability.

Readers can submit factual, licensing, coverage or reproducibility corrections
through the recorded public correction route. Identify the affected page or
record, the proposed correction and the supporting source. Maintainers handle
corrections under [`GOVERNANCE.md`](../GOVERNANCE.md), update the canonical source
and regenerate its public projections. The initial timestamp remains a record
of first publication, even when later releases change the content.

Both comparative claims remain `not_established` throughout this mechanism.
An elapsed window does not establish a claim automatically. Maintainers must
review submitted corrections and every claim condition before any separate,
evidence-backed change to public wording. Until then the project continues
“building the most comprehensive open AIDD learning system.”
