# What does an assay actually contain?

A drug-discovery table says a compound has a potency value. The assay behind that value says much
more: which endpoint was measured, whether the recorded relation was an equality or a bound, how
many replicates the curve had, what the plate's control regime was, and what the normalisation
equation actually did to the raw readings. This lab opens six archived PubChem BioAssay
dose-response assays and reads those things off the archive itself, then asks the question that
decides what a reader may conclude from them: does each assay carry the control record that its
own protocol says it has?

It is a descriptive read of already-published measurements. No model is fitted, no prediction is
made, and nothing here is a comparison of compounds' worth. What this does not show is any claim
about how potent, selective or clinically useful any compound is. A curve can be beautifully
measured and still say nothing useful about a decision, and an assay can carry a full dose-response
curve and still license no conclusion at all because its own control record is missing. The
protocol's `excluded_by_design` list is the machine-readable version of that sentence.

## Data and provenance

The source is the PubChem BioAssay archive on the NLM public FTP, specifically the per-assay
result CSV and the per-assay description XML. The six assays are declared in
`protocol.json`; each carries the exact container URL, the member path inside that container, the
container's byte length, the member's compressed and uncompressed byte lengths, and the member's
CRC-32 as the archive records it.

The access pattern matters, because the containers are large and the members are small. The
per-assay files are single gzip members inside ranged container zips that hold a thousand assay
identifiers each. The reader locates the container's central directory with HTTP byte-range
requests and reads only the declared member, so a container of 1,313,522,439 bytes is never
downloaded in full. What is cached is the archived record after both the zip and the gzip layer
have been undone, and every run re-checks that byte length before it reads anything. The six
assays together cache 407,461 bytes.

The archive is dated. The byte lengths and CRC-32 values in the protocol are what makes the cache
a snapshot rather than a moving target: if the upstream archive changes, the check fails rather
than silently measuring a different file.

## Frozen protocol

`protocol.json` records the frozen contract under the protocol id
`pubchem-bioassay-endpoint-controls-v1`, issued 2026-10-21. It fixes:

- the declared question, the six declared assays, and both retrieval URLs;
- the entity rule: the grouping unit is the PubChem compound identifier within one assay, the
  entity identifier is `PUBCHEM_CID`, the structure is the archived inline
  `PUBCHEM_EXT_DATASOURCE_SMILES`, and the admission rule is stated as an explicit list;
- the endpoint definition, with the unit and the direction of the measurement, and the rule that
  an equality is a measurement while a bound is a censored value that states a side and not a
  magnitude;
- the control contract, including the keyword lists that separate an unambiguous control keyword
  from an ambiguous one, and the reference-well keywords;
- the preprocessing fit scope: the only fit in this lab is a per-compound four-parameter logistic
  fitted to that compound's own archived per-concentration points, and only for the assays whose
  archived record carries the points;
- the split rule and seed, whose only purpose is a stability check on the cheap baseline;
- the baselines, the metrics, the curve tolerance, the equation scale check, and the
  `excluded_by_design` list.

Nothing in the protocol is chosen after a result is seen. The assays were declared, the tolerance
was fixed, and the reading was computed once.

## Setup

Python 3.11 and the project's pinned environment.

```bash
uv sync --group dev
```

## Reproduce

From the repository root. The first command needs network access; the rest do not.

```bash
.venv/bin/python labs/assay_endpoint_controls/run_lab.py download
.venv/bin/python labs/assay_endpoint_controls/inspect_assay_endpoint_controls.py show
.venv/bin/python labs/assay_endpoint_controls/inspect_assay_endpoint_controls.py check
.venv/bin/python labs/assay_endpoint_controls/export_summary.py
```

`download` fetches the declared members into `.cache/assay_endpoint_controls/` and re-validates
every byte length against the protocol on each run, so a second run against an intact cache
downloads nothing. `show` prints the reading. `check` recomputes the invariants and exits
non-zero when one is violated, which is what the test suite and the release scan rely on.
`export_summary.py` writes the committed `summary.json`.

The committed `summary.json` is the author's run, computed on 2026-10-21 with Python 3.11.15,
numpy 2.4.6, scipy 1.17.1 and rdkit 2025.09.6. It holds counts, distributions and named examples,
not raw rows.

## What to inspect

The cheap baseline comes first, and it is the whole of the first half of the lab. Across the
declared assays there are 1,529 admitted endpoint values, spread over five endpoint labels: AC50
706 (46.2 percent), IC50 429 (28.1), Ki 272 (17.8), EC50 69 (4.5), MIC 53 (3.5). The relation mix
covers 1,257 of those values with a stated qualifier: 832 equalities (66.2 percent), 406 greater-
than bounds (32.3), 4 less-than bounds and 15 with no stated qualifier. The confidence score
reaches 100 for 0.2 percent of values and sits at zero for 32.1 percent, with a median of 23.

That mix is the first thing a reader should notice. Almost a third of the recorded relations are
bounds rather than measurements, and a bound states a side and not a magnitude, so treating it as
a number overstates what the archive says.

The second half reads each assay's own record. For every declared assay the lab prints the
archived endpoint and its direction, the row counts before and after admission, the relation mix
within that assay, the replicate structure the archived protocol declares, the control regime the
protocol declares, the reference wells it names, and the normalisation equation in the archive's
own words. Where the archive's equation puts its positive reference at 100 and its negative
reference at 0, the lab says so and calls the scale a zero-to-hundred scale.

The curve check then recomputes what the archived equation produced. The protocol fixes the
tolerance at 5 points, and the check reports, for the development and held-out points separately,
how many curves land within tolerance, how many land within a factor of three, and the median and
worst absolute deviation. The archive's own recorded endpoint values are used as the reference for
the comparison, and the fit mode is stated for each assay.

The compound split is a stability check, not an evaluation. It partitions the compounds by a
deterministic parity of the seed and the compound identifier, so the same compound always lands in
the same half, and it lets a reader confirm that the cheap baseline does not move when the
compounds are divided differently. The protocol says explicitly that no predictive model, no
train-test evaluation and no held-out scoring belongs in this lab.

## Source terms

PubChem is a resource of the US National Library of Medicine. The retrieval route is the public
FTP archive and the exact URLs, member paths, byte lengths and CRC-32 values are recorded in the
protocol and re-checked on every run. NCBI's general policies page is the institutional reference
for reuse terms. This lab did not read a terms statement specific to the archived BioAssay
records, so the registry records those terms as unverified rather than asserting them here.

Original software in this repository is available under Apache-2.0 and the original prose under
CC BY 4.0. Third-party sources keep their own terms.

## Limitations

Six assays are not a sample of the archive. Nothing here estimates how relation qualifiers,
confidence scores or control regimes are distributed across PubChem BioAssay as a whole.

The admitted values are what the declared admission rule kept. A reader who changes the admission
rule gets a different cohort, and the protocol fixes the rule precisely so that this number is
attributable to one declared set rather than to an undocumented choice.

A missing control record is reported as a fact about the archive, not as evidence that the
experiment was performed without controls. The archive records what it records.

The curve check compares a recomputed curve against the endpoint values the archive itself
recorded, under a fixed tolerance. It is a check on the archive's internal consistency and on the
archive's own normalisation equation. It is not an assessment of the underlying experiment, and it
cannot detect an error that the archive made consistently in both the readings and the recorded
endpoints.
