# Reader session log

One row per session. This file is a blank template. No reader session has been
run, and no outcome is recorded here. Keep the completed log with the session
notes and outside the public source package.

## How to fill the log

Add one row as each session ends. Do not fill a row from memory afterwards,
and do not estimate a time.

| Session id | Date | Facilitator | Reader label | Session type | Start | End | Elapsed | Execution mode | What went wrong |
| ---------- | ---- | ----------- | ------------ | ------------ | ----- | --- | ------- | -------------- | --------------- |
|  |  |  |  |  |  |  |  |  |  |

## Column definitions

**Session id.** A short identifier you make up, in the form `S-2026-10-21-01`.
It ties the log to the observation sheet and to the batch roll-up. Do not put
a name in it.

**Date.** The calendar date of the session.

**Facilitator.** The person who ran the session.

**Reader label.** The anonymous label for the reader. Use the same label for
every session with the same person, so that one reader working in two
languages stays one reader.

**Session type.** One of `browser orientation`, `engineering task`,
`notebook session`, `paperqa source inspection`, `modelling transfer`,
`researcher decision`.

**Start and End.** Local timestamps carrying the UTC offset, written as
`2026-10-21T14:05:00+08:00`. Take both from a clock rather than from memory.

**Elapsed.** End minus Start, written as `26 min`. When the session included
installation or waiting, say so in the what went wrong column so that the
split between active work and setup stays visible.

**Execution mode.** One of `browser-only`, `local Jupyter`, `Colab`,
`local source copy`.

**What went wrong.** The first unresolved difficulty, where it happened (page,
cell or command), and the first useful error copied out verbatim with personal
details removed. Write `none observed` when nothing went wrong, so that a
blank cell is never ambiguous.

## Outcome vocabulary

Use these values wherever a task outcome is recorded, in this log, in the
observation sheets and in the batch roll-up.

`completed without help`, `completed with help`, `stopped`, `skipped`,
`not observed`.

A skipped unit is not a failed task. A browser-only reader who never executes
a cell has an unobserved execution outcome rather than a failed one. Record
elapsed time only when it was measured.

## The batch roll-up

The [batch roll-up](batch-rollup.csv) holds one row per reader per dimension,
and it is the artefact that a completion rate is computed from. A dimension is
one of `navigation`, `interpretation`, `help`, `execution mode` or `time`.

Completion level for the navigation and the interpretation dimension uses the
outcome vocabulary above. Completion level for the help, the execution mode
and the time dimension is `recorded` or `not recorded`, because those three
describe the session rather than carry a task outcome.

The completion denominator counts one unit for each navigation or
interpretation row whose level is `completed without help`,
`completed with help` or `stopped`. A `skipped` unit does not count, because a
skipped unit is not a failed task, and a `not observed` unit does not count,
because nothing was observed. The help, the execution mode and the time
dimension never count. Every row that does not count carries a short reason,
and a row that does count carries none. A completion rate that excludes help
is read from the task rows whose level is `completed without help`.

A row whose record kind is `example` never counts. The template ships example
rows so that the shape is visible, and they are excluded from every rate. Every
example row carries that exclusion in its reason, so the exclusion is visible
in the file rather than in the reader's memory.

## A filled roll-up row, for illustration only

| record_kind | reader_label | session_id | session_type | dimension | observed_value | completion_level | counts_toward_denominator | exclusion_reason |
| ----------- | ------------ | ---------- | ------------ | --------- | -------------- | ---------------- | ------------------------- | ---------------- |
| observed | reader-a | S-2026-10-21-01 | browser orientation | navigation | reached the representation lesson from the pathway map | completed without help | yes |  |

This row shows the format of a row that reaches the completion denominator. It
is not collected evidence, and the roll-up ships no collected row.

## A filled session row, for illustration only

| Session id | Date | Facilitator | Reader label | Session type | Start | End | Elapsed | Execution mode | What went wrong |
| ---------- | ---- | ----------- | ------------ | ------------ | ----- | --- | ------- | -------------- | --------------- |
| example-session-01 | 2026-10-21 | example-facilitator | example-reader-a | browser orientation | 2026-10-21T14:05:00+08:00 | 2026-10-21T14:31:00+08:00 | 26 min | browser-only | none observed |

This row shows the format only. It is not a recorded session, and it must not
be copied into the log above.
