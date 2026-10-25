# Editorial guide

This guide turns the project charter into a reviewable authoring contract. It applies to canonical lessons, Chinese pathway content, Atlas records, labs, experiment reports, and the living report.

## Four statement classes

Use wording that makes each statement's authority visible.

1. **Observed source fact** describes what an opened paper, repository, licence, dataset page, standard, or measured artifact directly establishes. Cite it at the sentence or table row.
2. **Project decision** declares an AIDD Commons choice such as curriculum order, a frozen split, or an editorial threshold. Give the rationale and version.
3. **Open question** identifies missing, conflicting, or inaccessible evidence. Preserve `unverified` rather than completing the story by inference.
4. **Future work** describes an intended contribution that has not been implemented, reviewed, or measured.

Do not use an abstract, search snippet, benchmark name, or secondary roundup to support a more specific claim than it contains. Prefer a primary paper for science, official documentation for interfaces, and the asset's licence text for permissions.

## Chapter contract

A substantive chapter contains:

- a motivating decision or scientific question;
- explicit prerequisites and testable learning outcomes;
- entities, units, labels, masks, and provenance for any data discussed;
- the strongest relevant cheap baseline before complex methods;
- evaluation units, splits, metrics, uncertainty, leakage risks, and negative controls;
- asset-level openness and licence constraints;
- a worked example or executable lab when feasible;
- sources adjacent to claims and a fixed last-review date.

A chapter should not become a catalogue of model brands. Teach the invariants that let a reader assess a new method after the chapter is published.

## Resource workflow

Create one YAML file per resource and follow [RESOURCE_SCHEMA.md](RESOURCE_SCHEMA.md). Open every evidence URL. Separate lifecycle, access, and seven openness dimensions. An official project page may establish identity and purpose while leaving code, weights, data, or licence states unverified.

Run schema and relation validation before requesting review. Generated JSON and CSV are outputs, not hand-edited authority.

## Lab protocol freeze

Before test access, record the data version, exact samples, label construction, split/grouping unit, preprocessing fit scope, baselines, metrics, calibration rule, seed policy, selection budget, and stop rule. Keep the test split untouched until the protocol passes structural and finite-output checks on training and validation data.

After evaluation, publish the observed numbers without result-driven retuning. A surprising value triggers inspection for leakage, implementation error, or protocol mismatch. It does not authorize selecting a friendlier seed or redefining the metric.

## English and Chinese parity

English is canonical. Chinese onboarding, pathway summaries, lessons, and lab guides must retain quantities, negation, uncertainty, causal direction, licence scope, and applicability conditions. Translators may restructure sentences for clarity but may not strengthen evidence. Technical terms may retain their standard English forms where a Chinese translation would be ambiguous. Each translated lesson links its canonical original and records a translation date separately from source review. Shared numerical panels and downloadable artifacts retain their original format.

## Corrections and deprecation

A correction names the affected artifact and version, shows the decisive evidence, and propagates to generated surfaces. Preserve meaningful history in the issue or pull request. Deprecate a resource when users still need its identity or successor relation; remove only when lawful or safe publication is not possible or the entry has no distinct value.

## Editorial review checklist

- Are load-bearing claims supported by opened primary sources?
- Do evidence links support the exact fields that cite them?
- Are units, sample identity, splits, and comparison protocols explicit?
- Is uncertainty reported over the real independent unit?
- Are negative results and known limitations visible?
- Are code, weights, data, and other openness dimensions separated?
- Are third-party terms and acknowledgements adjacent and scoped?
- Does Chinese content preserve the canonical meaning?
- Are accessibility, keyboard use, reduced motion, and small-screen reading maintained?
- Does the change avoid materially increasing harmful operational capability?
