# Counterevidence dossier teaching lab

This lab inventories what this repository preserved about its own results. It
reads the eight completed lab artifacts already committed here, separates six
kinds of counterevidence that are normally collapsed into one "limitations"
paragraph, and recomputes the relationships the lessons quote.

It runs no experiment, fits nothing, makes no network request, and imports
nothing outside the standard library. It cannot establish that any result is
correct. It establishes that the counterevidence is still present and still says
what is quoted.

Run both commands from the repository root:

```bash
python labs/counterevidence/inspect_dossier.py show
python labs/counterevidence/inspect_dossier.py check
```

## The six classes

| Class              | What it is                                                          |
| ------------------ | ------------------------------------------------------------------- |
| `not-run`          | an evaluation declared in a protocol and deliberately not executed  |
| `negative-result`  | the method ran and lost to its own baseline                         |
| `undefined-metric` | a metric that could not be computed and was recorded as undefined   |
| `scope-limit`      | a disclosure that narrows what the completed result may be used for |
| `missing-record`   | an admitted gap in this project's own evidence                      |
| `retained-noise`   | measurement spread kept in the record rather than averaged away     |

Each one implies a different repair, which is why collapsing them makes a
dossier uninformative.

## Sources

`ARTIFACTS` in `inspect_dossier.py` names the eight reviewed summaries. They are
frozen completed evaluations: do not rerun, retune or re-sample them to obtain a
better-looking number. Adding a lab means adding its artifact here and updating
the counts the checks lock, which is deliberate — a new undefined metric or a new
not-run state should force a considered edit rather than pass silently.

## What the checks lock

Thirteen checks, covering the transfer failure recomputed from the committed
metrics, the two-sided disclosure of a shared-label exposure, the refused
correlations stored as `null` rather than zero, the seven not-run states, the
designed acquisition policy that lost both replays, and the outright refusal of p
values and confidence intervals.

Tests are in `labs/tests/test_counterevidence_dossier.py`; eight of them are
known-bad edits that delete or soften a disclosure and must be rejected. The
bilingual lesson is at `site/src/content/docs/labs/counterevidence-dossier.mdx`
with its Chinese edition under `zh-cn/`.
