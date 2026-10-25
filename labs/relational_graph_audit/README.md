# Relational graph audit

This CPU-only laboratory reads the committed AIDD Commons resource catalogue as a directed, typed graph. It counts declared relations, their source-record evidence, missing declarations that meet a stated candidate rule, and per-node degree. It makes no causal or mechanistic inference.

## Input and protocol

The input is the 232 YAML resource records in `catalog/resources/` in the local snapshot recomputed on 2026-10-25. The protocol declares the 10 allowed node kinds, the 9 observed relation types and the 232-node expectation for this snapshot. The graph interpretation, issued on 2026-10-23, remains frozen as the catalogue grows; the node-count binding and compact projection identify the current snapshot. The catalogue remains the only copy of the records. A relation points from the record that declares it to its target. Only evidence entries in that declaring record with `relations` in `supports` count as edge provenance.

An unordered pair is a candidate when its records share a task or a stage and no relation is declared in either direction. Candidate pairs are not added to the graph. Degree is incoming plus outgoing declared edge instances. An isolated record is one that declares no outgoing relation, even when an incoming edge exists. The inspector prints each node's kind and degree, each edge and its source evidence identifiers, isolated identifiers by kind, the aggregate counts and the records with the most candidate pairs.

## Reproduction

Mode is fresh independent computation over the frozen protocol and committed catalogue. Use the project's Python 3.11 environment with PyYAML. Run from the repository root. No network, download or accelerator is needed. The first three commands write nothing. The exporter writes only `summary.json` after every check passes.

```bash
.venv/bin/python labs/relational_graph_audit/run_lab.py check
.venv/bin/python labs/relational_graph_audit/inspect_relational_graph_audit.py show
.venv/bin/python labs/relational_graph_audit/inspect_relational_graph_audit.py check
.venv/bin/python labs/relational_graph_audit/export_summary.py
.venv/bin/python -m pytest labs/tests/relational_graph_audit -q
```

The committed computation on 2026-10-25 used Python 3.11.15 and PyYAML 6.0.3. It contains 232 nodes and 39 directed declared edges. All 39 have source-record evidence under the protocol, and 0 are unevidenced. The rule yields 10560 candidate pairs, and 196 records declare no outgoing relation. These are observations about this catalogue and the stated rule, not discovered scientific relations. A path through this resource graph is not a mechanism, and an absent declaration is not an experimentally established negative.

Original teaching code is Apache-2.0 and this prose is CC BY 4.0. Source records and linked materials retain their recorded licences and caveats.
