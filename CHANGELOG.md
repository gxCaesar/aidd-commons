# Changes

## Unreleased

No changes yet.

## 0.2.0 — 25 October 2026

- Publish the bilingual learning system with 18 tracks, 120 declared teaching
  units, 111 Learn pages per language and 56 lab guides per language.
- Expand the Atlas to 228 source-backed records. The latest benchmark lesson
  distinguishes available code from dataset access, published comparisons from
  matched local evaluation, and descriptive score differences from causal evidence.
- Retain all frozen lab results, including adverse comparisons and execution
  limitations. No frozen experiment was rerun for this release.
- Provide a curated source export and GitHub Pages deployment. Record the public
  correction window separately from the two coverage claims, which remain
  `not_established`. Human reader outcomes and actual Colab execution remain
  unobserved.

### Development snapshot — 22 October 2026

The following records that round's measurements; later rounds are documented
in the roadmap and living report.

- Four curriculum tracks that held prose only gained a real-data, CPU-first,
  single-command laboratory each, with a frozen protocol, a committed summary
  and a known-bad rejection test.
- Six frontier method families gained a dated reading lesson with a Chinese
  mirror, and 62 Atlas records were written from opened primary pages.
- Four independent blind readings ran; three raised their topic, and the
  fourth refused. Executable coverage rose from 53 to 56 topics, executable on
  real data from 40 to 43, assessed from 24 to 27, and tracks with executable
  or assessed coverage from 14 to 17 of 18. Both coverage claims remain
  `not_established`, because the sixth gate criterion needs a public
  correction window and publication has not happened.
- The published blind-review record had three defects of its own, now
  corrected: a command count counted twice, two batches both labelled the
  sixth, and three topics' readings carried no isolation attestation.
- The site gained its first figures. Twenty vector figures are drawn by script
  from the repository's own results, eight stand on four pages in both
  languages, and they follow the manual theme switch.
- The dark mode was broken, measured at 1.06:1 contrast for a heading, and
  is now driven by one signal across both page shells.
- Six release-surface defects were closed, including a CI release job that
  omitted three of the five generated data files the site imports, and a
  reader-trial answer sheet that was being published with the release.

## 0.2.0-rc.1 — release candidate

Prepared 8 September 2026. This candidate has not been published as a final
release. No public release date or external adoption is claimed.

- Surveyed the last two thin providers, completing a pass over all twelve
  comparators. Direct observations rise from 577 to 591 of 1209 cells.

- Corrected a second conclusion drawn from a partial read. The O3DC benchmark
  index renders with JavaScript and a static fetch reports zero entries; the data
  file behind it holds 152 benchmarks across ten categories, every one carrying a
  required caveat note and 90 carrying a live-checked repository. Source review
  scope and counterevidence rise to worked and baseline protocols to explained,
  scored from the notes rather than the description.

- That correction cost this project a claim condition. Raising those cells took
  O3DC's upper bound at worked from 88 to 91, which equals this project's own
  lower bound, so the most-detailed claim no longer satisfies its bound condition.
  It passed before the survey and does not pass after it. The comprehensiveness
  claim still satisfies its own, at 93 against 92.

- Recorded the ML4Drug textbook's public surface as a proposal and capped every
  cell at mentioned. Its repository contains a five-kilobyte landing page, a theme
  and an unrelated workshop schedule, and no chapter exists anywhere. No absence
  was recorded against it, because a table of contents that omits a topic is not
  evidence that an unwritten book would omit it.

- Surveyed the AI-Guided Inquiry curriculum, opening three of its twenty
  talktorial notebooks in full. Docking and scoring protocols rises from mentioned
  to executable because the notebook shows a protocol being executed rather than
  described, and protein sequence and structure representation and binding-mode
  and pose hypotheses are recorded as executable for the first time. Both of those
  are rows this project is blocked on, so the survey raised a competitor exactly
  where we cannot reach. Four further cells are mentioned from the overview
  listing, each naming the surface it rests on. Direct observations rise from 571
  to 577.

- Added a bilingual docking protocol lab. It separates the five components that
  move a reported score from the two that move what it means, then computes which
  protocols may be compared. Two protocols differing in exactly one component
  report -8.2 and -10.7 for the same ligand on the same structure, no pair in the
  set is comparable, and a protocol declaring neither validation nor decoys still
  produces a full column of numbers. No docking program is run. Eleven checks,
  thirteen tests, six known-bad edits.

- Added a bilingual design space lab. Three constructions are enumerated exactly
  with every nominal size recomputed from its input lists. Growing a space from 25
  to 100 reached one further target and left two exactly as unreachable, one of
  which differs from a reachable molecule by a single ring atom; a third space of
  equal size reaches that target and shares no member with either enumeration
  space; and a fourth target is reachable in none of the three. Thirteen checks,
  fourteen tests, seven known-bad edits.

- Docking and scoring protocols and candidate design spaces both rise from worked
  to executable, taking runnable coverage to 44 topics with eight queue rows left.
  Those eight are exactly the set the 2026-09-11 triage marked as not reachable
  offline: four would need authored data and four are blocked by structures this
  repository does not hold. Every row judged reachable has now been built.

- Added a bilingual safety evidence lab separating molecular alerts, assay
  outcomes, organ liabilities, dose context and organism-level evidence. The
  record stores only findings that required an experiment and never stores an
  alert, which is computed from the structure instead. Seven of twelve compounds
  alert and five of those were never measured at all; an alert contradicted by a
  measurement is kept apart from an alert nobody checked; two compounds carry
  positive findings with no alert at all; two of seven assay outcomes carry no
  concentration and no exposure is declared anywhere; and one of twelve compounds
  carries organism-level evidence. Fourteen checks, sixteen tests, seven known-bad
  edits. Safety and toxicity endpoints rise from worked to executable, taking
  runnable coverage to 42 topics with ten queue rows left.

- Replaced a check that could not fail. The assertion that no compound stores an
  alert contained an `all()` over an empty sequence with an `or True` inside it,
  so it reduced to a single weak string test. It now inspects compound keys and
  finding systems directly, and the known-bad edit that writes an alert into a
  compound record fires it.

- Added a bilingual binder definition lab. It stores measurements and declared
  rules but no class label, then moves each definition while the molecules stay
  fixed: the positive count more than doubles across a cutoff grid, four of twelve
  compounds sit within the declared assay uncertainty of the cutoff on both sides,
  adding decoys moves prevalence from 0.500 to 0.250 with two thirds of the
  enlarged negative class never measured, and six positives occupy three scaffolds
  with one compound having no scaffold at all. Sixteen checks, thirteen tests, six
  known-bad edits, two of which exposed weak checks that were then strengthened.
  Binder classification rises from worked to executable, taking runnable coverage
  to 41 topics with eleven queue rows left.

- Added a bilingual SAR attribution lab. Its dataset stores a generating rule
  rather than labels, so the cause of activity is known and an explanation can be
  compared against it, which real activity data never permits. A confounder
  perfectly correlated with the cause takes the larger share of atom credit on
  seven of eight actives despite causing nothing, and the matched pair that breaks
  the correlation is ranked backwards, with the genuinely active molecule called
  inactive at a threshold declared before fitting. The lab separates the
  hypothesis an explanation licenses from the causal atom claim it does not.
  Fourteen checks, thirteen tests, five known-bad edits. Interpretability and
  structure-activity relationships rises from worked to executable, taking
  runnable coverage to 40 topics with twelve queue rows left.

- Recorded the reproducibility boundary for that lab rather than hiding it. The
  exact predictions depend on the fingerprint implementation, observed with RDKit
  2025.09.6 and NumPy 2.4.6, so the checks assert the qualitative relationships
  instead of the printed decimals.

- Added a bilingual disconnection comparison lab. Rule, retrieval and template
  families run over ten authored routes; the learned family is declared without
  being run and states why. All three runnable families recover 5 of 5 inside the
  precedent set and separate outside it, at 5, 3 and 0 of 5, for three different
  causes rather than by score. A retrieval score is shown to be decided by the
  split, at 100% on its own table against 50% overall, and recovery is separated
  from selection where more than one disconnection is proposed. Laboratory
  feasibility stays unassessed throughout. Thirteen checks, fourteen tests, seven
  known-bad edits. Retrosynthetic disconnections rise from worked to executable,
  taking runnable coverage to 39 topics with thirteen queue rows left.

- Re-triaged all fifteen remaining executable-queue rows against their taxonomy
  definitions. Seven are reachable offline, four only from authored data, and four
  need structures this repository does not hold. Two of those verdicts reverse an
  earlier note: binder classification and screening-selection transport were
  written off as blocked by compound-level label availability, and neither is
  data-hungry once the definition is read.

- Added a bilingual screening transport lab closing the first of the seven. It
  reads the completed two-assay pool-budget replay and converts every score into
  recovered targets, the only unit that makes the contexts comparable. The two
  assays measure in steps 4.92 times apart; the whole five-instance baseline
  spread is 1.62 and 1.25 recovered targets, so it cannot carry an error bar; and
  the policy that recovered nothing at all lost by 0.12 of a single target while
  the other context lost by more than thirteen times that. Disjoint chemistry is
  separated from a shared protocol as what makes a repeat informative and what
  limits it. Off-targets and prospective follow-up are stated as outside what the
  evidence reaches. Eleven checks, twelve tests, five known-bad edits. Screening
  selection and repurposing transfer rises from worked to executable, taking
  runnable coverage to 38 topics with fourteen queue rows left.

- Corrected a wrong absence conclusion about the AIDD doctoral network. The
  previous round recorded that no course material is published on any of its
  public surfaces. Reading the Lectures page in full found published agendas for
  all six AIDD schools and 109 downloadable lecture slide decks and workshop
  materials; the earlier conclusion came from reading only the first screen of a
  long page, the same truncated-read failure that once produced a wrong absence
  for a competitor's chapter. Both caveats are corrected in the record and the
  eligibility question they raised is withdrawn.

- Recorded eighteen mentioned cells for that provider from named school lectures
  with downloadable decks, covering representations, uncertainty and calibration,
  interpretability, toxicity, chemical space, multi-objective search, synthesis
  planning, split and leakage audits, out-of-distribution evaluation, reproduction
  reporting, active learning, human-in-the-loop review and research ethics. No
  deck was opened: the files sit behind a bot challenge that refused retrieval, so
  each note states the depth is limited by this review's reach rather than by the
  material, and a reviewer with access should expect to raise these scores.

- Both bound conditions now pass, at 93 against 90 for comprehensiveness and 91
  against 90 for detail, and the twelve-track condition passes at 12 of 18.
  Criterion 6 is still unmet, so both claims remain not established. The claim
  status field is a hardcoded literal in the exporter rather than a computed
  value, so it cannot change because the numbers moved.

- Surveyed the three providers still blocking the most-detailed bound condition.
  OpenMM gained one executable positive on convergence and protocol uncertainty
  plus 75 absences across tracks a simulation collection does not touch.
  Therapeutics Data Commons gained eleven cells, five executable and six
  mentioned, with no absences recorded because a hub spanning target discovery to
  manufacturing is not a place absence can be asserted from overview pages.
  Direct observations rise from 466 to 553.

- Declined to finish the third survey. The AIDD doctoral network publishes no
  course, module, lesson or notebook page anywhere in its public navigation, and
  recording absences there would have cleared the most-detailed bound condition
  immediately, since it is now the only provider still blocking it. The evidence
  is the weakest of the seven surveys, because the material plausibly exists and
  is simply not public. Two caveats were recorded instead, including an open
  eligibility question about whether a record publishing no learning material
  belongs in a comparison set of learning resources.

- Corrected how the audit measures its own movability. An upper bound falls not
  only through recorded absence but through any cell reviewed and found below the
  threshold, because a shallow direct observation contributes zero to the upper
  bound where an unverified cell contributes one. The counterfactual line now
  counts both mechanisms: comparator ceilings were lowered by 335 reviewed cells
  across 12 providers, and without that review the strongest external upper bound
  would be 93, which is this project's own lower bound.

- Surveyed four thin providers against their complete declared surfaces, taking
  direct observations from 328 to 466. RDKit Cookbook gained three positives and
  45 absences from a full page read; ChEMBL Quick Tour gained 70 absences after
  all seven course pages were read, with representations and mechanism-targets
  deliberately left unverified rather than absent; DeepChem and Practical
  Cheminformatics gained track-level absences recorded at index scope, which each
  note states. The strongest external upper bound at 'explained' falls from 93 to
  92, so the bound condition for the comprehensiveness claim now passes.

- Published the counterfactual beside that result, because a comparator's upper
  bound falls only when this project records an absence against it. The coverage
  bounds table gains a recorded-absent column, and the audit headline now states
  that comparator upper bounds rest on 218 absent cells recorded by this project
  and that without them the strongest external upper bound would be 93 — exactly
  this project's own lower bound. A test locks that sentence.

- The comprehensiveness claim remains not established. Criterion 6 is unmet: no
  public correction window has been recorded, and it cannot be satisfied from
  inside the repository. The most-detailed claim now meets its twelve-track
  condition at exactly 12 of 18 but not its bound condition, where three
  comparators still carry upper bounds equal to this project's lower bound of 91.

- Added a bilingual property decision lab turning the completed FreeSolv
  intervals into a threshold decision with an explicit abstention outcome. A
  frozen three-way rule makes the abstention band two conformal radii wide, and
  the committed numbers show that only one of four split and model combinations
  reaches the nominal 0.9 coverage it was built for, that it is the one with the
  widest band, that the narrowest band carries the largest shortfall, and that
  abstention rises monotonically as the band widens so the covering combination
  decides least. Both selection criteria are declared before the numbers are
  read, and they disagree in the same direction on both splits. Twenty checks,
  eighteen tests, eight of them known-bad edits. Property predictions in
  decisions rises from worked to executable, taking runnable coverage to 37
  topics with thirteen queue rows left.

- Recorded a second admitted evidence gap in the same style as the first: the
  number of real compounds inside the abstention band cannot be computed here,
  because the completed FreeSolv lab retained aggregate metrics and split
  membership rather than per-compound test predictions. The grid counts are
  arithmetic over a declared range and are not a yield.

- Advanced the frozen validator date to 2026-09-11 across four tests after the
  session crossed midnight and new evidence postdated the comparison record.

- Added a bilingual generation gate lab closing both molecular-generation queue
  rows. A frozen objective declares target context, four bounded properties, four
  SMARTS-backed prohibited motifs, structural synthesis limits and an experimental
  decision with an abstention rule; the inspector treats applicability as a
  precondition and refuses to screen against an objective that fails it. Six gates
  then run over twenty constructed candidates with chained denominators, where the
  headline 18 of 20 valid becomes 6 of 20 surviving. Memorization is shown to be
  the novelty gate against a narrower reference set rather than a seventh check,
  and route feasibility stays recorded as not assessed. Seventeen checks, twenty
  tests, eleven of them known-bad edits. Design objectives and the validity funnel
  both rise from worked to executable, taking runnable coverage to 36 topics with
  fourteen queue rows left.

- Noted a deliberate departure in the generation gate lab: it requires RDKit,
  unlike the other offline inspectors here, because its gates are computed from
  structures rather than read from a record. No generative model is run, and the
  candidates are authored by hand rather than sampled.

- Re-triaged the executable queue against taxonomy definitions rather than topic
  names, after the previous round showed a row had been deferred on its title.
  At least five of the seventeen are reachable offline; the earlier note that
  most needed structure, docking or generation artifacts behind resource gates
  was wrong. Two others are blocked by a stated data limit instead: binder
  classification and screening selection need compound-level labels, and only
  aggregates are committed.

- Added a bilingual counterevidence dossier lab. It reads the eight completed lab
  artifacts and separates six classes a "limitations" paragraph collapses: not-run
  evaluations, methods that lost to their own baseline, refused metrics, scope
  limits, admitted record gaps and retained measurement spread. It recomputes the
  transfer failure in which the model with the lowest primary-test error carries
  3.49 times the baseline error on assay replication with a negative rank
  correlation, and it requires the shared-label exposure to be disclosed by both
  the exposed and the exposing lab. Thirteen checks, fifteen tests, eight of them
  known-bad edits that delete or soften a disclosure. Counterevidence and failure
  analysis rises from worked to executable, taking runnable coverage to 34 topics
  and level with the strongest external provider, with sixteen queue rows left.

- Closed the last confirmed depth gap by building it. A bilingual claim
  separation lab groups the twenty registered systems that make a structural or
  affinity claim into monomer prediction, co-folded complex, generated pose, pose
  check and affinity estimate, then prints where two of them merge: a modality
  label spanning three claim classes, one model declaring both a pose and an
  affinity, and no measurement record anywhere in the family. Ten checks and
  fourteen tests, six of them known-bad edits. Its load-bearing finding is that
  no system in the family evidences the evaluation code behind its accuracy
  claim, twenty of twenty. Complex and co-folding hypotheses rise from explained
  to executable, confirmed depth gaps fall from one to zero, and the executable
  queue falls to seventeen rows. The comprehensiveness claim remains not
  established.

- Fixed a lab that would not have run from a clean checkout. The claim inspector
  first read the published resource registry, which is a build artifact under an
  ignored path, while its page claimed to read committed files. A generated
  extract now travels with the lab, selected by declared task so no system can be
  hand-picked in or out, and the exporter refuses to overwrite a differing
  extract unless asked.

- Named the PaperQA live-inference runtime budget in both notebook editions.
  `EXECUTION_PROFILE` selects the observed batch's limits or the accepted CPU
  execution copy's four threads, zero retries and 600/2400-second limits, and a
  check refuses any profile that would move a model, retrieval or answer setting.
  A test asserts the published CPU profile equals that copy's settings. The
  default lesson and every scientific setting are unchanged, and no unattended
  CPU run of the published notebook has been accepted.

- Opened three further providers through the repository API. Practical
  Cheminformatics rises to executable on co-folding evaluation and on Free-Wilson
  SAR interpretation and gains interaction-fingerprint and pose-preservation
  cells; DeepChem adds an executable single-cell representation workflow and a
  worked antibody-drug conjugate construct; Therapeutics Data Commons rises to
  executable on parameterised splits at README level. The executable queue reached
  eighteen rows, and the single confirmed depth gap now has two external providers
  at executable against this project's explained.

- Corrected an absent state that had been asserted from a truncated retrieval.
  Chapter 9 was fetched in full through the repository API and parsed locally,
  showing a configuration-grid policy comparison with learning curves, MaxMin
  diversity initialisation and Monte Carlo dropout uncertainty over four
  acquisition functions. Three cells were raised. All three measured records are
  now complete with no ranges, and on runnable coverage this project is level
  with one provider and behind the other by two topics.

- Read Build AI Chapter 9 and resolved five of the six held cells, recording a
  rule-defined docking box as executable, a single repaired structure as mentioned
  for structural alternatives, a declared objective without constraints as worked,
  and no stopping rule or policy comparison as absent. The sixth stays unverified
  because two retrieval attempts stopped before the active-learning section, which
  is a limit of this review's reach rather than an observed absence. Runnable
  coverage is now exactly level with one provider and undecided against the other
  by one unread code cell.

- Completed the Build AI Drug Discovery Pipelines record. All thirteen chapters
  were read, taking it to eighty-seven direct cells with forty-one absent and six
  deliberately left unverified on Chapter 9, which this pass did not read. Its
  executable range of 31-37 straddles this project's 32, so that comparison is not
  robust and one unread chapter decides it. Its assessed floor is zero across all
  93 topics, because the open repository carries code without the book's
  explanations or exercises. The executable queue grew to seventeen rows.

- Read five further chapters of Build AI Drug Discovery Pipelines, taking that
  record to nine of thirteen chapters and twenty-three direct cells. The
  executable queue grew from twelve rows to fifteen, because that provider is
  runnable on candidate design spaces, novelty screening and retained failure
  analysis where this project is not. Its assessed lower bound stays at zero
  because the open repository carries no exercises, and its Chapter 12 was not
  credited for structure despite its title.

- Closed three queue rows by crediting artifacts the record already had, and
  resolved the last unknown external cell through a smaller surface for T020.
  Both records are now complete with no unknown cells, and against this one
  provider the comparison reads 93 against 46 on explanation, 90 against 40 on
  worked cases, and exactly level at 32 and 23 on runnable and tested coverage.
  Twelve queue rows remain, now driven by other providers, and eleven providers
  are still largely unread, so the comprehensiveness claim is unchanged.

- Completed the TeachOpenCADD record. All fifty unscored topics were resolved
  from the talktorials already read: ten carried positive evidence not previously
  encoded, and forty are recorded as absent with the reviewed surfaces and date
  declared. Both providers now have zero unknown cells. Under one standard this
  project is robustly ahead on explanation at 93 against 46-47 and on worked
  cases at 90 against 40-41, and robustly behind on executable at 29 against
  32-33 and assessed at 21 against 23-24. Reading their cells raised their
  runnable floors, so the earlier apparent convergence was an artifact.

- Added an optimiser sweep to the student modelling sandbox. After selection it
  varies only the step budget and starting point, deterministically, and reports
  compute as gradient evaluations against decision agreement and probability
  spread. The cheapest budget is the only one where three starting points
  disagree about the decision. Three new tests, and computational uncertainty
  rises to assessed by building rather than by rescoring. Executable coverage
  reached 29 and assessed 21, which are floors and not an overtaking.

- Added a second model family to the student modelling sandbox. A decision stump
  is fitted beside the linear arm on the same constructed records, selected under
  the same rule, and scored on the same held-out records, where ridge reaches MAE
  4.5, the constant 3.5 and the stump 0.5. The lesson traces the difference to
  extrapolation rather than capacity and states that two test entities cannot
  rank families. Six new tests, and inductive-bias selection rises to assessed by
  building rather than by rescoring. Executable coverage reached 28.

- Registered the student modelling sandbox in the comparison record, which had
  no evidence entry for it, and raised classification formulation to assessed on
  its logistic arm, declared threshold and train-prevalence baseline. Inductive-
  bias selection and computational uncertainty were examined and deliberately
  left at worked, because no runnable artifact here compares model families or
  reports optimisation variability. Executable coverage rose to 27 and the queue
  fell to 16 topics.

- Added an offline contract inspector and bilingual guide for the frozen
  pool-budget campaign, recomputing the derived budget, the partition
  inheritance and the reported recovery AUC from the raw checkpoint series, and
  teaching why five fixed seeds are not an error bar. Fifty-three checks and
  eleven tests, six of them known-bad edits. Executable coverage rose from 24 to
  26, assessed from 16 to 18, and the executable-gap queue fell to 17 topics.

- Added an offline contract inspector and bilingual guide for the frozen rMD17
  system-state lab, printing the energy observable with its prohibited feature
  arrays, the frame sampling with measured adjacent-index gaps, and every error
  beside the range it is measured over. Fourteen checks and ten tests, five of
  them known-bad edits. Executable coverage rose from 21 to 24, assessed from 14
  to 16, and the executable-gap queue fell from 21 topics to 19.

- Corrected thirteen comparison cells still scored from a track introduction
  written before the deep lessons existed, and taught provenance through the new
  contract checker. Worked coverage rose from 74 to 90 and confirmed depth gaps
  fell from three to one. That fall is a correction of an understated record,
  not new teaching material.

- Reported the deficit the gap table could not see. The confirmed-gap table only
  lists topics below `worked`, so it emptied while runnable coverage stayed at 21
  against an external lower bound of 30. The gap builder now takes a depth
  threshold, the audit carries a second table at `executable` listing all 21
  topics, and a test asserts the executable table stays larger than the worked
  one.

- Added an offline contract inspector for the frozen ChEMBL 37 EGFR lab and a
  bilingual guide that teaches from it. The command reads only committed files,
  prints the screening unit, endpoint definition and admission arithmetic with
  their exclusions, and recomputes nine relationships across the protocol,
  development summary, locked summary and amendment. Eight tests include four
  known-bad edits. This closed three of the six confirmed depth gaps and raised
  executable coverage from 17 to 20 and assessed from 10 to 13, without a new
  experiment, protocol change or result change.

- Completed the self-audit against the frozen taxonomy. All 93 topics now carry
  a direct AIDD Commons observation, up from 21, so this project is the only
  provider in the set with no unverified cell and exact rather than ranged
  bounds. Measured under one rule it is robustly ahead on explanation at 93,
  undecided on worked cases at 74, and robustly behind on executable at 17 and
  assessed at 10, since the strongest external lower bounds of 30 and 21 already
  exceed them. A written lesson with a worked case and an answered exercise is scored
  `worked`; `executable` and `assessed` require a runnable artifact in this
  repository, so those two bounds are a floor. Confirmed depth gaps rose to six,
  and the tracks with executable or assessed coverage rose from four to eight of
  twelve.

- Completed the first external provider survey in the comparison audit. Of
  TeachOpenCADD's 34 talktorials, 32 were read and 2 exceeded the retrieval
  limit, taking that record from 4 reviewed talktorials to 32 and the matrix
  from 88 to 120 direct observations of 1,209 cells. The measured result
  favours that provider on every depth threshold, produced the audit's first
  four confirmed depth gaps, and left 32 further topics unclassifiable because
  this project has not self-audited them. No AIDD Commons content, protocol or
  frozen selection changed.

- Added a bilingual numeric-fidelity check over all 76 translated page pairs.
  Decimals and three-digit-or-longer integers must appear in both editions, with
  a probability accepted against the other edition's percent form. The current
  pages already satisfy it; no page content was changed to make it pass.

- Connected PaperQA as the fourth bilingual Notebook practice exercise in the
  shared route and root entry. Added a separate offline reader task and blank
  observation fields for citation support and retrieval coverage. No reader
  outcomes or publication are claimed by this preparation.

- Completed a five-question local-document PaperQA integration and added standalone
  English/Chinese evidence-inspection notebooks. Default execution is offline;
  a CPU-only live-notebook attempt later timed out while embedding the first
  document and produced no new answer. A later four-thread CPU execution copy
  with longer timeouts completed one live question; the unchanged default CPU
  limits remain unvalidated. Its core fact is supported, but its added reliability
  claims are not fully supported. Preserved
  an extra-prose attribution error and the refusal's limited evidence coverage.
  This is a worked example, not a benchmark result or autonomous-agent reproduction.

- Made local models the default scientific-agent integration route in both
  languages, with optional free-tier hosting and paid advanced comparisons.
  Added a downloadable PaperQA profile and dependency-free checker that rejects
  cloud routes, missing model roles and fallback overrides. This is configuration
  preparation only; the later worked example above adds a separate observed run.

- Added a bilingual scientific-agent resource guide with original worked cases
  separating answer correctness from execution records. Registered PaperQA2,
  LAB-Bench and BixBench and clarified ChemCrow's public-tool boundary and source
  licence. Current totals are 128 Atlas records and 69 Learn pages per language.
  No upstream agent, benchmark or paid API was run.

- Added bilingual physical-modelling and generation resource guides with
  constructed worked cases and independent questions, bringing Learn to 68
  pages per language. Registered REINVENT 4 separately from archived 3.2 (125
  Atlas records), corrected version-specific course links, clarified GuacaMol's
  two task families and refreshed the OpenFF documentation entry. No upstream
  simulation, generation, training or new empirical evaluation was run.

- Corrected resource facts on 9 September: retired CLUE tools versus archived
  LINCS data, OpenADMET/PK-DB source licences, GTEx protected data, SAbDab2's
  explicit training release and generic download-versus-training-data scope.
  Added a bilingual six-collection tutorial chooser. See the
  [corrections and source limits](docs/RESOURCE_FACT_CHECK.md).

- Expanded the Atlas from 101 to 124 records on 9 September. Added three
  bilingual resource-selection guides and the current 120-unit resource map
  with JSON download, taking Learn to 66 pages per language. Atlas entries now
  link back to registered teaching use. Added five tutorial collections alongside
  OpenADMET Demos and recorded source-code licences for RDKit and DeepChem.
  Historical comparison scores and empirical results remain unchanged.

- Completed a content-first written pass on 9 September: 23 additional English/
  Chinese chapter pairs, bringing Learn to 62 pages per language and linking all
  120 declared curriculum units. Extended the core and five specialist routes.
  Added a five-case capstone workbook with worked answers and transfer questions.
  These are written lessons, not new empirical runs. Local software, notebook and
  browser acceptance passed; cloud execution and reader feedback remain unverified.
  Prior scientific results and audit scores are unchanged.

- Added catalog-derived browser coverage for bilingual written exercises and
  corrected two pre-expansion test assumptions. Fixed keyboard access to the
  scientific-agent lesson's scrollable code example in both languages.

- Added the dated comparison of 13 learning systems across 93 topics, with
  evidence links and separate lower and upper coverage bounds.
- Completed the selected representation, physical-system, and experiment-budget
  teaching labs. Their aggregate results, exercises, and worked answers are
  available alongside the unchanged development snapshots.
- Preserved the ChEMBL representation ranking reversal, poor MaxMin outcomes,
  shared-label exposure between T05 and T15, and the rMD17 prediction-record
  limitation. These examples do not establish method superiority.
- Added a first-session route from installation to a label-free example and
  interpretation of a completed predictive comparison.
- Added 120 source-grounded resource links, direct Atlas entries, complete
  registered lesson reading lists and 14 curated lab downloads. See the
  [resource-link review](docs/RESOURCE_LINK_REVIEW.md) for coverage and limits.
- Added Chinese translations of the current 39 Learn pages and five lab
  guides, with linked canonical originals, localized reading controls and
  shared lesson progress. Numerical panels and download contents are unchanged;
  the Atlas and report remain English. See [edition scope](docs/CHINESE_EDITION.md).
- Added a bilingual T17 cross-lab reading exercise covering scaffold grouping,
  train-only fitting, correlated frames and T05/T15 shared-label exposure.
  Four worked answers reuse completed evidence without new experimental runs.
- Added its bilingual metrics-and-uncertainty follow-up on 9 September 2026,
  separating error, rank association, prediction-interval coverage and recovery
  AUC through four further reading cases. No new statistical results are claimed.
- Added a bilingual T15 diversity-to-feedback bridge on 9 September 2026,
  distinguishing label-blind acquisition, checkpoint-wise refitting and
  model-guided selection through four cases. The real replay remains unchanged;
  no new acquisition policy or prospective study has been run.
- Added the [v0.2 report addendum](report/aidd-commons-v0.2-addendum.md).
  The v0.1 report, PDF, bibliography, and citation remain historical artifacts.
- Added the bilingual layered curriculum map, explicit core/five specialist
  routes and granular planned-unit mappings on 9 September 2026. Existing lesson
  URLs and browser-local progress remain compatible; historical audit scores stay
  unchanged.
- Added four foundational lessons linking records, fitting, regression/classification
  and an isolated standard-library student sandbox, plus four mechanism readings.
  The sandbox was actually run on invented data and preserves worse-than-constant
  outcomes. It is not a real-assay QSAR result or a new frozen experiment.
- Added the teaching standard, dated frontier-maintenance practice and optional
  transfer questions for a future reader trial. No schedule or publication was activated.
- Added three bilingual biological-evidence chapters on assay controls/dose
  response, genetic target evidence, and clearance/exposure/PK–PD. Five planned
  unit objectives now link to these worked lessons. The core route remains
  bounded; specialist routes and introductions expose the new chapters.
  All numerical cases are constructed, not new biological or clinical results.

- Added two bilingual research-decision cases on 9 September 2026: diagnosing
  the existing ChEMBL cross-assay failure and planning discriminating validation
  from a constructed measurement example. Linked three further curriculum units
  and added a researcher-oriented reader task. No new empirical results or
  operational experimental protocols were produced.

- Added a bilingual real-data lipophilicity preparation pack on 9 September 2026:
  source/download instructions, a read-only structure and label inspector, and
  an explicit modelling protocol draft. Inspected 4,200 records without filtering,
  splitting or fitting at that preparation stage; the data
  copy and student outputs are excluded from the curated public package.

- Added standalone English/Chinese lipophilicity training notebooks and website
  downloads. Scientific steps and tested functions are visible in the cells.
  Both editions executed in fresh local kernels on a constructed 20-molecule
  fixture, with a held-out-label mutation check. A subsequent approved local CPU
  run completed all 12 English code cells on 4,200 real records. Bilingual lab
  notes retain the worse-than-constant Morgan result and three cross-split identical
  bit fingerprints despite distinct structures/scaffolds. Actual Colab validation
  remains unrun; the cloud entry is an upload guide, not a
  published repository badge. Notebook-first teaching now precedes CLI use.

- Connected three editable notebook stages: label-free representations, synthetic
  fitting and measured lipophilicity. Added English/Chinese foundation notebooks,
  a shared execution-state/saving/troubleshooting guide, and curated downloads.
  Existing scientific functions and frozen empirical protocols are unchanged;
  actual Colab runtime execution remains unverified.

This is a teaching and infrastructure milestone. It does not establish
comprehensive coverage, independent learner success, prospective discovery,
or a new SOTA method. External reader feedback has not yet been collected for
this candidate.

## Historical v0.1 materials

The original [report](report/aidd-commons-living-report-v0.1.md) and
[citation](report/CITATION-v0.1.cff) retain their original identity. Read them
with the addendum when using the current candidate. Scientific protocol IDs,
dataset versions, and historical software records are not package versions
and have not been renamed.
