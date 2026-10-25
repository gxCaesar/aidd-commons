# Docking protocol teaching lab

This lab separates the seven components a docking score comes out of and works out
which reported numbers may be compared. **No docking program is run**, no
structure is prepared, and the reported numbers are illustrative rather than
results.

```bash
python labs/docking_protocol/inspect_protocol.py show
python labs/docking_protocol/inspect_protocol.py check
```

## The rule

Five components move the number: search, pose generation, scoring, rescoring and
constraints. Two move what it means: decoys and validation.

Two protocols may have their scores compared only when they are identical on every
component that moves the number. **Shared units are not shared scale.**

## The cleanest case

`p-baseline` and `p-rescored` differ in exactly one component. Same search, same
pose generation, same scoring function, same constraints, same decoys, same
validation, same ligand, same structure. One applies a second scoring function to
the top pose.

They report **-8.2** and **-10.7** kcal per mole. The 2.5 gap is entirely the
protocol.

No pair in the set is comparable, and the checker names which components block
each pair.

## The two that move meaning

`p-constrained` declares no validation and no decoys. It still produces a full
column of numbers, which is why those two components are the easiest to leave out.
The lab records what it therefore cannot report: any claim that its scores behave
as scores, and any enrichment figure.

## What the checks lock

Eleven checks. A protocol that is not fully declared stops the run before any
comparison is attempted. Tests are in `labs/tests/test_docking_protocol.py`; six
are known-bad edits, including reclassifying rescoring as not moving the number,
which would make two scales look like one.

The bilingual lesson is at `site/src/content/docs/labs/docking-protocol.mdx` with
its Chinese edition under `zh-cn/`.
