# Property decision teaching lab

This lab turns calibrated property evidence into a threshold decision that
includes an explicit abstention outcome. It reads the completed FreeSolv
baselines committed in this repository, applies a frozen rule, and reports the
region where no decision is available.

It fits nothing, runs no model, makes no network request, and imports nothing
outside the standard library.

Run from the repository root:

```bash
python labs/property_decision/inspect_decision.py evidence
python labs/property_decision/inspect_decision.py decide
python labs/property_decision/inspect_decision.py check
```

## The argument

A point prediction always yields a decision, because a number is always on one
side of a threshold. An interval does not. Requiring the interval to clear the
threshold makes the undecidable region visible instead of resolving it silently
in favour of whichever side the point estimate happened to fall on. That region
is the abstention band, and it is two conformal radii wide.

Three relationships in the committed numbers carry the lesson:

- **Only one of four split and model combinations reaches the nominal 0.9
  coverage it was built for**, and it is the one with the widest band.
- **The narrowest band has the largest coverage shortfall.** A tighter interval
  is not a better interval unless it still covers.
- **The point criterion and the interval criterion disagree on both splits**, and
  they disagree in the same direction, so it is not a split artefact. The model
  with the lowest error is not the model whose intervals support a threshold.

Together these say that more trustworthy intervals decide less, which is the
trade-off a threshold applied to a point estimate hides.

## What it cannot compute

How many real compounds fall inside the band. The completed FreeSolv lab
committed aggregate metrics and split membership, not per-compound test
predictions. The grid counts are arithmetic over a declared range on the
prediction axis, **not a sample of molecules**, and must not be read as a yield.
The lab prints this rather than leaving it to be noticed.

## Files and checks

`decision-rule.json` is the frozen rule: evidence source, threshold with a
statement of how its value was chosen, the three-way decision rule, the declared
prediction grid, and both selection criteria declared before the numbers were
read. The threshold is a teaching value and the arithmetic does not depend on it,
which a test asserts by moving it.

Twenty checks. Rule completeness is a precondition: when the rule is incomplete
it is **not applied to the evidence**, because a rule that cannot be applied has
nothing to be applied to. Tests are in `labs/tests/test_property_decision.py`;
eight are known-bad edits covering a rule that drops abstention, a threshold
presented as derived, evidence softened so a second combination appears to cover,
and a zero radius that would make a model look decisive.

The bilingual lesson is at
`site/src/content/docs/labs/property-decision-threshold.mdx` with its Chinese
edition under `zh-cn/`.
