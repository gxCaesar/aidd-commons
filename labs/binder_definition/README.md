# Binder definition teaching lab

This lab turns one set of molecules into several datasets by changing only the
definitions. It reads one committed JSON file and uses RDKit for scaffolds. No
model is fitted, no compound was assayed, and nothing here is a screening
proposal.

```bash
python labs/binder_definition/inspect_definition.py show
python labs/binder_definition/inspect_definition.py check
```

## The dataset stores no classes

Twelve measured compounds carry a value, twelve decoys carry none, and **nothing
carries a class label**. A class is produced by a choice, and storing one would
hide the choice. A test asserts the file contains no label field.

## What each choice does

**The cutoff.** Across the declared grid the same unchanged measurements yield
9, 8, 6, 4 and 4 positives. Nothing was measured again.

**The assay uncertainty.** At the primary cutoff of 6.0 with a declared
uncertainty of 0.3, four of the twelve compounds sit within that distance of the
cutoff, on both sides. Their class is a property of one reading rather than of
the compound.

**The negative class.** Measured inactives and decoys are different things.
Reported together, prevalence falls from 0.500 to 0.250 and **67% of the negative
class carries no measurement at all.** Precision of a random selector equals
prevalence, so the number any reported precision must beat was moved by a
decision about untested molecules.

**The generalization unit.** Twelve molecules collapse to four Bemis-Murcko
scaffolds, with three scaffolds carrying more than one molecule. One compound is
acyclic and has **no scaffold at all**, so the unit is undefined rather than
coarse, and the lab reports that instead of assigning one. At the primary cutoff
the six positives sit on three scaffolds, which is the number a test set can
spend.

## What it does not do

It fits no model and reports no performance. Every number moved because a
definition moved, which is the point: a benchmark can be made easier or harder
without touching a molecule.

It also does not rank the choices. A decoy set is a legitimate tool when its
assumption is stated. The failure is reporting decoys and measured inactives under
one word and quoting a metric over the union.

## What the checks lock

Sixteen checks. Tests are in `labs/tests/test_binder_definition.py`; six are
known-bad edits. Two of those found weak checks rather than broken ones: an assay
with zero declared uncertainty made every class look determined, and a scaffold
collapse test was satisfied merely by an acyclic molecule dropping out rather
than by any real sharing. Both checks were strengthened.

The bilingual lesson is at
`site/src/content/docs/labs/binder-definition.mdx` with its Chinese edition under
`zh-cn/`.
