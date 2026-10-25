# Retrosynthetic disconnection teaching lab

This lab compares disconnection families and keeps route recovery apart from
laboratory feasibility. It reads two committed JSON files and applies reaction
SMARTS with RDKit. No model is trained or executed, no reaction is run, and
nothing here is a synthesis proposal.

```bash
python labs/retro_disconnection/inspect_disconnection.py compare
python labs/retro_disconnection/inspect_disconnection.py check
```

## Three families run, one is declared

| Family      | Coverage depends on                                          | Runs here |
| ----------- | ------------------------------------------------------------ | --------- |
| `rule`      | which transforms someone chose to write                      | yes       |
| `template`  | which classes the precedent set happens to contain           | yes       |
| `retrieval` | whether this exact molecule was already in the precedent set | yes       |
| `learned`   | the training distribution, which an output does not expose   | **no**    |

The learned family is declared without being run, and says why, so the
comparison states its own boundary instead of implying four families were
compared when three were.

## What the constructed set is for

Ten routes across four transformation classes. Five are in the precedent set,
which is both what retrieval may look up and what the templates were extracted
from. **The precedent set deliberately contains no suzuki-biaryl reaction.**

That single choice separates the families by cause rather than by score. All
three recover 5 of 5 inside the precedent set. Outside it, hand-written rules
recover 5 of 5, templates 3 of 5, and retrieval 0 of 5. Retrieval fails because
the molecules are not in its table; templates fail because no template exists for
a class the dataset never held; rules cover the class because someone wrote it.

Retrieval also shows what a split decides: 100% on the precedent subset, 50% over
everything. Neither number is wrong, and the memorising method is the one most
rewarded by choosing the subset.

The templates were extracted by hand rather than by an extraction algorithm, and
`methods.json` says so. The mechanical difference is not the lesson; the
consequence of provenance is.

## What it never establishes

`routes.json` records `laboratory_feasibility: not_assessed`. Nothing here
examines reagent availability, protecting groups, condition compatibility,
selectivity, scale or cost. A disconnection that recovers the recorded route can
still need a reagent nobody sells. This is the same boundary the generation gate
records when it calls its structural filters a proxy.

Recovery is also not selection. On three products the rules propose more than one
disconnection, and recovery means the recorded route was among the proposals.

## What the checks lock

Thirteen checks. A structure that does not parse stops the run before any family
is applied, because a family cannot be compared on a set that does not read.
Tests are in `labs/tests/test_retro_disconnection.py`; seven are known-bad edits.
The bilingual lesson is at
`site/src/content/docs/labs/retro-disconnection.mdx` with its Chinese edition
under `zh-cn/`.
