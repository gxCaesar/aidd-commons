# Screening transport teaching lab

This lab asks whether a screening result transports between contexts, and
whether either context could measure the effect being claimed. It reads the
completed pool-budget replay and the ChEMBL development summary already committed
here. It fits nothing, runs no model, and imports nothing outside the standard
library.

```bash
python labs/screening_transport/inspect_transport.py show
python labs/screening_transport/inspect_transport.py check
```

## The argument

A policy that loses in two assays looks twice as convincingly beaten as one that
loses in a single assay. That inference needs two things the headline never
carries.

**Independence.** The two replays share zero parent compounds, so the repeat is
over disjoint chemistry rather than the same molecules measured twice. That is
what makes it worth something. What holds it back is in the record's own
disclosures: both replays are retrospective on the same target, under one frozen
protocol, with one feature set and a penalty informed by an earlier lab.

**Resolution.** Recovery is counted in targets, and the two contexts hold 64 and
13 of them. One recovered target moves the score by 0.015625 in the first and
0.076923 in the second, so the coarser context measures in steps 4.92 times
larger. The same reported number means a different amount of evidence in each.

Expressed in that unit, two things become visible. The whole five-instance
baseline spread is under two recovered targets in both contexts, so it cannot
carry an error bar. And the outcome that sounds most decisive is the weakest: in
the assay where the designed policy recovered nothing at all, it lost to the
worst random instance by **0.12 of a single target**.

## What it cannot address

Off-targets, because both replays are assays on the same target, and the topic
names off-targets. Prospective follow-up, because both replays are retrospective
on completed measurements. The lab prints both rather than leaving them to be
noticed.

## What the checks lock

Eleven checks. Tests are in `labs/tests/test_screening_transport.py`; five are
known-bad edits covering equalised target counts, a widened seed spread, a
designed policy that wins somewhere, overlapping parents and a dropped seed.

The bilingual lesson is at
`site/src/content/docs/labs/screening-transport.mdx` with its Chinese edition
under `zh-cn/`.
