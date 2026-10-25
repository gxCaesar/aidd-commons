# Governance

## Purpose and authority

AIDD Commons is a contributor-led educational and reference project. Maintainers are responsible for scientific integrity, editorial coherence, release quality, community safety, and stewardship of the project's public licences. Governance does not confer authority over third-party projects listed in the Atlas.

Current project decisions are recorded in public issues, pull requests, and RFCs. The project charter defines scope; an accepted RFC may amend it. A source record never becomes true by vote: factual and licence claims still require supporting evidence.

## Roles

- **Contributors** propose sources, corrections, lessons, labs, experiments, translations, designs, and code.
- **Reviewers** assess a bounded contribution for source support, scientific validity, licensing, accessibility, or engineering quality.
- **Maintainers** merge contributions, manage releases, appoint reviewers, apply moderation, and resolve routine editorial conflicts.
- **Stewards** handle private security, biosecurity, and conduct reports. A maintainer may act as a steward, but should recuse when conflicted.

Roles are earned through sustained, accurate work and respectful review. Maintainers document appointments and departures publicly. No role permits a contributor to approve their own disputed scientific or licence claim.

## Decision process

Routine changes use lazy consensus after review. A maintainer may merge when required checks pass, material objections are resolved, and the evidence supports the stated scope. Silence is not consent for a breaking change.

An RFC is required for changes to project scope, canonical language policy, resource schema semantics, lab evaluation rules, licence policy, governance, or safety boundaries. The RFC must state the decision, evidence, alternatives, affected users, migration plan, and conflicts. Maintainers seek rough consensus. If it cannot be reached, unconflicted maintainers record a decision and the strongest unresolved objection. Decisions may be revisited when new evidence appears.

## Scientific disagreements

Disagreement is resolved against the defining artifact: the opened primary source, dataset documentation, code, split, metric, or observed output. Reviewers separate four states:

- **Observed source fact:** directly supported by cited material.
- **Project decision:** a declared curricular, engineering, or editorial choice.
- **Open question:** material evidence is incomplete or contested.
- **Future work:** intended but not yet implemented or measured.

If evidence remains insufficient, the public statement is narrowed or marked `unverified`. Popularity, affiliation, and benchmark reputation do not substitute for a matched comparison.

## Corrections and deprecation

Maintainers triage credible corrections promptly. High-impact errors involving safety, licensing, data leakage, or a headline result receive priority. The correction identifies affected artifacts and updates every generated surface. Material report corrections are listed in the next release notes.

Records are deprecated when a resource is withdrawn, superseded, inaccessible, or outside maintained scope. Historical records may remain with a clear lifecycle state and successor relation. Removal is reserved for content that cannot lawfully or safely remain, duplicates with no independent identity, or personal information.

## Learning questions and exchange

The current public exchange route is GitHub Issues. The learning-question form
accepts English or Chinese and requires only the relevant lesson, resource or
exercise and the question. An attempted solution is helpful but optional.
Corrections, reproduction reports and contribution proposals have separate
forms linked from the website's Contribute page. Reading the website does not
require a GitHub account; posting an issue does.

A maintainer triages a new question to the relevant scientific object and
records who will answer or review it. Questions about interpretation should
receive an explanation with a source or a worked step. Execution questions
should identify the attempted runtime and first useful error before proposing
a fix. A factual correction follows the correction process above. When a useful
answer improves a lesson, the follow-up change links back to the question and
updates both language editions where applicable.

Maintainers distinguish an answered question from a verified reproduction and
an accepted content change. They keep unresolved points visible and do not
close a question merely because a program passed a test. Conduct and sensitive
reports follow the Code of Conduct and security routes rather than a public
scientific thread. Response times depend on volunteer availability; no response
rate, active forum or community impact is claimed by preparing these routes.

## Conflicts and recusal

Contributors and reviewers disclose employment, funding, authorship, investment, or close collaboration relevant to a decision. A conflicted maintainer may provide facts but should not be the sole approver of a disputed ranking, licence interpretation, correction, or enforcement action.

## Releases

Release status is based on observed validation, not aspiration. Coverage claims identify their denominator and date. Generated public releases are curated from an allowlist and exclude private operational material. Maintainers may delay a release for unresolved scientific, legal, safety, or reproducibility risk.
