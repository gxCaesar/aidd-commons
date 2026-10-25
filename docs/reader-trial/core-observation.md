# Core session observation sheet

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
| Session type | `browser orientation` or `engineering task` |
| Date of session | |
| Candidate edition and date | |
| Language of the session | |
| Device, browser and prior experience | |
| Site address or source copy | |
| Optional engineering task | `offered` or `not offered` |
| Facilitator | |

### Session type

One of `browser orientation`, `engineering task`, `notebook session`,
`paperqa source inspection`, `modelling transfer` or `researcher decision`.
On this sheet the type is `browser orientation` when the optional engineering
task was not offered, and `engineering task` when it was offered in the same
sitting. The session type and the session identifier together keep a sheet
for one kind of session from being mistaken for a sheet for another.

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

The first four rows are the orientation tasks. The last two belong to the
optional engineering task and stay `not assigned` when that task is not
offered. A row that was not offered carries no evidence about the reader.

### CORE-01: Route and resource list

Task. Choose Foundations, Research or Engineering and say why it fits your
background. Find the representation lesson and its resource list, open an
Atlas entry and the original resource it points to, and say whether a visible
link establishes permission to use every associated asset.

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

Completion criterion. Rubric row `CORE-01`, level 2 or level 3. The reader's
note names a route and a reason tied to their own background, locates the
representation lesson and its resource list, locates an Atlas entry and the
original resource behind it, names at least one access or licence field with
the value the page shows, and answers whether a visible link covers every
associated asset.

### CORE-02: Label-free representation example

Task. Find the inspector's pyridine, alanine and sodium-acetate examples. Say
whether different strings must mean different molecules, which output loses
the alanine stereochemical distinction, and whether the salt becomes one
neutral molecule. Name the output fields you used.

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

Completion criterion. Rubric row `CORE-02`, level 2 or level 3. The reader's
note locates the two pyridine records, the two alanine enantiomers and the
salt record, names at least two output fields as the basis of the comparison,
gives a stated answer with a reason for each of the three questions, and adds
one limitation of identity agreement.

### CORE-03: Completed ChEMBL comparison

Task. Open the completed ChEMBL lab. Compare Morgan Ridge with descriptor
Ridge on both evaluation sets, say whether the same representation wins in
both, and say what the earlier T15 label access prevents the authors from
claiming. Do not run another evaluation.

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

Completion criterion. Rubric row `CORE-03`, level 2 or level 3. The reader's
note names both models, states a comparison outcome for each of the two
evaluation sets, states whether the ranking is the same in both sets, and
names the earlier shared-label exposure as the reason a stronger claim is not
available. The reader worked from the delivered table and did not run a new
evaluation.

### CORE-04: Next lesson and missing explanation

Task. Return to the pathway map and choose a topic you would study next. Name
one concrete explanation, example or prerequisite you could not find, and say
whether the gap is a missing resource link or a resource that exists and does
not teach the needed concept.

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

Completion criterion. Rubric row `CORE-04`, level 2 or level 3. The reader's
note names a next topic taken from the pathway map, names one specific
missing explanation, example or prerequisite rather than a general
dissatisfaction statement, says where they looked for it, and places the gap
as either a missing resource link or a resource that exists and does not teach
the needed concept.

### CORE-05: Optional local setup

Task. In a fresh local source copy, prepare the environment for the
label-free inspector under the first-session instructions. Stop after 15
minutes and keep the first useful error if setup fails.

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

Completion criterion. Rubric row `CORE-05`, level 2 or level 3. The reader
brought up a working local environment and showed a command that starts, and
the recorded installation minutes show the timebox was applied. A preserved
first useful error is recorded, and the row stays at level 1 when the setup
did not come up.

### CORE-06: Optional inspector execution

Task. Run only the label-free inspector, find its output and compare it with
the documented relationships. Do not download the ChEMBL or rMD17 data, run a
pretest, change a protocol or invoke a locked evaluation.

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

Completion criterion. Rubric row `CORE-06`, level 2 or level 3. The reader
produced the inspector's report in their own copy, located it by the path the
command printed, quoted at least one relationship from the local output, and
compared that relationship with the documented one for the same example.

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
