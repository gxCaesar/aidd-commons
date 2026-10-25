"""Apply the protocol's literal vocabulary to paired topic records."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .protocol import FAMILIES, STATES, AuditError


def _contains(text: str, phrases: list[str]) -> bool:
    lowered = text.casefold()
    return any(phrase.casefold() in lowered for phrase in phrases)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.!?;]+", text.casefold()) if part.strip()]


def missing_families(text: str, protocol: dict[str, Any]) -> list[str]:
    cues = protocol["falsifier_rule"]["missing_cues"]
    generic = protocol["falsifier_rule"]["generic_only"]
    found: set[str] = set()
    for sentence in _sentences(text):
        if sentence in generic or not _contains(sentence, cues):
            continue
        for family, words in protocol["missing_measurement_families"].items():
            if _contains(sentence, words):
                found.add(family)
    return [family for family in FAMILIES if family in found]


def names_falsifier(note: str, reason: str, protocol: dict[str, Any]) -> bool:
    phrases = protocol["falsifier_rule"]["discriminating_phrases"]
    return bool(
        missing_families(note, protocol) or missing_families(reason, protocol)
    ) or _contains(f"{note} {reason}", phrases)


def _ordinal_reading(row: dict[str, Any]) -> str:
    if row["depth"] == "assessed" and row.get("run_basis", "none") == "none":
        return "worked"
    return str(row["depth"])


def classify(
    note: str,
    reason: str,
    self_depth: str,
    reading: dict[str, Any],
    protocol: dict[str, Any],
    reviewed_scope: str = "",
) -> str:
    rule = protocol["state_rule"]
    later_raise = _contains(note, rule["later_raise_phrases"])
    if _contains(note, rule["lowered_phrases"]) and not later_raise:
        depths = protocol["depth_order"]
        if depths.index(self_depth) > depths.index(_ordinal_reading(reading)):
            raise AuditError("a lowered topic still exceeds its independent reading")
        return "lowered by a reading"
    if _contains(note, rule["held_phrases"]) and not later_raise:
        return "held by a reading"
    if _contains(note, rule["measurement_subjects"]) and _contains(note, rule["measurement_verbs"]):
        return "settled by measurement"
    if (
        _contains(reason, rule["closed_reason_phrases"])
        and _contains(reviewed_scope, ["measured", "lab", "inspector", "command"])
        and _contains(note, rule["bounded_decision_phrases"])
    ):
        return "settled by measurement"
    if note.strip() and reason.strip():
        return "open"
    if not note.strip() and not reason.strip():
        return "unexamined"
    raise AuditError("a topic has only one of its paired explanations")


def analyze(bundle: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    self_record = bundle["self_record"]
    reading = bundle["independent_reading"]
    taxonomy = bundle["taxonomy"]
    if self_record.get("id") != "aidd-commons" or reading.get("system_id") != "aidd-commons":
        raise AuditError("source identities differ")
    if (
        not isinstance(self_record.get("caveats"), list)
        or not isinstance(reading.get("reviewer"), str)
        or not isinstance(reading.get("isolation"), str)
    ):
        raise AuditError("record context is missing")
    tracks = taxonomy.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise AuditError("taxonomy tracks are missing")
    topics = [topic["id"] for track in tracks for topic in track["topics"]]
    if len(topics) != len(set(topics)):
        raise AuditError("taxonomy has duplicate topic IDs")
    own_rows = self_record.get("coverage")
    reading_rows = reading.get("readings")
    if not isinstance(own_rows, list) or not isinstance(reading_rows, list):
        raise AuditError("coverage or reading list is missing")
    own = {row["topic_id"]: row for row in own_rows}
    independent = {row["topic_id"]: row for row in reading_rows}
    if (
        len(own) != len(own_rows)
        or len(independent) != len(reading_rows)
        or set(own) != set(topics)
        or set(independent) != set(topics)
    ):
        raise AuditError("records must cover every taxonomy topic once")
    by_state: dict[str, list[str]] = {state: [] for state in STATES}
    open_with: list[str] = []
    open_without: list[str] = []
    held_without: list[str] = []
    note_missing: list[str] = []
    reason_missing: list[str] = []
    by_family: dict[str, list[str]] = {family: [] for family in FAMILIES}
    lowered: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for topic in topics:
        own_row, review_row = own[topic], independent[topic]
        note, reason = own_row.get("note"), review_row.get("reason")
        if not isinstance(note, str) or not isinstance(reason, str):
            raise AuditError(f"topic lacks note or reason: {topic}")
        if (
            own_row.get("depth") not in protocol["depth_order"]
            or review_row.get("depth") not in protocol["depth_order"]
        ):
            raise AuditError(f"invalid depth: {topic}")
        reviewed_scope = own_row.get("reviewed_scope", "")
        if not isinstance(reviewed_scope, str):
            raise AuditError(f"topic lacks reviewed scope: {topic}")
        state = classify(note, reason, own_row["depth"], review_row, protocol, reviewed_scope)
        by_state[state].append(topic)
        nf, rf = missing_families(note, protocol), missing_families(reason, protocol)
        if nf:
            note_missing.append(topic)
        if rf:
            reason_missing.append(topic)
        for family in set(nf) | set(rf):
            by_family[family].append(topic)
        has_falsifier = names_falsifier(note, reason, protocol)
        if state == "open":
            (open_with if has_falsifier else open_without).append(topic)
        elif state == "held by a reading" and not has_falsifier:
            held_without.append(topic)
        if _contains(note, protocol["state_rule"]["lowered_phrases"]):
            lowered.append({"topic_id": topic, "names_missing": has_falsifier})
        rows.append(
            {
                "topic_id": topic,
                "state": state,
                "names_falsifier": has_falsifier,
                "note_families": nf,
                "reason_families": rf,
                "note": note,
                "reason": reason,
                "self_depth": own_row["depth"],
                "reading": review_row,
                "reviewed_scope": reviewed_scope,
            }
        )
    return {
        "topic_count": len(topics),
        "state_topics": by_state,
        "state_counts": {state: len(items) for state, items in by_state.items()},
        "open_with_falsifier": open_with,
        "open_without_falsifier": open_without,
        "held_without_falsifier": held_without,
        "missing_measurement": {
            "notes": {"count": len(note_missing), "topics": note_missing},
            "reasons": {"count": len(reason_missing), "topics": reason_missing},
            "families": {
                family: {"count": len(by_family[family]), "topics": by_family[family]}
                for family in FAMILIES
            },
        },
        "lowered_topics": lowered,
        "rows": rows,
    }


def check_invariants(result: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    states = result["state_topics"]
    if sum(map(len, states.values())) != result["topic_count"]:
        failures.append("state partition does not cover taxonomy")
    if len({topic for topics in states.values() for topic in topics}) != result["topic_count"]:
        failures.append("state partition repeats a topic")
    rows = {row["topic_id"]: row for row in result["rows"]}
    for topic, row in rows.items():
        if row["state"] != classify(
            row["note"],
            row["reason"],
            row["self_depth"],
            row["reading"],
            protocol,
            row["reviewed_scope"],
        ):
            failures.append(f"question state contradicts the protocol: {topic}")
        if row["names_falsifier"] != names_falsifier(row["note"], row["reason"], protocol):
            failures.append(f"falsifier label contradicts the protocol: {topic}")
        if row["note_families"] != missing_families(row["note"], protocol) or row[
            "reason_families"
        ] != missing_families(row["reason"], protocol):
            failures.append(f"missing-measurement families contradict the protocol: {topic}")
    expected_with = [topic for topic in states["open"] if rows[topic]["names_falsifier"]]
    expected_without = [topic for topic in states["open"] if not rows[topic]["names_falsifier"]]
    if (
        result["open_with_falsifier"] != expected_with
        or result["open_without_falsifier"] != expected_without
    ):
        failures.append("open-question falsifier labels contradict the audited rows")
    if set(result["open_with_falsifier"]) & set(result["open_without_falsifier"]):
        failures.append("an open question has both falsifier labels")
    expected_held_without = [
        topic for topic in states["held by a reading"] if not rows[topic]["names_falsifier"]
    ]
    if result["held_without_falsifier"] != expected_held_without:
        failures.append("held-question falsifier labels contradict the audited rows")
    expected_lowered = [
        {"topic_id": row["topic_id"], "names_missing": row["names_falsifier"]}
        for row in result["rows"]
        if _contains(row["note"], protocol["state_rule"]["lowered_phrases"])
    ]
    if result["lowered_topics"] != expected_lowered:
        failures.append("historical lowering inventory differs")
    for field, key in (("notes", "note_families"), ("reasons", "reason_families")):
        expected = [row["topic_id"] for row in result["rows"] if row[key]]
        entry = result["missing_measurement"][field]
        if entry["topics"] != expected or entry["count"] != len(expected):
            failures.append(f"{field} missing-measurement inventory differs")
    for family in FAMILIES:
        expected = [
            row["topic_id"]
            for row in result["rows"]
            if family in row["note_families"] or family in row["reason_families"]
        ]
        entry = result["missing_measurement"]["families"][family]
        if entry["topics"] != expected or entry["count"] != len(expected):
            failures.append(f"missing family inventory differs: {family}")
    if Counter(result["state_counts"]) != Counter(
        {key: len(value) for key, value in states.items()}
    ):
        failures.append("state counts differ from topic lists")
    return failures
