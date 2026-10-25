# Design space teaching lab

This lab enumerates three declared candidate spaces exactly and tests four target
molecules against each. It reads one committed JSON file and uses RDKit to build
and canonicalise. **No molecule here is a design proposal** and no space is a real
screening library.

```bash
python labs/design_space/inspect_space.py show
python labs/design_space/inspect_space.py check
```

## Size and reach are different properties

A space is a construction plus its inputs. **The inputs decide how much of it
there is. The construction decides what is reachable.** Only the first is usually
reported.

| space               | nominal size | construction                          |
| ------------------- | ------------ | ------------------------------------- |
| `enumeration`       | 25           | one fixed core, two attachment points |
| `enumeration_grown` | 100          | the same core, longer lists           |
| `scaffold_hop`      | 25           | a different core, the original lists  |

## What growing bought

Going from 25 to 100 reached `t2` and left `t3` and `t4` exactly as unreachable as
before. **The core never changed, and no amount of substituent buys a new core.**

`t3` differs from a reachable molecule by **one atom in the ring**. It is
unreachable in both enumeration spaces at any list size, and reachable in the
third space, which is the same nominal size as the first.

The third space and the grown space **share no member at all**. Two spaces can be
disjoint without either being larger.

`t4` changes the linker and is reachable in none of the three. That is a statement
about these three constructions and nothing else.

## What reachability is not

Reachable means the construction can write the molecule down. It says nothing
about whether the molecule can be made, whether it would be stable, or whether it
is worth making. **A space is a generator, not a plan.**

## What the checks lock

Thirteen checks, including that every nominal size is recomputed as the product of
its input lists rather than read from a stated number, and that every declared
product actually builds so no space is quietly smaller than its inputs.

Tests are in `labs/tests/test_design_space.py`; seven are known-bad edits. The
bilingual lesson is at `site/src/content/docs/labs/design-space.mdx` with its
Chinese edition under `zh-cn/`.
