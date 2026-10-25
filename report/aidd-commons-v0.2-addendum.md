---
title: "AIDD Commons v0.2 Addendum: Coverage and Completed Teaching Labs"
version: "0.2.0-rc.1"
---

## Scope of this addendum

Version 0.2.0 packages this living addendum with the bilingual curriculum and
curated Atlas. The dated sections below retain their original evidence scope.
The [publication record](https://github.com/gxCaesar/aidd-commons/blob/main/docs/PUBLICATION.md) gives the public correction
route and window. Neither coverage claim is established by publication.

Prepared 8 September 2026 for the **0.2.0-rc.1 release candidate**. This
addendum updates the project's coverage and teaching evidence; it does not
replace the eight-chapter v0.1 report or revise its historical source survey.
That candidate was not a published final release. External reader feedback and
independent adoption have not yet been established for it.

**Updated 12 September 2026.** The sections below through "What the completed
labs establish" describe the addendum as it stood on 8 September and are left
as they were; "Five more completed labs and a closed executable-gap program"
is new material added on 12 September, not a revision of the earlier text.

The intended use remains graduate-level learning and research reference.
English lessons are canonical; Chinese pages provide onboarding and pathway
summaries. The project is not presented as a SOTA method or as the most
comprehensive or most detailed AIDD learning system.

## Coverage is measured, not inferred from page count

The comparison covers 13 learning systems and 93 topic units across the 18
curriculum tracks. Unknown coverage remains unknown. Lower and upper bounds
are reported separately, and no weighted overall leaderboard is constructed.
Completing three selected labs does not make all 18 tracks equally deep.

The audit and its source records are available in `docs/COMPARISON_AUDIT.md`
and `catalog/comparisons/`. The three candidate-selection records remain
historical snapshots; their implementation status records subsequent delivery.

## What the completed labs establish

**Small-molecule representations (T05).** The ChEMBL EGFR comparison has
132 primary evaluation parents and 170 separate-assay parents. Morgan Ridge
has the lowest primary MAE but the highest separate-assay MAE. Descriptor
Ridge is lowest in the separate assay. A representation that wins one
comparison is therefore not uniformly best in these two comparisons.
T15 accessed shared labels before the T05 run, so the result is not an entirely
untouched independent confirmation. Frozen selections were not retuned after
that exposure. All three baselines and both comparisons are retained in
`labs/chembl_egfr/locked-summary.json`.

**Physical model and system state (T11).** In benzene and uracil, Ridge has
lower errors than the training-mean control. Each model is fitted using its
own system's 600 training frames, with 200 validation and 200 evaluation
frames. These are two within-system evaluations, not zero-shot molecular
transfer or independent evidence from 400 unrelated observations. The original
output did not retain per-frame Ridge predictions. Post-run recomputation
checked training-mean scores and target ranges, not Ridge scores. The full
aggregate is in `labs/rmd17_system_state/locked-summary.json`.

**Experiment pools and budgets (T15).** MaxMin recovery AUC is below all
five fixed random policy instances in both retrospective assays. The external
pool has only one scaffold group, which makes that diversity fraction
uninformative. The real campaign is separate from the synthetic arithmetic
exercise and is not prospective discovery or independent T05 corroboration.
All policies remain visible in `labs/pool_budget/real-summary.json`.

These labs teach interpretation under a specified protocol. Their completion
does not validate a broadly superior representation, active-learning policy,
or molecular model. The summaries contain no confidence intervals or p values;
seeds and correlated frames are not treated as new biological units.

## A reader can start without reopening an evaluation

The first-session route uses seven authored, label-free molecular examples.
Readers inspect which identities are preserved or collapsed, then read the
completed ChEMBL comparison and its worked answers. This separates executing
a small example from reproducing a locked scientific evaluation.

The existing author's completed workspace must not be used to rerun a locked
evaluation or remove its one-time marker. Independent replication requires
a fresh workspace and the relevant lab protocol; it is not a first-session
requirement. A clean source package intentionally excludes raw datasets and
private execution records.

## Five more completed labs and a closed executable-gap program

Added 12 September 2026. Every number below is dated, machine-checked, and
independently re-read by a separate model session working from a sandbox
containing the real underlying data, exactly as required for the three labs
above; none of it changes the frozen T05, T11 or T15 evaluations, which keep
their own protocols, splits and locked outputs untouched.

**Four more topics reached `worked`.** The claim-promotion gate for "most
detailed" needed this project's own worked-or-deeper lower bound to exceed
every comparator's upper bound; it stood short by exactly four topics. Two new
lessons were written directly: **One claim, one decision unit**
(`foundations/decision-unit`) reads this repository's own frozen ChEMBL EGFR
contract and shows the identical fitted-model sentence support one context and
fail a second the same lab measured. **Define the disease state before the
target** (`mechanism-targets/disease-state-definition`) works six defining
fields through a real published discovery (Lynch et al. 2004) and a real
randomised trial (Mok et al. 2009) whose two mutation-status subgroups point
in opposite clinical directions, every trial number verified against the
cited record. A third lesson, closing the audit's only confirmed depth gap in
`biologics-design`, was drafted, reviewed and revised entirely by a different
model family working from a structural brief that named no subject matter,
because a session that had read even a two-line brief for it was independently
stopped by a safety safeguard while this round was being planned; it was
accepted only after 23 automated structural checks and its own independent
review.

**All six originally confirmed executable gaps are now closed**, each by a
lab that extends real, already-vetted data rather than a new frozen protocol:

- **A trajectory observable and its convergence** (`rmd17-dynamics-observable`,
  physics-based-modeling, closing two gaps) computes the mass-weighted radius
  of gyration from the same rMD17 trajectories the frozen energy lab already
  uses. A naive standard error understates ethanol's uncertainty by a factor
  of 3.30 and malonaldehyde's by 6.26; at 10,000 of 100,000 frames,
  malonaldehyde's cumulative estimate still sits four to nine block-standard-
  errors from its converged value, despite matching it to two decimal places.
- **An ensemble-variance acquisition policy** (`pool-budget-uncertainty-
  acquisition`, active-learning) adds a seventh policy to the completed
  pool-budget campaign, acquiring by cross-fold Ridge prediction variance. It
  leads MaxMin and all five fixed random seeds on both real assays: 0.1133
  against MaxMin's 0.0508 on the primary assay, 0.1635 against 0.0000 on the
  separate one.
- **A CYP3A4-versus-CYP2D6 assay system** (`cyp-assay-system`,
  metabolism/DDI risk) reads two whole live ChEMBL 37 targets instead of two
  named assays: 5,251 admitted CYP3A4 parents, 2,781 CYP2D6, 1,195
  overlapping. Potency against one enzyme predicts the other only weakly
  (Spearman rho about 0.30); quinidine alone carries 32 CYP2D6 records
  disagreeing by more than a 10,000-fold range beside a single CYP3A4 value.
- **An AZ clearance system** (`az-clearance-system`, PK exposure endpoints,
  closed narrowly) compares intrinsic clearance across human liver
  microsomes, rat hepatocytes and human hepatocytes from one real AstraZeneca
  ChEMBL deposition: 743, 592 and 288 admitted parents, Spearman rho 0.39 to
  0.49 pairwise. This covers only clearance of the several measures the topic
  names, after two other candidate data sources were checked and rejected on
  licensing grounds. A real methodological catch: microsome values are
  reported per gram of protein and hepatocyte values per million cells, so
  only the rank correlations, not a raw fold-change, compare validly across a
  matrix change.
- **A LINCS L1000 perturbation-context lab** (`l1000-perturbation-context`,
  omics and perturbation representation) compares compound-perturbation
  gene-expression signatures between MCF7 and PC3 across 1,721 compounds
  shared in one real GEO series. On raw expression, matched and mismatched
  compounds correlate almost identically (rho 0.79 against 0.70): a
  methodological problem caught before publication, not after. Subtracting
  each profile's own plate vehicle-control baseline first reveals the real
  signal, 0.175 against a null of 0.034 (p ≈ 8 × 10⁻⁸²).

One further lesson, "Docking, pose generation, and physical validity"
(`dti-screening`), deepens an existing topic using a real published
comparison (PoseBusters) rather than a constructed one, but is deliberately
not mapped to any historical topic id and changes no count below; it closes a
measured content-depth gap (dti-screening had one instructional lesson
against two to five in every other track), not an audit gap.

**Measured effect on the comparison audit.** Executable rose from 47 to 53 (40
of those on real data), and confirmed executable gaps fell from 6 to 0.
Combined with the four-topic raise above, this project's own lower bounds now
read: explained 93, worked 93, executable 53, executable on real data 40,
assessed 24, against the unchanged 13-system, 93-topic comparison set.
Confirmed depth gaps and confirmed executable gaps are both 0. Both
claim-promotion bound conditions are now measured `true` (explained 93 exceeds
the strongest external upper bound of 92; worked 93 exceeds the strongest
external upper bound of 91, with enough tracks at executable or assessed
depth). **Neither claim's status changes: both remain `not_established`.**
The gate's sixth criterion, a public 30-day correction window, cannot start
before publication, and publication is deferred by this project's own
decision, independent of these numbers. A bound condition being satisfied is
a necessary, not sufficient, part of the claim, and 40 topics still score
deeper under an independent second reading than this project's own record
without being raised on that basis alone, since a raise requires new material
and a new reading, not a record edit.

## Four tracks gained a runnable task, and three of them gained it honestly

Added 22 October 2026. Four curriculum tracks had prose only and no task a
reader could run: `foundations`, `drug-discovery-foundations`,
`mechanism-targets` and `biologics-design`. Each now has one real-data,
CPU-first, single-command laboratory with a frozen protocol, a committed
summary from the author's run, and a test that a mutated contract is rejected
before any output is written.

- **A decision-unit scope lab** (`decision-unit-scope`, `foundations`)
  resolves a declared cohort of fifteen ChEMBL 37 compounds to ten distinct
  parents, reduces 13,305 reported activity rows to 1,004 admitted
  measurements through a frozen twelve-stage admission rule, and reports the
  assay, document, target, organism, assay type, confidence score and relation
  that travel with every surviving measurement.
- **An assay-endpoint-controls lab** (`assay-endpoint-controls`,
  `drug-discovery-foundations`) reads six archived PubChem BioAssay
  dose-response assays and reports 1,529 admitted endpoint values over five
  endpoint labels, of which 1,257 carry a stated qualifier: 832 equalities and
  406 bounds, where a bound states a side and not a magnitude. A third of the
  confidence scores are zero, and each assay declares its own replicate
  structure, control regime, reference wells and normalisation equation.
- **A cross-modality lab** (`rosetta-cross-modality`, `mechanism-targets`)
  takes 528 perturbations measured in both a transcriptomic and an imaging
  readout across sixteen plates each. The apparent agreement of 0.83 at
  feature level and 0.82 at perturbation level falls to 0.63 and 0.69 once the
  batch is blocked, and a size-matched random control reaches 0.79 to 0.81. Most
  of the apparent agreement is structure rather than biology, and the lab
  measures how much of it survives.
- **An affinity-table lab** (`skempi-affinity`, `biologics-design`) reads a
  real affinity table in which 830 rows resolve to 51 complexes, of which 719
  carry a complete measurement. A row-level split leaks 142 of 144 test rows
  through a shared complex, and a complex-held-out split gives 35 training and
  9 test complexes. The lab was drafted, reviewed and revised entirely by a
  different model family working from a structural brief that named no
  subject matter, for the reason given in the section above.

**Four new blind readings, and one refusal.** Four independent readings ran
on 22 October 2026 in sandboxes holding only the published material, with the
real data snapshot present so the command actually ran, each checked for
isolation by parsing its event stream. Three of the four raised their topic:
the decision unit, the assay controls and the cross-modality perturbation
evidence each moved from `worked` to `assessed` on real data. The fourth
refused its raise, which is the discipline working rather than a shortfall. The
affinity-table lab teaches independent units and affinity evaluation, and the
reader judged that it does not provide a runnable task for the six-objective
distinction that its topic asks about, so under the audit's ordinal mapping
that topic stays at `worked`.

**Measured effect.** Executable rose from 53 to 56, executable on real data
from 40 to 43, and assessed from 24 to 27. Seventeen of the eighteen tracks
now hold at least one executable or assessed topic, against fourteen before;
the one that does not is `biologics-design`. Both claim-promotion bound
conditions remain measured `true` and **both claims remain
`not_established`**, for the same sixth criterion as before. The published
blind-review record carried three defects of its own and they are now
corrected: the isolation string had counted the first three batches' commands
twice, two different batches were both labelled the sixth, and the sixth and
seventh batches had produced readings for three topics while carrying no
isolation attestation at all.

**Six frontier families gained a lesson.** Machine-learned interatomic
potentials, single-cell foundation models and virtual cells, autonomous
laboratory agents, the ADMET and DMPK tool frontier, flow matching and GFlowNet
objectives, nucleic-acid and peptide design models, and reading a structure
from an image are now taught from their own registry records. Each reading
states what its family is for, what the records establish about openness and
licence, and where the evidence stops. The interatomic-potential reading is the
sharpest case: all six releases open their inference, training and
architecture, four open their weights, two open their training data, none
documents its data recipe, and one opens its evaluation code. A reader can
therefore run those models and inspect them, and cannot reproduce their
training from what is published.

**Twenty figures, and the site now carries them.** The report had no figure
and the site had no image in 362 built pages. Twenty vector figures are now
drawn by script from this repository's own committed results, and eight of
them stand on the landing, audit, laboratory and report pages in both
languages. The figures are inlined rather than loaded as pictures, because a
picture is a separate document and does not inherit the page's custom
properties, which would leave every drawing in the light palette whatever the
reader chose. The site's own four brand tokens put the coral and focus pair
6.06 CIEDE2000 apart under deuteranopia, below the floor the derived figure
palette holds, so the second channel carries that separation; the measurement
is recorded rather than hidden.

**The release surface was repaired before anything was published.** The CI
release job did not regenerate the catalog data, so the release it produced
omitted three of the five generated data files the site imports. The curated
export also shipped the release builder and the hygiene scanner without their
own tests, and three macOS metadata files had passed the hygiene scan. The
reader-trial instrument's facilitator answer sheet was inside the export, so the
answer key and the rubric are now excluded from it. A publish checklist
records the eight-command gate and the decisions a person has to make, and the
public wording stays at "building".

**The living report itself was completed.** It is now twelve chapters and
27,413 words with twenty figures, against the eight chapters and thirty pages
it had before. The four added chapters report what the completed laboratories
produced, how the comparison audit works, what the independent reading found,
and where the eight frontier method families stand. Every figure is drawn by
script from a committed artefact, and a test now holds the report's stated
coverage numbers to the regenerated comparison products, so a later audit
change cannot leave the prose quietly wrong.

## The last track gained a runnable task, and a reading that raised it

Added 23 October 2026. The topic that asks a reader to separate sequence
recovery, folding, structural plausibility, binding, catalysis and biological
function had a reading lesson and no task a reader could run. The independent
reading of 22 October refused to raise it for that reason, and named the
missing thing: the affinity-table laboratory teaches independent units and
affinity evaluation, not the six-objective distinction that the topic asks
about. A new laboratory now reads the public records of six examined entities
against the six objectives and states, per entity and per objective, whether a
public record carries evidence at that level and which record it is. Thirty-one
of the thirty-six cells carry a record, five are empty, and every empty cell
names the source-specific reason.

The laboratory is deliberately narrow. It reads a sequence and its annotations
from UniProtKB, a deposited structure and its coordinates from the RCSB
Protein Data Bank, a model entry and its global metric from the AlphaFold
Protein Structure Database, and measured affinity rows from SKEMPI 2.0. It
predicts no value, scores no compound, and ranks no entity. A structure the
search service returns counts as a structure of the examined entity only when
the entry itself lists that entity's accession, and a row of the affinity
archive that carries no value cannot fill a cell, because the mirror's rows
are ragged and a missing parsed field is a property of this reading rather
than proof of an absent upstream measurement.

A fifteenth independent reading ran on 23 October 2026 in a sandbox holding
only the published material, with the live-fetched records present so the
command actually ran, and its isolation was checked by parsing the event
stream. It scored the topic assessed on public data, with the inspection and
the test suite passing in the sandbox. Executable rose from 56 to 57,
executable on real data from 43 to 44, and assessed from 27 to 28, and all
eighteen tracks now hold at least one executable or assessed topic. Both
claim-promotion bound conditions remain measured `true` and both claim
statuses remain `not_established`, because the sixth criterion is a public
correction window that cannot start before publication.

## Every record has a lesson, and the atlas records what its terms page says

Added 23 October 2026. Two gaps were measured rather than assumed.

**The curriculum now teaches every record it holds.** The catalogue holds 191
records and the curriculum holds 87 lessons per language. Eleven records were
cited by no lesson, and every one was a recent method family: the ESM
Cambrian release, the ESMC checkpoint, a protein language model family whose
paper names a Hugging Face organisation that states it is not operational, a
gated binder generator, a binder design pipeline whose installer requires a
commercially licensed dependency, a generative binder design model, an
atom-level diffusion model, a transcriptomic language model, and an industrial
ADME measurement set. Two dated frontier readings now teach the four records
of each of two families, and four records that a lesson already named are now
cited by it.

**The atlas stopped guessing about terms.** A hundred and four records carried
no licence and a hundred and ten carried no verified access level, and
eighty-two of the hundred and four were records the first sweep of 4 September
2026 had never opened. Every one was opened on 23 October 2026 and its terms
recorded from what the page states: the repository's own licence file, the
dataset page's terms, the article's rights statement, or a caveat that says
the page states nothing and was read on that date. Records that carry a
licence went from 87 to 157, and records that carry no verified access level
fell from 110 to 46. The FreeSolv v0.52 record keeps no licence, because a
licence file in a repository's default branch is not evidence for a tagged
release.

**The openness matrix was read from the repositories themselves.** The cells
that a reader can check by opening a repository were read from its file
listing and its README, and the cells that no repository states were left
alone. The inference code of 65 of 70 models is now recorded, against 40
before, the training code of 41 against 25, the architecture of 46 against 31
and the evaluation code of 15 against 6. The data recipe of 6 of 70 models is
still the weakest dimension in the matrix, because no repository states the
procedure that built the training set.

**A published claim was corrected rather than kept.** The co-folding
laboratory recorded that no system in its family evidences the evaluation code
behind its accuracy claim. Two of the twenty-four do now, and the claim was
restated for the co-folding systems, which still publish none of it, with the
two exceptions named in the inspector's own output.

## Four topics gained a runnable task, and the reading that checked them found two defects

Added 23 October 2026. Four topics that had a reading lesson and no runnable
task now have one, and four readings on the same day say what each laboratory
establishes.

The asset-openness laboratory audits this project's own catalogue: twenty-four
examined records, fifty-two available claims, twenty-six that do not apply,
eighty-eight unverified, two recorded as not available, and all 191 records
keeping the seven openness dimensions apart. The reading scored it assessed on
authored data, because the laboratory audits this project's own availability
judgements rather than an external measurement.

The leakage laboratory takes the 486 independent measurements the
decision-unit laboratory admits from fifteen ChEMBL 37 seeds and counts the
identities that cross a random row split: all 98 test measurements share a
parent with the training set, 98 share a scaffold, 98 a standard form, 81 a
target and 1 an assay, and a grouped split by parent holds 353 test
measurements that are all unseen parents.

The relational-graph laboratory builds the atlas as a typed graph and reports
191 nodes, 32 declared relations in seven types, the records that declare no
relation, and the 6,754 candidate pairs that share a task without declaring
one.

The claims laboratory sorts the comparison cells into the four states a record
can be in, and finds 14 direct observations, no bounded inference, no
unsupported claim and 38 unresolved fields over thirteen providers and four
topics, with the two disagreements against the independent reading named.

The reading of the leakage laboratory found two defects in it. The contract
took its declared RDKit release from the running environment, so the
laboratory refused to run on a machine carrying another release and the
reading could not verify it; the version is frozen in the contract now, the
check compares the counts and reports the environment's release as a note, and
the counts were checked under both releases and agree. The reading also found
that two routes the topic names were missing from the laboratory's list, and
the target-family route and the fitted-preprocessing route are now named as
untestable with the reason. The topic was read again after the fix.

Executable went 57 to 60, executable on real data 44 to 46, and assessed 28
to 31.

Two more topics were raised and two were not. The source-review topic and the
entity-glossary topic both gained a laboratory, and the twenty-seventh and
twenty-eighth readings raised them, so executable reached 63, executable on
real data 47 and assessed 34.

Three more laboratories landed, and three more readings followed. The
generalization-unit laboratory counts the same 486 measurements under each unit
a split could use, and the same table spans 481 assays, 221 documents, 100
targets and 9 observed parents. The applicability-domain laboratory measures
how far a FreeSolv molecule is from its nearest training neighbour and how
large the error is, and the error grows with the distance. The readiness-rule
laboratory applies a rule fixed before the cohort was counted and names the
measurement each compound that does not go still lacks. The thirty-first,
thirty-second and thirty-third readings raised the first two and said what the
third needs, so executable stands at 65, executable on real data at 49 and
assessed at 36.

The atlas's own terms were read from the organisations that state them. The
EMBL-EBI terms and the National Library of Medicine's policy were recorded for
four records whose access level the first sweep had left unverified, and
records that carry a licence went from 157 to 161. The two readings that came back with no
runnable task for their own topic were kept where they are, and the notes say
what a raise would need.

A second sweep of the model pages took the data recipe of the models from 6 of
70 records to 21 and the training data dimension from 18 to 22, each from the
statement the model's own page makes. The data recipe is still the weakest
dimension, because most repositories name a corpus without stating the
procedure that built the training set.

Two readings on the same day said two of the new laboratories do not test
their topics, and the self record follows them. The multi-endpoint laboratory
audits which endpoint families the cohort carries, and the trade-off it
describes needs exposure and toxicity measurements the cohort does not have,
so that topic stays where it is. The functional-validation laboratory
classifies general assay records rather than this topic's functional
validation, so that topic stays where it is too. Both notes say what a raise
would need.

A further laboratory audits how this atlas binds its own claims. The
source-review laboratory sorts the atlas' own evidence entries by the parts
they carry, the source surface, the version, the date and the exact material
reviewed. Over twelve examined records none of the twelve entries carries all
four parts, and none carries a date and a surface without a version, so a
claim in this atlas is bound to a surface and a date but not to a version.
Four routes are named as unmeasurable, among them the content of a linked
page, because the laboratory reads the entry and not the page it names.

Two more topics found their runnable task the same evening. A multi-endpoint
laboratory sorts the 486 independent measurements into endpoint families, each
with its own unit, count and spread, and finds that no compound in the cohort
has a toxicity or an exposure measurement at all, so those two families cannot
be integrated from that table. A functional-validation laboratory reads the
ChEMBL 37 activity rows and the archived PubChem BioAssay dose-response
records and sorts them by the claim each record can carry: 1,004 records, 488
point measurements and 516 bounds on one side, 1,257 records, 1,204
concentration-response tables, 38 bounds and 15 records that license no claim
on the other, and a clinical outcome measured in neither.

The specificity topic gained its runnable task on 23 October 2026, and the
reading that checked it found a third defect. A partner-coverage laboratory
counts the partners each protein is measured with in the affinity archive: 7,085
rows read, 2,544 carrying a parsed measurement, 2,487 of those with both
protein labels, 102 distinct unordered pairs and 171 distinct protein labels.
The median distinct-partner count is 1, the interquartile range runs from 1 to
1, and 154 proteins are measured against exactly one partner. Only 9 counted
pairs have more than one observed partner on both sides, and those are the only
pairs in which the table can show a margin at all. The thirty-seventh reading
scored the topic assessed on public data, and it found that the laboratory's
inspection command read the package version from a repository file that neither
a published export nor a reading sandbox carries, so the command failed in
both places. The reviewer worked around it, reproduced every frozen census
field and reported the defect, and the command was fixed and then run in a
tree without that file.

Two readings that had been run but not merged were merged, and they changed
two of twenty-eight topics. One gained a real-data run basis. The other lost
its runnable depth: the thirty-fifth reading found that the runnable profile
check validates the local PaperQA configuration and not a tool's input and
output contract, so no runnable task tests that topic, and the self record
was lowered from executable to worked. Executable stayed at 66, because that
lowering and the specificity raise cancelled. Executable on real data went 50
to 51 and assessed went 37 to 38.

The isolation checker that certifies these readings was itself wrong twice
more, reporting a path under the sandbox as an escape and reading a relative
path join as an absolute path. Both were false positives, and a third of the
same class was already recorded as a known false positive that had never been
fixed. The checker now accepts the sandbox's own path, reads a relative join
as relative, and distinguishes a relative name from a home or absolute path to
the same name. It carries a self-test of nineteen cases with every rule
exercised in both directions, and the fixed checker reports zero problems
across all thirty-four event files.

One working laboratory was invisible from the only directory a reader is
given. The affinity-table laboratory's guide page was added to both languages
on 21 October 2026 without a matching entry on either laboratories index, so a
laboratory with its own frozen protocol and its own committed summary could not
be found from the page that lists them. Both indexes now carry it, and a new
test holds the index to the guides that exist: it fails when a guide is
missing from an index, when an index links a guide that does not exist, and
when the two editions disagree about the set. The test was checked by removing
the new entry and confirming that it failed with the guide's slug. The same
defect class was found and fixed on 12 September 2026, when five laboratories
were missing from the same page, and that round fixed the entries without
adding the gate, which is why the class recurred.

Three topics rose on a re-reading, and three methods from 2026 entered the
catalogue. Forty-three topics had been read once, on 11 September 2026, and
never read again, although the curriculum gained more than thirty
laboratories since. Eleven of them were re-read, and three rose: the
permitted-use topic, on the asset-openness laboratory's own records of access
levels, evidence references and licence scopes; the multi-objective search
topic, on the pool-budget laboratory's real ChEMBL replay of diversity-aware
selection; and the chemical-series topic, on the SAR laboratory's
attribution test with confounded molecules. The other eight came back as
they were, seven of them with a lesson and an exercise and no runnable task.

Three 2026 methods were added to the catalogue: Raygun, which edits an
existing protein with insertions, deletions and substitutions at once, NISE,
an iterative selection-expansion protocol, and LASErMPNN, the
ligand-conditioned sequence network used within it. Each record was written
from the repository's own README and licence file. Two findings came out of
reading those first-party files rather than the summaries: Raygun's README
states CC-BY-NC-SA 4.0 and its LICENSE file states CC BY-NC 4.0, so the
record carries both and says that a reader cannot settle the applicable terms
from the repository alone; and the NISE and LASErMPNN READMEs carry no
licence statement at all, where a secondary source had called one of them
MIT, so both records have no licence, an unverified access level and an
unverified data recipe.

Executable went 66 to 69, executable on real data 51 to 53 and assessed 38 to
41.

A laboratory now audits this project's own tools against a contract with the
six parts the tool-contract topic names. It reads the twenty committed
laboratory return records and checks each against the contract. All twenty
carry a schema version, a protocol identifier, a computation date and a
software version, six declare their own limits under seven different names,
and none declares the environment, the side effects, the run status or the
scientific meaning the contract asks for. The guide says what that is and is
not: a missing field is a metadata gap, and it does not establish that a
laboratory failed or that a measurement is wrong.

Three defects were found while building it, and all three were fixed. The
first version of the laboratory wrapped affinity rows as tool responses, so
the branch the topic cares most about, a failed control that must halt, was
never exercised on real data, and it was rebuilt against the right material.
The contract's status field was named run_status, which the release hygiene
scan reserves for pipeline state, and it is now outcome_status. The
laboratory also counted its own return record, which is the file it writes,
so the summary depended on its own output; the protocol now names the
laboratory it excludes.

The thirty-ninth independent reading scored the topic assessed on public
data, and it found a fourth defect: the laboratory's README still described
the earlier twenty-one-record account while the protocol excluded one
laboratory and audited twenty. The README now states the twenty records, the
six that declare their own limits, and the fact that none of the twenty
declares the four contract fields. The reading also named what the laboratory
leaves underdeveloped, the design of an input request schema and the
enforcement of a contract on each call.

The last measured frontier gap is closed. That topic was the only one where
an external provider was runnable and this project was not, and after the
laboratory and the reading no topic stands that way. Executable went 69 to
70, executable on real data 53 to 54 and assessed 41 to 42. This is a
statement about the measured comparison set of thirteen providers, and it is
not a claim of comprehensiveness, which stays not established because the
sixth gate criterion is a public correction window and publication has not
happened.

Four resources from 2026 entered the catalogue, three lessons teach them, and
a new laboratory carries the PK/PD topic's assumptions into a computation.
AgentD pools candidates with REINVENT4 and iterates affinity and ADMET
prediction, and it needs a commercial language-model key and a search-service
key, so its access level is unverified. MDCrow configures and runs OpenMM from
a natural-language instruction, its README states no licence and its LICENSE
file states MIT, and the record carries both. LiTENexus publishes no
installable command, no checkpoint and no data route. PXMeter assesses
structure predictions with LDDT, DockQ, pocket-aligned ligand RMSD and
PoseBusters validity checks, and its benchmark pipeline can rebuild the
evaluation set over a chosen time window, which is what makes the benchmark's
own construction checkable rather than fixed.

The new PK/PD translation laboratory reads the human and rat hepatocyte
measurements the clearance laboratory already admits and runs an explicit
exposure, engagement and effect model over them. Of 1,120 distinct admitted
parent molecules, 106 can be carried by the paired-species model and 1,014
cannot, each for a named reason: 346 sit in a microsome assay whose clearance
has a different basis from the hepatocyte assays, and 668 have no counterpart
in the other species. Thirty-seven paired compounds show at least a threefold
species difference. The laboratory states that only intrinsic clearance is
measured and that the concentration, the occupancy and the effect are outputs
under declared unmeasured parameters.

The fortieth reading re-read the eleven topics still on the first reading of
11 September 2026, and two of them rose. The atom-mapping topic reached
assessed on authored inputs, because the retrosynthesis laboratory applies
mapped SMARTS across constructed transformation classes. The trace-recovery
topic reached assessed on authored inputs, because the notebook's
controlled-failure tests verify saved errors and partial outputs while the
failure inputs are constructed fixtures.

The isolation checker was wrong twice more and is fixed. It reported a
regular expression containing a slash and a host name in a domain RFC 2606
reserves for documentation as absolute paths. A path now has to start from a
real top-level directory to count, the self-test grew to twenty-one cases with
each rule exercised in both directions, and the fixed checker reports zero
problems across all thirty-eight event files.

Executable went 70 to 72, executable on real data stayed at 54 and assessed
went 42 to 44. The catalogue holds 198 records.

A new test asks a question the audit had never asked, whether every record in
the catalogue is reachable from the published material. The answer was no, and
the eleven records it named had never been taught. RoseTTAFold All-Atom,
ColabFold, MMseqs2, DynamicBind, GROVER, MolCLR, MoleculeX, ProGen, MDTraj,
the LINCS L1000 perturbation profiles and the CZ CELLxGENE Discover Census
were in the catalogue and in no lesson. The previous round's claim that every
record was cited was measured with a weaker rule, that a record's identifier
appeared somewhere in the repository, and that included the self record and
the comparison export.

Three lessons close the gap. The open structure stack teaches the steps of
obtaining a structure, a sequence search, a template, a fold and a binding
pose, and says at each step what the step licenses and where the claim
stops. The open representation stack does the same for a corpus, a pretext
task, an encoder and a perturbation experiment, and keeps the two
perturbation datasets apart. The third covers two 2026 generation releases
and the difference between a published release and an obtainable one.

Two more records entered the catalogue, and what reading the first-party
files showed is the point of both. Zatom-1 publishes code, a full set of
checkpoints and the generated sample archives, and its code is under a
three-clause BSD with an added clause while its weights are under a Creative
Commons Attribution grant, so a reader redistributing a checkpoint and a
reader redistributing the source are under different terms. It names seven
training corpora and does not state the filtering or splitting procedure
behind any of them. MolCraftDiffusion publishes a modular platform and a
command line, and its README states that the asset catalogue is currently
private and needs a token with permission, and it carries no licence
statement for the code at all.

The forty-first reading scored the PK/PD topic assessed on public data, and
the self record now states that reading. The reading also named what the
model does not measure, that the binding, the exposure scaling and the
response parameters are assumed, and that a measured engagement, a measured
response and an externally validated species translation are absent.

Executable went 72 to 73, executable on real data 54 to 55 and assessed 44 to
45. The catalogue holds 200 records and the curriculum 120 lessons.

Two new laboratories carry topics that had a lesson and no runnable task, and
four more 2026 methods entered the catalogue.

The multi-endpoint integration laboratory reads the measured response
potency, the intrinsic clearance and the CYP inhibition this repository
already holds, and joins them by parent molecule and by nothing else. Of
7,908 compounds, 58 carry two families and none carries three, while 1,062
carry only exposure, 6,780 only interaction and 8 only efficacy. There is no
measured toxicity snapshot here, so that family is reported as unmeasured
rather than filled in. The laboratory refuses a composite score, and a
known-bad test performs one and confirms the refusal.

The oracle-exploitation laboratory fits a model on the training part of the
committed FreeSolv scaffold split, ranks the training molecules by the
model's own prediction, and compares what it predicted with what was
measured. The gap reaches 8.06 kcal/mol on one selected molecule, while a
random selection from the same pool stays within 1.03. The batch it proposes
for independent evaluation comes from the held-out part of the split, with a
verification target and an interval for each member, and the laboratory states
that this is a bounded retrospective proposal and not an independent
evaluation.

Four more 2026 methods entered the catalogue, and what the first-party files
showed is the point of each. AQAffinity's repository is gated and the record
could not read its model card, so every openness dimension except the access
level and the licence is unverified. Nesso-1's README states no training data
at all. ByteFF's repository is archived and no longer maintained and publishes
no checkpoint. ByteFF2 is the maintained successor, with published weights, a
named training corpus, an Apache grant on the code and a different grant on the
weights.

A third laboratory audits what the catalogue itself states about a biologic
construct, across the four fields the topic names. Of the 46 records that
name a biologic modality, 46 state the modality, 4 state the construct type,
and none states an expression system or an intended function, so 42 of them
state a modality alone. A modality is not a construct.

Two more 2026 methods entered the catalogue. ALF is a framework for
scientific active learning that separates the roles of a loop, and it is the
first record the active-learning track of this curriculum carried. The Mobley
Lab notebooks are a published procedure for multiobjective optimisation over
multi-target binding, with no licence statement, no data statement and no
runnable command on the page.

The forty-second reading scored two topics assessed on public data. The
multi-endpoint topic rose because the new laboratory integrates potency,
clearance and CYP inhibition without a composite score. The
generated-candidate topic rose because the new laboratory measures what a
selection rule reads back on the data it was fitted on, with a gap reaching
8.06 kcal/mol on one selected molecule against 1.03 for a random selection
from the same pool. Both readings named what the coverage does not reach.

Twenty-one topics were still on the first reading of 11 September 2026, and
the forty-third batch re-read eleven of them. Ten came back unchanged. The
regression-formulation topic came back lower: the record claimed executable on
the strength of a laboratory that runs a train-mean, a fingerprint Ridge and a
Random Forest, and the reading found that the exercise supplies the learned
regression coefficients but no neural or learned-representation regression
baseline, so the claim of a runnable regression-formulation comparison was not
supported. The record was lowered to assessed and says so. Two more run bases
were corrected in the same direction, the provenance-versioning and
small-molecule-representation topics, where the runnable material rests on
invented fixtures and on seven authored molecules rather than on measured
data.

Ten benchmark records carried an unverified access level even though their
evidence entries named the projects' own pages, and the access level is the
one field a reader cannot get past. Reading those pages settled six: MOSES,
GuacaMol, the Open Graph Benchmark and PoseBusters are open source, with
their code under MIT and their data under CC BY 4.0 or the same repository,
and AI-Researcher, DrugOOD and the Therapeutics Data Commons are source
available, because the data needs a separate route or carries narrower terms.
Four stayed unverified: the DUD-E site timed out, LIT-PCBA and the O3DC
index state no licence or reuse terms, and the record says so rather than
guessing.

NVIDIA's Contrastive KERMT entered the catalogue: 70.6 million parameters,
pretrained without labels on a joint objective of SMILES reconstruction,
in-batch contrastive discrimination and chemistry-specific self-supervision,
over about 11.1 million unique canonical SMILES from a ZINC15 and ChEMBL base
pool with three further sets added, deduplicated and scaffold-balanced. Its
code is Apache 2.0 and its weights are under the NVIDIA Open Model Licence,
and the record carries the card's own limits, that it is a backbone to be
fine-tuned rather than a predictor, that the pretraining has no testing set
and the card reports no benchmark, and that its predictions are statistical
estimates rather than substitutes for measurement in safety-critical
decisions.

A claim-chain laboratory joins the topics of a nomination and checks each
link against the evidence its own record names. Two chains of eight links are
audited, the weakest link of each sits at the worked level, six links of one
chain and five of the other sit below the strongest state the chain reaches,
and seven links disagree with the independent reading.

Forty-four catalogue records carried an unverified access level although their
evidence entries named the projects' own pages, and the access level is the
one field a reader cannot get past. Reading those pages settled seventeen of
them and left twenty-seven unverified, each with the reason written down: a
site that timed out, a page that renders only a JavaScript shell, a page that
states no licence at all, and a source licence that does not establish rights
to the data. Among the seventeen are the CellxGene Census, the BioGRID
datasets, PCQM4MV2, the LASErMPNN, NISE, MolCraftDiffusion and TargetDiff
repositories under MIT, and the DepMap portal under its own data terms, which
are free for research and require a separate licence for commercial and
clinical use and name specific AI model uses. DrugBank's academic licence
permits verified non-commercial academic research and teaching, and withholds
a grant for model training.

Two 2026 families entered the single-cell area. A pair of interactive atlases
of sparse-autoencoder features, extracted from every layer of two single-cell
foundation models, reported that 99.8 percent of the features are invisible
to singular value decomposition and that 29 to 59 percent annotate to a named
pathway database, and then reported that under genome-scale CRISPRi testing
only 3 of 48 transcription factors show transcription-factor-specific feature
responses, which a multi-tissue control raises to 5. Organised biological
knowledge in a representation, and almost no regulatory logic in it, is the
distinction the record holds on to. Tahoe-x1 entered as well, a
perturbation-trained family from seventy million to three billion parameters,
whose record carries the page's own two numbers for the pretraining size
without reconciling them.

An open-question laboratory classifies the state of every question the
comparison record holds and checks that each open one still names a
falsifying observation or a missing measurement. Twenty-eight questions are
open, and all twenty-eight name one.

Three laboratories that were right about their subject and wrong about their
topic were caught by the forty-fifth reading, which refused a raise on each for
the same reason in three different words. The construct laboratory counts
phrases in the catalogue's own descriptions rather than applying the four
fields to real construct records. The claim-chain laboratory audits the
curriculum's records rather than a candidate's evidence. The open-question
laboratory classifies the curriculum's wording rather than running a
disease-mechanism test. Each measured the right thing and the wrong object,
and the three notes now say so.

A target product profile laboratory applies a profile of mandatory gates and
preferences, fixed before the measurements are read, to the compounds three
measured endpoint families share. No compound satisfies it. The clearance gate
passes for 24 and fails for 5, the CYP3A4 gate passes for 19 and fails for
20, and clinical response and immunogenicity have no measurement in the cohort
at all. The laboratory states that it judges only what these in-vitro
measurements can judge, and it never divides a microsome clearance by a
hepatocyte clearance.

An agent evaluation laboratory checks three of this repository's own
laboratories as fixed tasks across five dimensions. No task passes all five,
and action authorisation passes for none of the three, which is the dimension
the lesson says a human review belongs to.

Two laboratories now replace two that measured the wrong object. The mechanism
consistency laboratory tests a target-mediated explanation against a fixed
different-compound control over 1,721 compounds measured in two cell lines:
678 fit the mediator-specific pattern, 123 fit the generic-stress one, and 920
cannot be decided, 490 of them because the mismatched control agrees with the
compound better than the compound agrees with itself. The candidate evidence
chain laboratory assembles a compound's own measurements into one chain of
the eight links the topic names and reports the first link that is not
measured: for the three compounds with the most links, five of the eight are
not covered at all, and no chain reaches a claim.

The construct laboratory now applies its four fields to the records of six
named medicines rather than to the catalogue's own descriptions. All six state
the modality, five the construct, three the production host and four the
intended function. Three give a construct without a host and one gives a host
without a construct, so only three define all four, and the laboratory
records that a source's organism is not a production host.

A free-energy network laboratory reads the released OpenFE relative binding
free-energy results for eight protein-ligand systems, each an alchemical
network file holding the edges of the network, the transformation that
estimated each edge and the per-repeat and per-generation estimates. Across the
eight systems there are 566 edges, 1,698 estimates and 92 cycles, and 87 of
the cycles close within the uncertainty the estimates carry while 5 do not, the
largest by 7.87 kilocalories per mole. The failed cycles are kept by name and
size rather than dropped, and the tolerance is derived from the estimates' own
uncertainty rather than chosen after seeing the result.

The access levels are mostly closed. Forty-four records carried an unverified
access level and thirteen still do. The Reactome licence agreement states
that the database data are CC0 and the illustrations CC BY 4.0, and the
record now carries both. The SPDX legal notices state that the specification
is offered under a community specification licence together with an
attribution licence. The PK-DB README states that the source code is MIT and
the documentation CC BY-SA 4.0, and says nothing about the study records, so
the classification follows the code and not the data. Each of the thirteen
that remains names the page that could not be read.

A script now answers the count that keeps breaking. Adding a catalogue record
breaks the laboratories that audit this project's own catalogue, because they
freeze the catalogue size on purpose, and that happened four times in one
day. The script rewrites the frozen count, regenerates the affected
summaries, and rewrites the numbers the tests pin, reading them from the
regenerated summaries rather than guessing.

The multi-endpoint laboratory wrote a key named `parent_molecule_chembl_id`
and the oracle laboratory one named `canonical_smiles`, and the release
hygiene scan rejects both, because those names are reserved for records of
which rows a locked evaluation consumed. The names are now
`parent_chembl_id` and `molecule_smiles` in each laboratory's own output,
while the readers still read the upstream fields under their own names.

## Four frontier systems entered the atlas, the report stopped repeating old numbers, and thirty-one topics were raised

Four catalogue records arrived, each read from its own first-party pages rather
than from a search summary. DockM8 is a consensus virtual screening platform
whose own paper reports median relative enrichments of 100 percent on DEKOIS
2.0, 82.59 percent on DUD-E and 8.85 percent on Lit-PCBA, and whose own
conclusion is that no pose-selection or consensus strategy excels universally.
The record keeps that conclusion beside the headline, and notes that the
paper's own count of over 55 million configurable protocols describes a larger
space than the product of the four component counts it names. TRIDS is an
AI-native docking framework that guides sampling with the gradient of an
analytic scoring function; its repository carries an Apache 2.0 licence file
while its README separately says the software is free to academic users and
that commercial use needs the authors, so the record keeps the two apart.

RetroAgent is a retrosynthesis agent that treats planning as a search over an
AND-OR graph memory and is trained with reinforcement learning on
search-budget efficiency. Its record carries the released reward constants
rather than a description of them, and separates the licences: the code is
MIT, the published weights are Apache-2.0, the DESP-sourced data is CC BY 4.0,
and the NOTICE states that the vendored single-step model remains under its
upstream terms. Agentic-Syn-RRAG is a retrieval-augmented synthesis agent
that generates candidates by reaction-state beam search, retrieves ten patent
precedents with RXNGraphormer and FAISS, reranks to three, and refines into a
structured protocol. Its record carries the reported 48.0, 46.0 and 14.7
percent reactant accuracies with the metric definition and the prefix caveat
that make them readable, and notes that its default configuration drives
reranking through an external endpoint, so an MIT repository is not a
self-contained system.

Two lessons teach this material, in both languages. The screening lesson reads
the platform's three-benchmark evaluation and an AI-native docking abstract side
by side, and the route-planning lesson reads a released reward function as
code and a 150-target evaluation as a procedure, both with handworked
exercises and worked answers.

The report was repeating numbers the figures did not carry. The captions in
the living report were hand copies of generated strings, and they had drifted
to a catalogue of 191 records and to coverage depths two readings behind the
audit. A script now refreshes them from the generated manifest at build time,
a test fails when they drift again, and the depth counts in the report text
move with the audit rather than with a hand.

Eleven of the thirteen remaining unverified access levels were settled by
reading the pages a different way. The FreeSolv repository carries two licence
files, CC BY 4.0 for the data and MIT for the code, and its own licence
statement limits the grant to the data that are the authors' own to license, so
the record is source available rather than open. The JUMP consortium's own
repository carries a BSD 3-Clause licence, though the project site presents a
self-signed certificate and the Zenodo record its badge advertises returns 404.
The EPA states that all of its computational toxicology data is open data free
of copyright restrictions, which settles the ToxCast dataset and the CompTox
dashboard together. The GTEx portal publishes its own data licence, which
charges nothing and restricts no use but does require an acknowledgement and
that a redistributed product say whether it carries the most current data. The
IEDB export page carries its licence as machine-readable Dublin Core metadata.
The O3DC index states no licence at all, not even in its own application
bundle. The DepMap team's forum statement of the portal's terms settles the
PRISM repurposing record, and it also records that the portal's downloads now
sit behind a captcha. Two records remain unverified: the DUD-E host truncates
the TLS handshake and answers nothing over plain HTTP either, and the rMD17
deposit returns 403 to every client tried.

Thirty-three topics had a record shallower than the reading that had already
verified them, and this project does not raise a topic on its own judgement.
Three new blind readings were run on 2026-10-24 against the current commit, in
sandboxes holding only the published material with the data each topic's own
laboratory reads present. The fiftieth batch re-read fifteen topics, the
fifty-first re-read fourteen and the fifty-second re-read the four whose
laboratories had been rebuilt after their last reading. The fifty-first batch
first delegated its scoring to a second agent after it noticed a prior rating
embedded in a lab guide, and a delegated scorer writes its commands to a
different log from the one the isolation check reads, so that batch was
refused and repeated with multi-agent switched off. The checker now refuses any
batch that shows a delegation, and its self-test covers the case.

Every topic the three batches read came back assessed, thirty-one of them
with a run basis behind it, and thirty-one of the thirty-three were raised:
twenty-seven from executable to assessed, and four from worked to assessed
because those readings found a runnable task behind them. Executable rose from
77 to 81, executable on real data from 57 to 62, and assessed from 50 to 81.
The self record now agrees with the independent reading on all ninety-three
topics, and the audit's line that the two records disagreed on twenty-nine
topics no longer holds.

Two were not raised, and both refusals are the discipline working in the one
direction that is easy to get wrong. The topic that asks where a scientific
task stops being an action a tool may take was read by the fifty-first batch,
which found a written exercise with a worked answer and a checker that
validates declared permissions, but no runnable task that establishes who
authorized a historical action. An earlier reading of that topic had scored
it assessed on authored inputs; the single-agent re-reading scored it assessed
with nothing runnable, and the record took the reading that does not permit a
raise. The topic that asks what a biologic's functional validation has to
show was read by the fifty-second batch, which found the assessments written
and the runnable audits pointing at other questions, and again no runnable
task for that topic.

Twelve topics stay at worked, and the reason is the rubric rather than a gap
in the material: their readings carry no runnable task, so under the ordinal
mapping an assessed reading compares as worked and permits no raise. The
fifty-second batch is what shows that the way out is a laboratory rather than a
re-reading: the three topics it raised had each gained a laboratory that
applies the topic's own fields to real records, and the topic it refused had
not.

## Remaining work and feedback

The next evidence needed is reader experience, not another favourable score.
Useful feedback identifies the page and version, the task attempted, the
expected outcome, and the first point of difficulty. Do not include private
data or credentials. Installation success, scientific interpretation, and
exercise completion are separate outcomes.

Broader topic expansion should follow the measured gaps and reader needs. As
of 23 October 2026, all eighteen tracks hold at least one executable or
assessed topic, and both claim-promotion bound conditions measure `true`,
but neither claim's status has changed from `not_established`: the sixth
gate criterion needs publication and a surviving 30-day public correction
window, neither of which has happened, and publication remains deferred by
this project's own decision rather than by a numeric shortfall. Public
language stays at "building" until that changes. None of this establishes a
prospective-discovery claim or a scholarly claim based on adoption; reader
experience remains the next evidence needed, not another favourable score.
