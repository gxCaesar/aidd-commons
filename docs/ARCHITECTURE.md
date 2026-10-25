# Architecture

## Repository layout

```text
site/       Astro and Starlight application
catalog/    Human-maintained YAML source registry
labs/       Reproducible Python labs and tests
report/     Living technical report sources
scripts/    Validation, export, and release tooling
tests/      Cross-cutting fixtures and checks
docs/       Project charter, architecture, and contributor documentation
```

`site/public/data/` and `public-release/` are generated. Editors change canonical source files, then validators generate deterministic web-facing artifacts.

## Data flow

```text
catalog/resources/*.yaml
          │
          ├── schema and evidence validation
          │
          └── generated resources.v1.json / resources.v1.csv / openness.v1.json
                                      │
                                      └── static Astro pages and client-side filters

site curriculum definitions ──> curriculum.v1.json ──> learning-path UI
labs results ──────────────────> reviewed summaries ──> lessons and report
```

The site has no account system or application backend. Filter state is encoded in query parameters. Optional learning progress remains in the browser under `aidd-commons:v1:progress`.

## Resource record

Each resource is stored in one YAML file and contains stable identity, type, summary, canonical URL, identifiers, pipeline stages, modalities, tasks, relations, lifecycle status, access level, multidimensional openness, licences, evidence, caveats, acknowledgements, and a last-verified date.

Lifecycle status and access level are separate. A discontinued open repository and an active closed service are therefore representable without collapsing distinct facts.

## Quality gates

The smallest useful checks run first:

1. schema and source-evidence validation;
2. unit tests for generators and labs;
3. TypeScript and Astro builds;
4. internal links and citations;
5. one CPU notebook execution;
6. browser and accessibility smoke tests;
7. a release-tree scan for private workflow material and unsupported licence claims.

Known-bad fixtures ensure the load-bearing validators actually reject malformed records, leakage-prone splits, broken links, and release contamination.

