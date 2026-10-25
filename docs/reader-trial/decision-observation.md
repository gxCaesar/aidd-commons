# Researcher decision session observation sheet

Facilitator copy, not for distribution to participants. Duplicate this sheet
once per actual reader and once per session. Leave every field blank until the
outcome is witnessed in front of you. Keep completed copies outside the public
source package. Do not collect names, email addresses, employer details,
credentials, private datasets or screenshots that contain personal
information.

Automated tests and agent self-review are not reader evidence. A passing test
suite, a software acceptance run or an agent's own review of the material does
not fill any field on this sheet. Every outcome stays `not observed` until a
human session is actually recorded.

The task text the reader receives is in the organiser's guide. This sheet
records what happened, not whether the reader was right. The
[rubric](rubric.md) turns a recorded sheet into a completion level, and the
[analysis plan](analysis-plan.md) turns the batch into a report. The
[session log](session-log.md) and the [batch roll-up](batch-rollup.csv) carry
the same session identifier and the same reader label, and the shared outcome
vocabulary is the one they declare.

## Session header

| Field | Entry |
| --- | --- |
| Session identifier | |
| Reader label | |
| Session type | `researcher decision` or `modelling transfer` |
| Date of session | |
| Candidate edition and date | |
| Language of the session | |
| Device, browser and prior experience | |
| Site address or source copy | |
| Optional execution task | `offered` or `not offered` |
| Facilitator | |

### Session type

One of `browser orientation`, `engineering task`, `notebook session`,
`paperqa source inspection`, `modelling transfer` or `researcher decision`.
On this sheet the type is `researcher decision` for the decision memo and
`modelling transfer` for the record-then-median arithmetic, the classifier
threshold item and the sandbox execution item. The session type and the
session identifier together keep a sheet for one kind of session from being
mistaken for a sheet for another.

### Reader label convention

A reader label identifies a person, not a session. Number the readers `R-01`,
`R-02`, `R-03` and so on in the order the organiser schedules them inside one
batch. The number belongs to that reader for the whole batch and never
changes. A reader who skips a session keeps the label. A reader who returns
later keeps the label. A reader added in the middle of a batch takes the next
unused number, and a retired number is never reused. The same reader's core
session, notebook session and PaperQA session therefore carry the same label
and join without manual matching. The session log and the batch roll-up carry
the same label, and a batch that already uses another anonymous label form
uses it here as well, with one label per person.

### Session identifier convention

A session identifier is `S-YYYY-MM-DD-NN`, for example `S-2026-10-21-01`. The
number is unique across the batch for that date, so two sessions on one day
never share an identifier. The identifier is the same one that the session log
and the batch roll-up carry, and it holds no name.

## Session type and row assignment

The decision memo belongs to the researcher decision activity. The
record-then-median arithmetic, the classifier threshold item and the sandbox
execution belong to the modelling-transfer activity. Use one sheet per
activity and per reader, and use a second sheet with a second session
identifier when one reader completes both activities. A row that does not
belong to the session type stays `not assigned`.

| Row | `researcher decision` | `modelling transfer` |
| --- | --- | --- |
| `DEC-01` Decision memo | assigned | not assigned |
| `DEC-02` Record-then-median arithmetic | not assigned | assigned |
| `DEC-03` Classifier threshold item | not assigned | assigned |
| `DEC-04` Sandbox execution item | not assigned | assigned when the optional execution task is offered |

## Field vocabulary

Use these codes in every field of every sheet. A blank cell means the field
was not measured. A code is never written from expectation, from a test
result or from what the reader is likely to say next.

### Task status

| Code | Meaning |
| --- | --- |
| `attempted` | The reader worked on the row and produced an answer, an artefact or a stated refusal. |
| `stopped` | The reader began the row and halted, including a failed install and an expired timebox. |
| `skipped by the reader` | The reader was offered the row and chose not to attempt it. |
| `not assigned` | The facilitator did not offer the row in this session. |
| `not observed` | The row was offered but no outcome was witnessed. |

### Navigation outcome

| Code | Meaning |
| --- | --- |
| `reached unassisted` | The reader found the page or the artefact without help. |
| `reached after help` | The reader found it after a recorded help event. |
| `not reached` | The reader did not find it. |
| `not observed` | No navigation was witnessed. |

### Interpretation outcome

| Code | Meaning |
| --- | --- |
| `correct without help` | The reader's answer matches the organiser's answer notes and no help was given. |
| `correct with help` | The reader's answer matches the organiser's answer notes after a recorded help event. |
| `incorrect` | The reader gave an answer that does not match the organiser's answer notes. |
| `no answer offered` | The reader gave no answer to the question the row asks. |
| `not observed` | No answer was witnessed. |

Code the interpretation outcome after the attempt, against the answer notes.
The help type, the navigation outcome and the task status are written during
the session.

### Help type

| Code | Meaning |
| --- | --- |
| `none` | No help was given. |
| `pointer to a page` | The facilitator named a page, a section or an address to look at. |
| `conceptual explanation` | The facilitator explained the underlying idea. |
| `the answer` | The facilitator gave the answer or part of it. |
| `not observed` | No help event was witnessed. |

Record assistance instead of coaching the reader toward the expected answer.
A pointer and a handed-over answer are different events and are recorded
differently.

### Execution mode

| Code | Meaning |
| --- | --- |
| `browser only` | The row was worked by reading in a browser, with no notebook, runtime or command executed for it. |
| `notebook executed locally` | A notebook was executed on the reader's own machine for this row. |
| `notebook executed in a hosted runtime` | A notebook was executed in a hosted runtime for this row. |
| `local command executed` | A documented command was run on the reader's own machine for this row. |
| `not attempted, no account` | Execution was not attempted because the participant had no account. |
| `not attempted, install failed` | Execution was not attempted because an install failed. |
| `not attempted, other stated reason` | Execution was not attempted for another reason the participant stated. |
| `not applicable to this row` | The row has no executable component in this session. |

The mode is the reason a reader's outcome looks the way it does. A browser-only
reader and a reader whose install failed can both end an execution row without
a result, and only the mode tells the two apart.

### Elapsed time

Record three separate numbers for every row. Active work is the time the
reader spent on the task. Installation is the time spent preparing the
environment. Waiting is the time the reader spent idle, for example in a
runtime queue, on a download or with the facilitator. Leave a cell blank when
the component was not measured and never estimate a time from memory. The
setup timebox of 15 minutes is a session rule, and the three numbers are the
evidence that it was applied.

## Instrument rows

### DEC-01: Decision memo

Activity. Researcher decision. Task. A constructed follow-up reports a
relative reporter signal of 63 and a viable-cell count of 70, each normalized
to a vehicle value of 100. Under the lesson's linear model, write the
relative per-cell signal. A second detection method then shows no change, and
its ability to detect the proposed biological effect has not been established.
Say whether this settles interference versus biology, name the next useful
check and the result that would change your interpretation, and say why the
real ChEMBL aggregate metrics alone cannot identify the cause of transfer
failure. Mark each statement as observed or hypothetical. Do not fit a new
model and do not rerun an evaluation.

| Field | Entry |
| --- | --- |
| Task status | |
| Navigation outcome | |
| Interpretation outcome | |
| Help type | |
| Execution mode | |
| Active work minutes | |
| Installation minutes | |
| Waiting minutes | |
| First difficulty and location | |
| Reader's initial note | |
| Reader's revised note after help | |
| Rubric level reached | |

Completion criterion. Rubric row `DEC-01`, level 2 or level 3. The memo
states a relative per-cell signal as a number, takes a stated position on
whether the follow-up result settles interference versus biology, names a
concrete next check, names the result that would change the interpretation,
says why the ChEMBL aggregate metrics alone cannot identify the cause of
transfer failure, and marks each statement as observed or hypothetical.

### DEC-02: Record-then-median arithmetic

Activity. Modelling transfer. Task. A new export gives parent P exact IC50
values of 20 nM and 200 nM, and parent Q an IC50 greater than 2 µM. Apply the
lesson's log-then-median rule and say which record does not enter an
exact-value regression.

| Field | Entry |
| --- | --- |
| Task status | |
| Navigation outcome | |
| Interpretation outcome | |
| Help type | |
| Execution mode | |
| Active work minutes | |
| Installation minutes | |
| Waiting minutes | |
| First difficulty and location | |
| Reader's initial note | |
| Reader's revised note after help | |
| Rubric level reached | |

Completion criterion. Rubric row `DEC-02`, level 2 or level 3. The reader's
note states a median target for parent P as a number, names the rule as a
logarithm first and a median second, states that parent Q does not enter the
exact-value regression, and states that the bound on parent Q is preserved
rather than discarded.

### DEC-03: Classifier threshold item

Activity. Modelling transfer. Task. A trained classifier gives probabilities
of 0.9, 0.6 and 0.4 for recorded classes of 0, 1 and 1. Say which mistakes
occur at a threshold of 0.5, and say whether the test records can be used to
pick a new threshold while keeping an untouched-test claim.

| Field | Entry |
| --- | --- |
| Task status | |
| Navigation outcome | |
| Interpretation outcome | |
| Help type | |
| Execution mode | |
| Active work minutes | |
| Installation minutes | |
| Waiting minutes | |
| First difficulty and location | |
| Reader's initial note | |
| Reader's revised note after help | |
| Rubric level reached | |

Completion criterion. Rubric row `DEC-03`, level 2 or level 3. The reader's
note states the threshold used, lists each mistake type that occurs at that
threshold including a statement about the true negatives, states which mistake
is most costly under a loss the reader names, and answers whether the test
records can be used to choose a new threshold while keeping an untouched-test
claim.

### DEC-04: Sandbox execution item

Activity. Modelling transfer, optional. Task. In a reader copy, run only the
synthetic student sandbox, locate its output, and explain why a test MAE of
4.5 is worse than the constant baseline's 3.5 despite a zero validation MAE.
Do not run a frozen assay evaluation.

| Field | Entry |
| --- | --- |
| Task status | |
| Navigation outcome | |
| Interpretation outcome | |
| Help type | |
| Execution mode | |
| Active work minutes | |
| Installation minutes | |
| Waiting minutes | |
| First difficulty and location | |
| Reader's initial note | |
| Reader's revised note after help | |
| Rubric level reached | |

Completion criterion. Rubric row `DEC-04`, level 2 or level 3. The reader
produced the sandbox output in their own copy, located it by the path the run
printed, quoted the fitted model's test MAE and the constant baseline's test
MAE, and stated a mechanism that connects a zero validation MAE to the worse
test error.

## Session close

| Field | Entry |
| --- | --- |
| Reader agreed to share a redacted correction | |
| Proposed correction, page or cell, and reason | |
| Sheets copied out of the session workspace | |

Do not combine navigation, installation, scientific answers and satisfaction
into a single score. This sheet is a formative check of instructions,
navigation and interpretation, and a completed session establishes nothing
about learning gains, adoption or a comparison of the two language editions.
