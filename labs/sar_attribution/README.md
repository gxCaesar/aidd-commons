# SAR attribution teaching lab

This lab explains a well-fitted model whose true cause is known, and shows the
explanation pointing away from it. It reads one committed JSON file, uses RDKit
for fingerprints with bit provenance, and NumPy to solve a ridge system.

No activity value here is real, no molecule was measured, and nothing is a design
proposal.

```bash
python labs/sar_attribution/inspect_attribution.py show
python labs/sar_attribution/inspect_attribution.py check
```

## The construction

The dataset stores **no labels**. It stores a rule: a molecule is active if and
only if it contains a carboxylic acid. Labels are computed from that rule every
time, so no label can drift away from its cause, and a test asserts the file
contains no label field.

A second substructure, an unsubstituted furan, is **perfectly correlated with the
cause in training** and has no causal role. Sixteen molecules, eight of each
class.

The confounder wins for a reason worth stating: it appears in an identical
environment in every active, so its fingerprint bits repeat, while the acid
appears in a different environment each time and its credit is spread across many
distinct bits. **Uniformity, not importance, concentrates weight.**

## Observed behaviour

Largest training error 0.0549, so the model fits. Per-atom credit is then traced
back through bit provenance. **The confounder outscores the true cause on 7 of 8
active molecules**, and every active molecule assigns positive credit to atoms
that cause nothing.

Four analogues break or control the correlation:

| id  | molecule           | cause | proxy | predicted | call |
| --- | ------------------ | ----- | ----- | --------- | ---- |
| a01 | `CCCc1ccoc1`       | 0     | 1     | +0.4908   | 0    |
| a02 | `OC(=O)CCc1ccccc1` | 1     | 0     | +0.4607   | 0    |
| a03 | `OC(=O)CCc1ccoc1`  | 1     | 1     | +0.9671   | 1    |
| a04 | `CCCCc1ccncc1`     | 0     | 0     | -0.0086   | 0    |

The pair that matters is a01 and a02. They have **opposite true activity**, the
model separates them by 0.0300, and it puts them in the **wrong order**. The
genuinely active molecule is called inactive at a threshold declared before
fitting.

## What it licenses

A hypothesis. An explanation reports which features the model used, which is a
fact about the model. Turning that into a claim about which atoms cause activity
needs an analogue that breaks the correlation, and that is an experiment rather
than a re-reading of the same fit.

It does not license a causal atom effect. On real activity data the generating
rule is unknown, so the comparison performed here is unavailable and the analogue
is the only route left.

## Reproducibility

The exact predictions depend on the fingerprint implementation. Observed with
RDKit 2025.09.6 and NumPy 2.4.6. The checks assert the qualitative relationships,
inverted ranking, credit share and fit quality, rather than the decimals, so a
library update changes the printed numbers without silently invalidating the
lesson.

Fourteen checks. Tests are in `labs/tests/test_sar_attribution.py`; five are
known-bad edits. The bilingual lesson is at
`site/src/content/docs/labs/sar-attribution.mdx` with its Chinese edition under
`zh-cn/`.
