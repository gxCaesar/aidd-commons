# Generation gate teaching lab

This lab covers the two decisions that surround a generative run: what the
objective was, frozen before any candidate existed, and which of six gates each
candidate survived. It runs no generative model, makes no network request, and
proposes nothing for synthesis or measurement.

Run from the repository root:

```bash
python labs/generation_gate/inspect_gate.py objective
python labs/generation_gate/inspect_gate.py screen
python labs/generation_gate/inspect_gate.py check
```

Unlike the other offline inspectors in this repository, this one requires RDKit,
because the gates are computed from structures rather than read from a record.
Nothing else outside the standard library is used.

## Files

| File              | What it is                                                                                                                         |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `objective.json`  | The frozen design objective: target context, desired properties, prohibited motifs, synthesis limits and the experimental decision |
| `candidates.json` | Twenty candidates authored by hand, each labelled with the single gate it was written to exercise                                  |
| reference set     | `labs/freesolv/results/splits/scaffold.csv`, the committed 642-molecule split table from the completed FreeSolv lab                |

No generative model produced the candidates. The `constructed_for` label is a
teaching annotation: gates are computed from structure, and a test asserts that
relabelling every candidate changes no gate outcome.

## What the two halves teach

The objective is checked for the fields that make each part applicable. A
property without a two-sided bound is a wish, a prohibited motif whose SMARTS
does not compile silently stops excluding anything, and an objective with no
experimental decision cannot say what a passing candidate is for. When the
objective fails these checks the screen is not run against it, because an
uncheckable objective cannot be applied.

The screen applies six gates in order, and every gate's denominator is the
previous gate's survivors. That is why the single headline figure and the
survivor count differ so widely on the committed set. Two further points are
printed rather than left to be inferred: memorization is the novelty gate applied
to a narrower reference set rather than a seventh gate, and route feasibility is
recorded as `not_assessed` because structural proxies cannot establish it.

## What the checks lock

Seventeen checks. Tests are in `labs/tests/test_generation_gate.py`; eleven of
them are known-bad edits covering an objective that drops its decision, a bound
retrofitted so a stopped candidate would pass, a misdeclared reference set size,
and a claim of route feasibility from proxies alone.

The bilingual lesson is at
`site/src/content/docs/labs/generation-gate.mdx` with its Chinese edition under
`zh-cn/`.
