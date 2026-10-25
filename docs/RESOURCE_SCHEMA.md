# Resource schema

Each file under `catalog/resources/` is one resource record. The validator reads
either one YAML file or a directory of `.yaml`/`.yml` files and validates all
relations after every record has loaded.

## Required fields

```yaml
id: stable-lowercase-kebab-case
name: Human-readable name
kind: model-or-dataset-category
summary: Short source-grounded description
canonical_url: https://example.org/canonical-page
identifiers: []
stages: []
modalities: []
tasks: []
relations: []
status:
  value: unverified
access_level:
  value: unverified
openness:
  inference_code: { value: unverified }
  training_code: { value: unverified }
  weights: { value: unverified }
  architecture: { value: unverified }
  data_recipe: { value: unverified }
  training_data: { value: unverified }
  evaluation_code: { value: unverified }
licenses: []
evidence:
  - id: metadata-source
    url: https://example.org/source
    label: Source for the displayed metadata
    supports: [name, kind, summary]
caveats: []
acknowledgements: []
last_verified: "2026-09-04"
```

`id`, relation `type`, and relation `target` use lowercase kebab-case. A
relation target must match an `id` in the fully loaded catalog. All URLs use
HTTPS. `last_verified` is an ISO calendar date and must not be after the
validator date.

## Claim evidence

`status.value` is one of `active`, `legacy`, `superseded`, `unmaintained`,
`withdrawn`, or `unverified`. `access_level.value` is one of `open_source`,
`open_weights`, `source_available`, `research_only`, `gated`, `api_only`,
`closed`, or `unverified`.

Every openness dimension has one of `available`, `not_available`,
`not_applicable`, or `unverified`. `unverified` records that no claim is made.
All other status, access, and openness values require one or more evidence IDs.
Each licence record also requires evidence IDs. Every referenced ID must exist
in the same record's `evidence` list.

An evidence link must support the particular field, not merely mention the
resource. `training_data: available` requires an explicitly identified training
corpus or training-data release. A generic database query or download page alone
does not establish that claim. Conversely, a curated AI/ML training release can
support it even if no single model is named. Use `identifiers` and the resource
description to expose ordinary data-access routes. Unknown training fields do
not mean that database records are inaccessible.

Read the actual licence file or explicit resource terms, preserving amendments
and the covered asset. Do not infer software terms from Swagger metadata or apply
a software licence to imported data. When a README and LICENSE disagree, record
the conflict and link the licence file. Neither a working URL nor a current page
footer proves an actively maintained service; check dated retirement notices.

Every evidence entry has an explicit `supports` array. Its allowed values are
`name`, `kind`, `summary`, `identifiers`, `stages`, `modalities`, `tasks`,
`relations`, `caveats`, and `acknowledgements`. Each non-empty metadata field
or group must occur in at least one evidence entry's `supports` array. An
evidence entry cannot support a group that is empty in the same record. An
empty `supports` array is allowed for evidence used only by a direct status,
access, openness, or licence claim.

```yaml
status:
  value: active
  evidence: [official-page]
access_level:
  value: open_source
  evidence: [official-page]
openness:
  inference_code:
    value: available
    evidence: [official-page]
  training_code: { value: unverified }
  weights: { value: unverified }
  architecture: { value: unverified }
  data_recipe: { value: unverified }
  training_data: { value: unverified }
  evaluation_code: { value: unverified }
licenses:
  - name: Apache-2.0
    scope: code
    evidence: [official-page]
evidence:
  - id: official-page
    url: https://example.org/project
    label: Official project page
    supports: [name, kind, summary]
```

`identifiers` contains objects with `scheme`, `value`, and optional HTTPS
`url`. `relations` contains objects with `type` and `target`. `caveats` and
`acknowledgements` are lists of non-empty strings.

Use linked identifiers for useful additional entry points: `paper`,
`documentation`, `source-code`, `project-homepage`, `dataset`, or
`model-weights`. Record a primary source that establishes the link under
`evidence` with `supports: [identifiers]`. Keep version-specific papers and
assets separate. A link does not establish access or licence permissions.
The Atlas card opens `canonical_url`; the detail page collects all distinct
canonical, identifier and evidence URLs under **Resource links**.

## Commands and generated data

```bash
pnpm catalog:validate
pnpm catalog:build
```

The validator accepts an optional YAML file or directory and `--today
YYYY-MM-DD`. The exporter accepts the same input, plus `--output DIRECTORY`.
Without options it writes ID-sorted, timestamp-free files to
`site/public/data/`:

- `resources.v1.json`: complete resource records;
- `resources.v1.csv`: complete records with structured values JSON-encoded in
  CSV cells;
- `openness.v1.json`: `{ id, openness, evidence }` records, with only the
  evidence referenced by openness claims.

Validation errors identify the input file and schema field. Contract-only
example records belong under `tests/catalog/fixtures/`; canonical catalog
records must carry source-linked public metadata.
