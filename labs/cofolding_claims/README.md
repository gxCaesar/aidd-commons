# Claim separation teaching lab

This lab separates five claims that arrive in the same file format: monomer
prediction, complex prediction, co-folding, pose generation, and experimental
binding evidence. It reads records, not structures. It runs no model, makes no
network request, imports nothing outside the standard library, and evaluates no
system's accuracy.

Run both commands from the repository root:

```bash
python labs/cofolding_claims/inspect_claims.py show
python labs/cofolding_claims/inspect_claims.py check
```

`show` groups the registered systems by the claim their declared task licenses
and prints the three places where two claims are invited to merge. `check`
recomputes ten relationships across the extract and exits non-zero if any fails.

## Why an extract rather than the registry

`inspect_claims.py` reads `claim-records.json`, committed beside it, rather than
the published registry at `site/public/data/resources.v1.json`. That path is a
build artifact under an ignored directory, so a lab reading it would not run
from a clean checkout.

Regenerate the extract after a registry change:

```bash
python labs/cofolding_claims/export_claim_records.py            # report differences
python labs/cofolding_claims/export_claim_records.py --update   # replace it
```

Without `--update` an existing extract is never overwritten. The script names
each record that would change and exits non-zero, so a registry edit cannot
silently move a number the lesson quotes. Membership in the extract follows the
declared task and nothing else, so no system can be hand-picked in or out.

## What the checks do and do not establish

The checks verify the extract's internal consistency and the separation between
claim classes. They say nothing about whether any system's predictions are
accurate. One check records that no co-folding system in this family evidences
the evaluation code behind its accuracy claim, and the inspector names the 7
systems in the wider family that do publish theirs, which is a statement about
what was found on the declared review surfaces by the recorded date, not a claim
that the code does not exist.

The bilingual lesson is at `site/src/content/docs/labs/cofolding-claim-separation.mdx`
and its Chinese edition under `zh-cn/`. Tests are in
`labs/tests/test_cofolding_claims.py`.
