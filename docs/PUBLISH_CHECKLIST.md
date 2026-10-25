# Publish checklist

This is a reusable checklist for each future AIDD Commons release candidate.
The unchecked boxes below are template fields, not the status of an already
completed release. [v0.2.1](https://github.com/gxCaesar/aidd-commons/releases/tag/v0.2.1)
was published on 25 October 2026 after all seven stages of its
[hosted validation and deployment](https://github.com/gxCaesar/aidd-commons/actions/runs/40161346027)
passed. Its accepted scope and exact-artifact checks are recorded in the
[public milestones and scientific limits](PUBLIC_ROADMAP.md).
Actual first public availability and the correction window are recorded in
[`PUBLICATION.md`](PUBLICATION.md) and its canonical metadata.

Publishing is a separate authorisation from building. The repository can be in
every state described below without anything having been published.

## What publishing means here

1. A public repository exists, with the release candidate as its content.
2. The site is served from a public address.
3. The comparison claim's sixth condition, a public thirty-day correction
   window, starts running. Until it has run, the project keeps the wording
   "building the most comprehensive open AIDD learning system".

## The gate

Every command below must pass on the commit that is published, in a clean
checkout, with no uncommitted changes. The release export is built into a
scratch directory, never over the committed snapshot.

```bash
export PATH=/opt/homebrew/opt/node@24/bin:$PATH
cd <repository root>

# 1. content and schema
node node_modules/tsx/dist/cli.mjs scripts/catalog/validate.ts catalog/resources
node node_modules/tsx/dist/cli.mjs scripts/curriculum/validate.ts
node node_modules/tsx/dist/cli.mjs scripts/comparisons/validate.ts

# 2. generated surfaces, regenerated from the canonical sources
node node_modules/tsx/dist/cli.mjs scripts/catalog/export.ts
node node_modules/tsx/dist/cli.mjs scripts/comparisons/export.ts
node node_modules/tsx/dist/cli.mjs scripts/curriculum/coverage.ts

# 3. the site
npm --prefix site run check
npm --prefix site run build

# 4. tests
node node_modules/vitest/vitest.mjs run --exclude 'tests/e2e/**'
.venv/bin/python -m pytest labs/tests -q
.venv/bin/python -m ruff check labs
.venv/bin/python -m mypy

# 5. links, citations and text encoding, against the built site
npm run links:internal
npm run citations:check
npm run text:check -- --rendered site/dist

# 6. browser and accessibility
node node_modules/@playwright/test/cli.js test tests/e2e

# 7. the curated export, built and scanned into a scratch directory
node node_modules/tsx/dist/cli.mjs scripts/release/build.ts \
  --destination tmp/release-final --inventory tmp/release-final.inventory.txt
node node_modules/tsx/dist/cli.mjs scripts/release/hygiene.ts \
  tmp/release-final --report tmp/release-final.hygiene.json

# 8. the export must be able to test itself, against its own code
(cd tmp/release-final && PYTHONPATH=labs/src python -m pytest labs/tests -q)
```

Step 8 is the one that catches a lab whose code does not ship while its tests
do. It is not optional, and the `PYTHONPATH` is not optional either. An
editable install of `aidd_commons` puts the working tree's package on the
import path, so without it the export's suite silently tests the working tree
instead of the export, and a broken export passes its own gate.

## Candidate checklist template

Complete a fresh copy for the candidate being checked. The completed v0.2.1
receipt above remains historical evidence for that release.

- [ ] The working tree is clean and the commit is the one intended for release.
- [ ] The generated surfaces are regenerated from the canonical sources and
      staged, so the repository matches what the site serves.
- [ ] The coverage document and the comparison report are the regenerated ones.
- [ ] Every hand-maintained count in the reader-facing prose matches the
      filesystem. The test that checks this is part of the gate.
- [ ] The claim wording still reads "building toward". The claim is not
      promoted by the release.
- [ ] The report's own stated coverage numbers match the regenerated comparison
      products. The test that checks this is part of the gate.
- [ ] The reader-trial answer key, the facilitator rubric, and the two
      notebook task sheets are absent from the export.
- [ ] The export contains no internal working material, no approval record, no
      task brief, and no checksum metadata.
- [ ] The release note states what changed, what was measured, and what was not
      run.

## Publication choices

| Decision | Why it cannot be automated | Note |
|---|---|---|
| The public repository's name and owner | it is an identity claim | `gxCaesar/aidd-commons` |
| The licence of the released code and prose | it is a rights decision | currently Apache-2.0 for code and CC BY 4.0 for prose |
| The deployment target and its address | it is an outward-facing service choice | GitHub Pages at `https://gxcaesar.github.io/aidd-commons/` |
| The release title and date | it is a naming decision | match the candidate version and date; v0.2.1 above is a historical acceptance example |
| Whether to mint a DOI and deposit a release | it is a permanent public commitment | no DOI deposit in this release |
| Who may correct the published record | it is a governance decision | the correction issue template is the route |
| When the thirty-day correction window starts | it is a public commitment to a date | record actual public source availability and check the correction route; verify the site before announcing completion |

## Publishing the verified export

Publish only the curated export with a fresh public history. Keep the internal
working tree, hidden execution state and facilitator answer sheets outside that
repository. Its CI builds the Pages artifact from another curated export and
deploys only after its checks pass. Enable GitHub Pages with the Actions source.
Record actual public source availability for the correction-window timestamp,
then verify the public pages and downloads, synchronize citation metadata and
tag the released commit.
Publication does not promote a coverage claim, establish reader outcomes, send
reader invitations or create a DOI deposit.

## If the gate fails

Read the failing command's own output before changing anything. Most failures
in this repository have historically been a stale generated surface or a
hand-maintained count, and both are fixed by regenerating or by letting the
count test tell you which sentence is wrong. A failure that comes from a real
scientific disagreement is not fixed by regenerating anything; it goes to the
comparison record and is resolved there, in the open, with the evidence.
