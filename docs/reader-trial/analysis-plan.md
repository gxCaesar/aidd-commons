# Analysis plan for the first-reader trial

Facilitator copy, not for distribution to participants.

Reader outcomes are not observed until sessions are actually run. No reader
session has been run for this trial. Every number named in this document is a
procedure, and a procedure is not a result. The forms, the
[rubric](rubric.md) and this plan are instruments. Until a facilitator records
a human session on a sheet, every row of every sheet stays `not observed`, and
the trial's public status stays "not run".

## Scope

This plan covers the roll-up of one batch of reader sessions for one candidate
edition. It covers the sheets, the levels, the denominator of every rate, the
treatment of missing observations, the comparison of two facilitators, and the
rule that opens a content correction. It does not cover recruitment, the
choice of readers, the invitation process, deployment or publication, each of
which is a separate authorisation.

## Instruments

| Artefact | Role | Session types | Row identifiers |
| --- | --- | --- | --- |
| [Core session observation sheet](core-observation.md) | records the orientation tasks | `browser orientation`, `engineering task` | `CORE-01` to `CORE-06` |
| [Researcher decision session observation sheet](decision-observation.md) | records the decision and transfer tasks | `researcher decision`, `modelling transfer` | `DEC-01` to `DEC-04` |
| [Notebook session observation sheet](notebook-observation.md) | records the notebook tasks | `notebook session`, `paperqa source inspection` | row names, which the notebook sheet does not number |
| [Session log](session-log.md) | one line per session | all six | no instrument rows |
| [Batch roll-up](batch-rollup.csv) | one line per reader per dimension | all six | no instrument rows |
| [Rubric](rubric.md) | assigns a level to a recorded row | all six | every row above |

A reader's sessions are joined by the reader label on the sheet. The reader
label identifies a person, and the same reader's core session, notebook
session and PaperQA session carry it. Two language sessions by one reader are
one reader, and they are never counted as two.

## Relation to the session log and the batch roll-up

The session log declares the outcome vocabulary that the whole trial shares.
The observation sheets record the same events in more fields, and the two are
related by the mapping below. A report may use either, as long as it says
which one it used.

| Sheet field and value | Shared outcome vocabulary |
| --- | --- |
| Task status `attempted` with rubric level 3 | `completed without help` |
| Task status `attempted` with rubric level 2 | `completed with help` |
| Task status `attempted` with rubric level 1 | `completed without help` or `completed with help`, by the help type |
| Task status `stopped` | `stopped` |
| Task status `skipped by the reader` | `skipped` |
| Task status `not observed` | `not observed` |
| Task status `not assigned` | no unit, so no line in the roll-up |

The shared vocabulary records what happened to a task. The rubric level
records how much of the row's completion signal the reader produced. The two
are recorded side by side and are never merged into one code.

The session log records one execution mode per session and the sheet records
one per row. The sheet's `browser only` matches the log's `browser-only`,
`notebook executed locally` matches `local Jupyter`, `notebook executed in a
hosted runtime` matches `Colab`, and `local command executed` matches `local
source copy`. A row coded as not attempted keeps the session's mode in the
log and records the reason on the sheet.

Two completion rates can be computed from the same batch. The rate over the
rubric levels counts a completion made with recorded help as completed and
reports the unassisted count beside it. The rate over the shared vocabulary
puts only the unassisted completions in its numerator. The two agree on which
rows leave the denominator and on how a stop and a skip are treated, and they
differ in the numerator. A report states which rate it prints.

## The completion denominator

The completion denominator for one reader in one session is the set of rows
that the reader was assigned and that produced a witnessed outcome.

A row enters the denominator when its task status is `attempted` or
`stopped`. A row leaves the denominator when its task status is `not
assigned` or `not observed`. Every row that leaves the denominator is
reported with its status, and every row that leaves with `not observed` is
reported with its execution mode.

Which rows are assigned depends on the session type.

- `browser orientation` and `engineering task` assign `CORE-01` to `CORE-04`.
  They assign `CORE-05` and `CORE-06` only when the optional engineering task
  was offered, which the session header records.
- `researcher decision` assigns `DEC-01`.
- `modelling transfer` assigns `DEC-02` and `DEC-03`. It assigns `DEC-04`
  only when the optional execution task was offered.
- `notebook session` and `paperqa source inspection` assign the rows of the
  notebook sheet that belong to the session that was run, and the sheet
  records which rows were used.

The denominator counts rows and not readers, and its size is printed next to
every rate. A reader who was never offered the optional engineering task does
not carry its two rows, and a reader who was offered it and stopped carries
both.

The completion rate is the number of completed rows divided by the completion
denominator. Every report states the numerator, the denominator, the number of
rows that left the denominator and the reason for each of them. A rate is
never published without them.

## Which outcome codes count as completed

A row counts as completed when its rubric level is 2 or level 3. Level 2 is a
completion with recorded help and level 3 is a completion without help. Both
count as completed. The unassisted completion count is reported separately,
so that a handed-over answer is never reported as an unassisted completion.

Level 1 and level 0 do not count as completed. Level 1 covers an attempt that
produced no completion signal, a row the reader stopped on, a row the reader
declined, and an attempt that only repeated what the facilitator said. The
task status on the sheet says which of those happened, so a stop is never
reported as a plain missing completion.

The interpretation outcome codes `correct without help` and `correct with
help` are counted separately. They compare the reader's answer with the
organiser's answer notes, and they are never part of the completion rate. A
reader who reached the right answer for the wrong reason shows a completion
level and a separate correctness count, and the two are reported side by
side.

The task status, help type, navigation, interpretation and execution mode
codes are recorded per row. They are never summed into one score, and a
reader's rows are never averaged into a single reader score.

## A mode-dependent not observed and a stopped

A stop is an observation. A row coded `stopped` was watched, the reader began
the work, and the work ended. The sheet holds the preserved first useful
error, the three time numbers, and the point where the reader halted. The row
stays in the completion denominator, counts as not completed, and is reported
as a difficulty with its row identifier, its location and its reason.

A not-observed row is the absence of an observation. The row was offered and
nothing was witnessed, most often because the reader's mode left the row
impossible to witness. A browser-only reader has no execution row to observe.
A reader without an account has no hosted runtime to observe. The mode on the
sheet names that reason. The row leaves the completion denominator, is
reported with its mode, and is never reported as a failure and never as a
stop.

The distinction is the presence of evidence. A stop has a timestamp, an
artefact and a preserved error. A mode-dependent not-observed row has none of
the three. The sheet records the absence of the condition rather than the
absence of a result.

A not-observed row without a mode-dependent reason, for instance a session
that ended before the row was reached, also leaves the denominator and is
reported separately as missing data. No not-observed row is ever counted as a
failure.

The mode-dependent case is decided on the sheet, at the session, where the
facilitator saw what the reader could and could not do. The roll-up never
reclassifies a row.

The 15-minute setup timebox is a session rule, and the three time numbers are
its evidence. A stop recorded without the three numbers is reported as a stop
whose timebox is unevidenced, and it is not counted as evidence that the
timebox was applied.

## Batch roll-up procedure

1. The organiser collects the completed sheets for one batch into one working
   directory outside the public source package. One batch uses one candidate
   edition, and sheets from another edition are not mixed into it.
2. The organiser checks each sheet for a reader label, a session identifier, a
   candidate edition, a session type, and a filled task status on every row
   the sheet covers. A sheet missing one of these is returned to its
   facilitator before the roll-up and is not transcribed.
3. Sheets are keyed by reader label and session identifier. Two sheets for the
   same reader and the same session type are not merged. A duplicated session
   identifier is resolved by asking the facilitators, and never by editing a
   value on a sheet.
4. Each sheet is transcribed into one line of a batch table per instrument
   row. The line holds the reader label, the session identifier, the row
   identifier, the task status, the navigation outcome, the interpretation
   outcome, the help type, the execution mode, the three time numbers, the
   rubric level and the evidence note. The evidence note keeps the reader's
   own words. No field is filled from an expectation of what the reader should
   have said.
5. The batch table is split into the batch roll-up, one line per reader per
   dimension. The instrument row identifier travels with the line, so that a
   reader's six core rows do not collapse into one navigation line. A roll-up
   file with no column for the identifier takes it at the front of the
   observed value.
6. A second person checks the transcription of one reader per language against
   the sheet, and checks every sheet that carries a disagreement.
7. The roll-up computes, for each session type and for each instrument row,
   the assigned rows, the observed rows, the completed rows, the unassisted
   completed rows, the stopped rows, the rows that left the denominator with
   their mode, the count of correct interpretation outcomes, and the median
   active minutes.
8. A result from one reader is reported as that reader's result and never as a
   batch rate. A batch rate is reported only with its numerator and its
   denominator.
9. The batch table and the sheets stay outside the public source package.
   Neither is copied into the repository.
10. The trial's public status stays "not run" until a batch with real sheets
    exists. A roll-up over zero sheets is reported as zero sheets.

## Inter-rater procedure

When two facilitators record the same session independently, each keeps their
own sheet. The two sheets are paired by reader label and session identifier,
and they are not merged into one sheet before the comparison.

The facilitators first compare the recorded fields, which are the task
status, the navigation outcome, the interpretation outcome, the help type,
the execution mode and the three time numbers. Where the fields agree, the
two rubric levels are compared, and the comparison is recorded as agreement or
as disagreement.

Where the levels differ, the facilitators compare the recorded evidence with
the row's anchor in the rubric and settle the level against the anchor rather
than against their memory of the session. The outcome is recorded as
agreement after discussion, as one level recorded with the other level kept
alongside it, or as a disagreement that stays open. An open disagreement is
reported as a disagreement in the batch table and is never averaged into a
single level.

The disagreement rate is reported for the batch. A high disagreement rate
means the anchor is not observable enough, and the anchor is rewritten before
the next batch is recruited. The rubric is changed before new readers are
recruited and not after a level has been reported.

A third facilitator adjudicates only the rows that stay open. Their level is
recorded next to the two original levels, and a level that changes after
adjudication is reported with the change while the earlier level stays in the
record.

## The rule that opens a content correction

The batch is the trigger for a content review, and the review decides the
change. The rule is as follows.

A content correction opens when a recorded row shows that the material led a
reader to a wrong scientific conclusion or to an action that is unsafe, even
when it was observed once. The row identifier, the location, the reader's own
words, the assistance given and the reason are recorded together.

A content correction opens when two or more readers record the same stop with
the same first location, because that points at an instruction or a
navigation path rather than at one reader.

A content correction opens when every reader in the batch recorded level 1 on
the same row, because the task then asks for something the page does not
support.

A content request opens when a single reader names a missing resource link or
a missing explanation. Such a request is a content need and not a defect in
an existing page.

A cosmetic preference is recorded and opens nothing.

Every correction names the affected page, the row identifier, the observed
difficulty, the assistance given and the reason. A correction that would
change a claim, a number, a protocol, a split, a metric or a frozen result
needs the ordinary content decision and is not made by this rule. Completed
experiments and frozen results stay unchanged, and a request for a new
scientific lab needs a separate source, data, split, baseline and evaluation
decision.

## What may be published

Reader outcomes stay `not observed` until a human session is actually
recorded. The prepared instruments do not fill a single field of a sheet.

Until a batch exists, the project may state that the trial is prepared and
that no reader outcome has been collected. It may not state a completion rate,
a navigation rate, an interpretation rate, a reader count or a session
count, because no denominator has been filled.

After a batch, the report states the numerator and the denominator of every
rate, the number of readers, their backgrounds and languages, the candidate
edition, the dates, and the excluded rows with their reasons. The report does
not claim learning gains, a comparison of the two language editions, adoption
or the quality of a lesson. A small formative batch cannot establish any of
them, and a software acceptance result is not reader evidence either.

Preparing these instruments does not authorise reader invitations, a
deployed site, a published report or a public claim about the trial.
