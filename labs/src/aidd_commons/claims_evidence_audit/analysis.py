"""Separate evidence states, independent readings, and recorded claim gates."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .protocol import STATES

DEPTH_RANK = {
    "absent": 0,
    "mentioned": 1,
    "explained": 2,
    "worked": 3,
    "executable": 4,
    "assessed": 5,
}


class AuditError(ValueError):
    """A source or result violates a declared audit invariant."""


def classify_cell(
    record: dict[str, Any], cell: dict[str, Any], root: Path, *, is_default: bool = False
) -> tuple[str, str | None]:
    """Return exactly one state and, for unsupported claims, the first reason."""
    references = cell.get("evidence")
    if is_default and cell.get("depth") == "unverified" and references == []:
        return "unresolved-field", None
    if not isinstance(references, list) or not references:
        return "unsupported-claim", "no evidence reference"
    entries = {entry["id"]: entry for entry in record["evidence"]}
    for reference in references:
        if not isinstance(reference, str) or reference not in entries:
            return "unsupported-claim", f"undeclared evidence: {reference}"
        entry = entries[reference]
        if "repository_path" in entry:
            repository_path = entry["repository_path"]
            if not isinstance(repository_path, str) or not repository_path:
                return "unsupported-claim", f"invalid repository path: {reference}"
            candidate = (root / repository_path).resolve()
            if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
                return "unsupported-claim", f"missing repository file: {reference}"
        elif not isinstance(entry.get("url"), str) or not entry["url"]:
            return "unsupported-claim", f"evidence has no source: {reference}"
    if cell.get("depth") == "unverified":
        return "bounded-inference", None
    return "direct-observation", None


def bounds(depth: str, threshold: str) -> tuple[int, int]:
    if depth == "unverified":
        return 0, 1
    covered = int(DEPTH_RANK[depth] >= DEPTH_RANK[threshold])
    return covered, covered


def ordinal_reading(reading: dict[str, Any]) -> str:
    if reading["depth"] == "assessed" and reading.get("run_basis") == "none":
        return "worked"
    return str(reading["depth"])


def analyze(bundle: dict[str, Any], protocol: dict[str, Any], root: Path) -> dict[str, Any]:
    providers = bundle["providers"]
    taxonomy = bundle["taxonomy"]
    reading = bundle["reading"]
    comparison = bundle["comparison"]
    tracks = taxonomy.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise AuditError("taxonomy has no tracks")
    track_topics: dict[str, list[str]] = {}
    for track in tracks:
        if not isinstance(track, dict) or not isinstance(track.get("topics"), list):
            raise AuditError("invalid taxonomy track")
        track_topics[track["id"]] = [topic["id"] for topic in track["topics"]]
    all_topics = [topic for topics in track_topics.values() for topic in topics]
    if len(all_topics) != len(set(all_topics)):
        raise AuditError("taxonomy repeats a topic")
    track_id = protocol["track"]["id"]
    topic_ids = protocol["track"]["topic_ids"]
    if track_topics.get(track_id) != topic_ids:
        raise AuditError("declared track topics differ from taxonomy")
    if reading.get("system_id") != "aidd-commons" or not isinstance(reading.get("readings"), list):
        raise AuditError("independent reading has wrong system or no readings")
    reading_by_topic = {row["topic_id"]: row for row in reading["readings"]}
    if len(reading_by_topic) != len(reading["readings"]) or set(reading_by_topic) != set(
        all_topics
    ):
        raise AuditError("independent reading does not cover taxonomy once")

    coverage: dict[str, dict[str, dict[str, Any]]] = {}
    direct = 0
    per_provider: dict[str, dict[str, int]] = {}
    for identifier, provider in providers.items():
        rows = {cell["topic_id"]: cell for cell in provider["coverage"]}
        if not set(rows) <= set(all_topics):
            raise AuditError(f"unknown coverage topic: {identifier}")
        for cell in provider["coverage"]:
            if cell.get("depth") not in (*DEPTH_RANK, "unverified"):
                raise AuditError(f"invalid depth: {identifier}/{cell['topic_id']}")
        coverage[identifier] = rows
        direct += len(rows)
        per_provider[identifier] = {
            "direct_cells": len(rows),
            "default_unverified_cells": len(all_topics) - len(rows),
        }
    total = len(providers) * len(all_topics)
    observations = comparison.get("observations")
    if not isinstance(observations, dict) or observations != {
        "direct_cells": direct,
        "default_unverified_cells": total - direct,
        "total_cells": total,
    }:
        raise AuditError("comparison record declared cell counts differ from source records")
    declared_taxonomy = comparison.get("taxonomy")
    if not isinstance(declared_taxonomy, dict) or (
        declared_taxonomy.get("tracks") != len(tracks)
        or declared_taxonomy.get("topics") != len(all_topics)
    ):
        raise AuditError("comparison record declared taxonomy counts differ")
    summaries = {
        row["provider_id"]: row
        for row in comparison.get("summaries", [])
        if row.get("threshold") == "explained"
    }
    for identifier, counts in per_provider.items():
        row = summaries.get(identifier)
        if row is None or any(row.get(key) != value for key, value in counts.items()):
            raise AuditError(f"comparison record declared provider counts differ: {identifier}")
    exported_rows = comparison.get("rows")
    if not isinstance(exported_rows, list) or len(exported_rows) != total:
        raise AuditError("comparison record row count differs")
    row_index = {(row["provider_id"], row["topic_id"]): row for row in exported_rows}
    if len(row_index) != total:
        raise AuditError("comparison record repeats or omits a provider-topic cell")
    for identifier, provider in providers.items():
        for topic in all_topics:
            direct_cell = coverage[identifier].get(topic)
            cell = direct_cell or provider["coverage_default"]
            row = row_index.get((identifier, topic))
            if (
                row is None
                or row.get("depth") != cell["depth"]
                or row.get("coverage_origin") != ("direct" if direct_cell else "default")
            ):
                raise AuditError(f"comparison row differs from source: {identifier}/{topic}")
            if [entry.get("evidence_id") for entry in row.get("evidence", [])] != cell["evidence"]:
                raise AuditError(f"comparison evidence differs from source: {identifier}/{topic}")

    cells: list[dict[str, Any]] = []
    unsupported: list[dict[str, str]] = []
    state_counts: dict[str, dict[str, int]] = {}
    for identifier in protocol["provider_ids"]:
        provider = providers[identifier]
        counter: Counter[str] = Counter()
        for topic in topic_ids:
            direct_cell = coverage[identifier].get(topic)
            cell = direct_cell or provider["coverage_default"]
            state, reason = classify_cell(provider, cell, root, is_default=direct_cell is None)
            counter[state] += 1
            cells.append(
                {
                    "provider_id": identifier,
                    "topic_id": topic,
                    "depth": cell["depth"],
                    "evidence": cell["evidence"],
                    "note": cell["note"],
                    "state": state,
                }
            )
            if reason is not None:
                unsupported.append({"provider_id": identifier, "topic_id": topic, "reason": reason})
        state_counts[identifier] = {state: counter[state] for state in STATES}

    disagreements: list[dict[str, str]] = []
    for topic in topic_ids:
        recorded = coverage["aidd-commons"].get(
            topic, providers["aidd-commons"]["coverage_default"]
        )
        independent = ordinal_reading(reading_by_topic[topic])
        recorded_depth = recorded["depth"]
        if recorded_depth == "unverified":
            continue
        difference = DEPTH_RANK[independent] - DEPTH_RANK[recorded_depth]
        if difference:
            disagreements.append(
                {
                    "topic_id": topic,
                    "recorded_depth": recorded_depth,
                    "independent_depth": independent,
                    "direction": "independent-deeper"
                    if difference > 0
                    else "independent-shallower",
                }
            )

    source_claims = comparison.get("claims")
    if not isinstance(source_claims, dict):
        raise AuditError("comparison record has no claims")
    self_rows = coverage["aidd-commons"]
    self_explained = sum(
        bounds(
            self_rows.get(t, providers["aidd-commons"]["coverage_default"])["depth"], "explained"
        )[0]
        for t in all_topics
    )
    self_worked = sum(
        bounds(self_rows.get(t, providers["aidd-commons"]["coverage_default"])["depth"], "worked")[
            0
        ]
        for t in all_topics
    )
    external_explained = max(
        sum(
            bounds(coverage[p].get(t, providers[p]["coverage_default"])["depth"], "explained")[1]
            for t in all_topics
        )
        for p in providers
        if p != "aidd-commons"
    )
    external_worked = max(
        sum(
            bounds(coverage[p].get(t, providers[p]["coverage_default"])["depth"], "worked")[1]
            for t in all_topics
        )
        for p in providers
        if p != "aidd-commons"
    )
    runnable_tracks = sum(
        any(
            coverage["aidd-commons"].get(t, {}).get("depth") in ("executable", "assessed")
            for t in topics
        )
        for topics in track_topics.values()
    )
    real_data_tracks = sum(
        any(
            coverage["aidd-commons"].get(t, {}).get("depth") in ("executable", "assessed")
            and coverage["aidd-commons"][t].get("run_basis") == "real-data"
            for t in topics
        )
        for topics in track_topics.values()
    )
    comprehensive = source_claims["most_comprehensive"]
    detailed = source_claims["most_detailed"]
    expected_claim_values = {
        "most_comprehensive": {
            "self_lower_at_explained": self_explained,
            "strongest_external_upper_at_explained": external_explained,
            "bound_condition_satisfied": self_explained > external_explained,
        },
        "most_detailed": {
            "self_lower_at_worked": self_worked,
            "strongest_external_upper_at_worked": external_worked,
            "executable_or_assessed_self_tracks": runnable_tracks,
            "real_data_executable_or_assessed_self_tracks": real_data_tracks,
            "bound_condition_satisfied": runnable_tracks >= detailed["required_self_tracks"]
            and self_worked > external_worked,
        },
    }
    failures: list[str] = []
    for key, expected in expected_claim_values.items():
        for field, value in expected.items():
            if source_claims[key].get(field) != value:
                failures.append(f"recorded claim value differs: {key}.{field}")
    claims = {
        key: {
            "status": source_claims[key]["status"],
            "bound_condition_satisfied": source_claims[key]["bound_condition_satisfied"],
            "bound_condition_measured": not any(
                item.startswith(f"recorded claim value differs: {key}.") for item in failures
            ),
            "measured_values": {
                field: source_claims[key][field]
                for field in expected_claim_values[key]
                if field != "bound_condition_satisfied"
            },
            "condition": protocol["claims"][key]["condition"],
            "correction_window_condition": protocol["claims"][key]["correction_window"],
            "correction_window_status": comprehensive["correction_window_status"],
        }
        for key in ("most_comprehensive", "most_detailed")
    }
    return {
        "cells": cells,
        "state_counts": state_counts,
        "unsupported_claims": unsupported,
        "disagreements": disagreements,
        "claims": claims,
        "source_counts": observations,
        "failures": failures,
    }


def check_invariants(result: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    failures = list(result["failures"])
    for row in result["unsupported_claims"]:
        failures.append(f"unsupported {row['provider_id']}/{row['topic_id']}: {row['reason']}")
    expected_cells = len(protocol["provider_ids"]) * len(protocol["track"]["topic_ids"])
    if len(result["cells"]) != expected_cells:
        failures.append("selected cells do not cover the declared provider-topic cross product")
    for identifier, counts in result["state_counts"].items():
        if sum(counts.values()) != len(protocol["track"]["topic_ids"]):
            failures.append(f"state counts do not cover every selected cell: {identifier}")
    if any(row["direction"] == "independent-shallower" for row in result["disagreements"]):
        failures.append("own row exceeds the independent reading")
    return failures
