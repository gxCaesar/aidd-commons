# Contributing to AIDD Commons

AIDD Commons accepts source records, corrections, lessons, labs, reproducible experiment reports, translations, accessibility fixes, and engineering improvements. The governing rule is simple: a reader must be able to distinguish what a source directly establishes from what the project decides, infers, or has not verified.

Start with the matching issue form. Small factual corrections may go directly to a pull request when the evidence and affected paths are unambiguous. Material changes to scope, schema, evaluation policy, licensing, or governance require an RFC.

## Source records

Store one resource per YAML file under `catalog/resources/`. Use a stable lowercase kebab-case `id`; do not rename an established ID merely to improve wording. Follow [the resource schema](docs/RESOURCE_SCHEMA.md) and validate both the record and its cross-record relations.

For every claim:

1. Open the primary source rather than relying on a search snippet.
2. Add the direct source URL to `evidence`.
3. Declare the exact fields that source supports.
4. Link status, access, openness, and licence values to their evidence IDs.
5. Use `unverified` when the opened material does not establish the field.

“Open” is asset-specific. Inference code, training code, weights, architecture, data recipe, training data, and evaluation code must be assessed separately. A public paper, demo, API, repository, or model card does not by itself establish the other dimensions.

Run:

```bash
pnpm catalog:validate
pnpm catalog:build
```

## Lessons and language editions

Canonical scientific content is written in English. Chinese content includes onboarding, pathway summaries, and translations of the current lessons and lab guides; it must preserve the same numerical values, caveats, evidence scope, and uncertainty. Translation is semantic work: do not strengthen claims, remove conditions, or convert `unverified` into a positive or negative assertion. Numerical panels and downloads retain their original format.

Each substantive chapter should state its prerequisites, learning outcomes, data contract, strongest relevant cheap baseline, evaluation traps, openness constraints, and last review date. Use [the editorial guide](docs/EDITORIAL_GUIDE.md) and the curriculum chapter template.

## Labs and experiment reports

Freeze the scientific protocol before evaluating a held-out test set. At minimum record the data version, sample identity, labels, split unit, baseline, metric, selection rule, seed policy, exclusions, and uncertainty unit. Fit transforms and calibration only on permitted training or validation data. A lab must preserve negative results and must not claim state of the art without a matched protocol and current comparison audit.

Keep notebooks executable from a clean CPU environment when the task permits. Notebook output should be compact and reproducible; large or restricted data stay outside the repository with lawful download instructions.

## Review and corrections

For a first-reader session, use the blank [reader observation forms](docs/reader-trial/)
and separate navigation, interpretation and optional installation. Facilitator
answer sheets and actual reader notes stay outside the public source package.
Send source-backed corrections through the repository's correction issue template.
A prepared form or successful software test is not evidence that a reader
completed the exercise.

Reviewers check scientific scope, source support, licensing, language parity, accessibility, and executable behavior in proportion to the claim. A merged statement can still be corrected. Corrections keep a visible record, identify the affected version, and propagate to generated exports, lessons, and report prose. A resource is deprecated rather than erased when its historical identity or relations remain useful.

## Licences

By contributing original software, you agree that it is released under Apache-2.0. By contributing original prose or figures, you agree that they are released under CC BY 4.0. You must have the right to contribute the material. Third-party terms remain in force and must be retained beside the relevant asset; see [third-party notices](THIRD_PARTY_NOTICES.md).

## Safety and conduct

Do not post confidential information, personal data, access tokens, or restricted materials. Content that materially increases harmful biological operational capability must be escalated according to [SECURITY.md](SECURITY.md) before public discussion. Participation is governed by [the Code of Conduct](CODE_OF_CONDUCT.md).

## Local verification

Run the smallest relevant check first, then the full documented check before requesting review. Report exact commands and observed results, including failed or unavailable checks. Do not include private workflow records in a public artifact.
