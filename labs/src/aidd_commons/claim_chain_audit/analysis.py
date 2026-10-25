"""Resolve topic links and measure the weakest evidence chain."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .protocol import BOUNDARY, DEPTH_ORDER, ROLES

DEPTH_RANK = {name: index for index, name in enumerate(DEPTH_ORDER)}
LINK_STATES = (*DEPTH_ORDER, "unresolved")


class AuditError(ValueError):
    """A source or claimed result violates the audit contract."""


def _index(rows: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise AuditError(f"{label} must be a list")
    found: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(key), str):
            raise AuditError(f"invalid {label} entry")
        identifier = row[key]
        if identifier in found:
            raise AuditError(f"duplicate {label} identifier: {identifier}")
        found[identifier] = row
    return found


def load_records(root: Path, protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Read only the three named committed YAML sources."""
    records: dict[str, dict[str, Any]] = {}
    for name, declaration in protocol["sources"].items():
        path = root / declaration["path"]
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise AuditError(f"cannot read {name}") from error
        if not isinstance(value, dict):
            raise AuditError(f"{name} must contain an object")
        records[name] = value
    if records["self_record"].get("id") != "aidd-commons":
        raise AuditError("wrong self record")
    if records["independent_reading"].get("system_id") != "aidd-commons":
        raise AuditError("wrong independent reading")
    return records


def effective_depth(depth: Any, run_basis: Any) -> str:
    if depth not in DEPTH_RANK:
        raise AuditError(f"invalid depth: {depth}")
    if run_basis not in (None, "none", "authored", "real-data"):
        raise AuditError(f"invalid run basis: {run_basis}")
    if depth == "assessed" and run_basis in (None, "none"):
        return "worked"
    return str(depth)


def licence(depth: str, run_basis: str) -> str:
    if depth == "absent":
        return "No coverage found in the reviewed material"
    if depth == "mentioned":
        return "A mention or link only"
    if depth == "explained":
        return "An explanation of the topic"
    if depth == "worked":
        return "A worked case or written exercise, not a measurement"
    if depth == "executable":
        return f"A runnable task over {run_basis} inputs only"
    return f"An assessed runnable task over {run_basis} inputs only"


def _taxonomy_topics(taxonomy: dict[str, Any]) -> set[str]:
    tracks = taxonomy.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise AuditError("taxonomy has no tracks")
    topics: set[str] = set()
    for track in tracks:
        if not isinstance(track, dict):
            raise AuditError("invalid taxonomy track")
        for topic_id in _index(track.get("topics"), "id", "taxonomy topic"):
            if topic_id in topics:
                raise AuditError(f"duplicate taxonomy topic: {topic_id}")
            topics.add(topic_id)
    return topics


def _link(
    topic_id: str,
    role: str,
    coverage: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    readings: dict[str, dict[str, Any]],
    root: Path,
) -> dict[str, Any]:
    if topic_id not in coverage or topic_id not in readings:
        raise AuditError(f"missing topic record: {topic_id}")
    cell = coverage[topic_id]
    reference_ids = cell.get("evidence")
    if not isinstance(reference_ids, list) or any(not isinstance(x, str) for x in reference_ids):
        raise AuditError(f"invalid evidence list: {topic_id}")
    if len(reference_ids) != len(set(reference_ids)):
        raise AuditError(f"duplicate evidence reference: {topic_id}")
    opened = 0
    for reference in reference_ids:
        if reference not in evidence:
            raise AuditError(f"undeclared evidence: {topic_id}/{reference}")
        entry = evidence[reference]
        access = entry.get("access")
        if not isinstance(access, str):
            raise AuditError(f"missing evidence access: {reference}")
        if access == "opened":
            opened += 1
            repository_path = entry.get("repository_path")
            if not isinstance(repository_path, str) or not repository_path:
                raise AuditError(f"opened evidence lacks repository path: {reference}")
            target = (root / repository_path).resolve()
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                raise AuditError(f"opened evidence file missing: {reference}")
    raw_depth = cell.get("depth")
    basis = cell.get("run_basis", "none")
    self_depth = effective_depth(raw_depth, basis)
    reading = readings[topic_id]
    reading_depth = effective_depth(reading.get("depth"), reading.get("run_basis", "none"))
    if not opened:
        state = "unresolved"
        link_licence = "No supported link; the evidence list has no opened entry"
    else:
        state = self_depth
        link_licence = licence(self_depth, basis)
    comparison = (
        "agree"
        if self_depth == reading_depth
        else "reading_shallower"
        if DEPTH_RANK[reading_depth] < DEPTH_RANK[self_depth]
        else "reading_deeper"
    )
    return {
        "topic_id": topic_id,
        "role": role,
        "evidence_ids": reference_ids,
        "opened_evidence_count": opened,
        "resolved": opened > 0,
        "self_depth": self_depth,
        "self_run_basis": basis,
        "state": state,
        "licence": link_licence,
        "reading_depth": reading_depth,
        "reading_run_basis": reading.get("run_basis", "none"),
        "comparison": comparison,
    }


def analyze(
    records: dict[str, dict[str, Any]], protocol: dict[str, Any], root: Path
) -> dict[str, Any]:
    topics = _taxonomy_topics(records["taxonomy"])
    coverage = _index(records["self_record"].get("coverage"), "topic_id", "self coverage")
    evidence = _index(records["self_record"].get("evidence"), "id", "self evidence")
    readings = _index(records["independent_reading"].get("readings"), "topic_id", "reading")
    chains = []
    for declaration in protocol["chains"]:
        topic_ids = declaration["topic_ids"]
        if any(topic_id not in topics for topic_id in topic_ids):
            raise AuditError(f"chain has topic absent from taxonomy: {declaration['id']}")
        links = [
            _link(topic_id, role, coverage, evidence, readings, root)
            for role, topic_id in zip(ROLES, topic_ids, strict=True)
        ]
        resolved = [link for link in links if link["resolved"]]
        unresolved = [link for link in links if not link["resolved"]]
        weakest = (
            unresolved[0]
            if unresolved
            else min(resolved, key=lambda link: DEPTH_RANK[link["state"]])
        )
        strongest_rank = max((DEPTH_RANK[link["state"]] for link in resolved), default=None)
        counts = Counter(link["state"] for link in links)
        comparisons = Counter(link["comparison"] for link in links)
        chains.append(
            {
                "id": declaration["id"],
                "links": links,
                "link_count": len(links),
                "link_state_counts": {state: counts[state] for state in LINK_STATES},
                "weakest_link": (
                    {"topic_id": weakest["topic_id"], "depth": weakest["state"]}
                    if weakest
                    else None
                ),
                "below_strongest_count": (
                    len(unresolved)
                    + sum(DEPTH_RANK[link["state"]] < strongest_rank for link in resolved)
                    if strongest_rank is not None
                    else 0
                ),
                "comparison_counts": {
                    state: comparisons[state]
                    for state in ("agree", "reading_shallower", "reading_deeper")
                },
                "supported_claim": len(resolved) == len(links),
                "claim_scope": "named-topic-material-only",
            }
        )
    return {"chains": chains, "boundary_statement": BOUNDARY, "rules": protocol["rules"]}


def check_invariants(result: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    """Recount reported values and refuse any unsupported or biological claim."""
    failures: list[str] = []
    if result.get("boundary_statement") != BOUNDARY or result.get("rules") != protocol["rules"]:
        failures.append("boundary or rules changed")
    reported = result.get("chains")
    if not isinstance(reported, list) or len(reported) != len(protocol["chains"]):
        return failures + ["chain inventory differs from protocol"]
    for chain, declared in zip(reported, protocol["chains"], strict=True):
        name = declared["id"]
        links = chain.get("links")
        if not isinstance(links, list) or len(links) != len(ROLES):
            failures.append(f"{name}: wrong link count")
            continue
        if chain.get("id") != name or [x.get("topic_id") for x in links] != declared["topic_ids"]:
            failures.append(f"{name}: links differ from protocol")
        if [x.get("role") for x in links] != list(ROLES):
            failures.append(f"{name}: roles differ from protocol")
        if chain.get("link_count") != len(links):
            failures.append(f"{name}: reported link count is wrong")
        for link in links:
            topic = link.get("topic_id")
            opened = link.get("opened_evidence_count")
            references = link.get("evidence_ids")
            if not isinstance(opened, int) or not isinstance(references, list):
                failures.append(f"{name}/{topic}: invalid evidence count")
                continue
            resolved = opened > 0
            if opened > len(references) or link.get("resolved") is not resolved:
                failures.append(f"{name}/{topic}: resolution disagrees with evidence")
            expected_state = link.get("self_depth") if resolved else "unresolved"
            if link.get("state") != expected_state:
                failures.append(f"{name}/{topic}: state disagrees with resolution")
            if link.get("state") not in LINK_STATES:
                failures.append(f"{name}/{topic}: invalid state")
            if (
                link.get("self_depth") not in DEPTH_RANK
                or link.get("reading_depth") not in DEPTH_RANK
            ):
                failures.append(f"{name}/{topic}: invalid depth")
                continue
            expected_comparison = (
                "agree"
                if link["self_depth"] == link["reading_depth"]
                else "reading_shallower"
                if DEPTH_RANK[link["reading_depth"]] < DEPTH_RANK[link["self_depth"]]
                else "reading_deeper"
            )
            if link.get("comparison") != expected_comparison:
                failures.append(f"{name}/{topic}: comparison is wrong")
            basis = link.get("self_run_basis")
            expected_licence = (
                licence(link["self_depth"], basis)
                if resolved
                else "No supported link; the evidence list has no opened entry"
            )
            if link.get("licence") != expected_licence:
                failures.append(f"{name}/{topic}: licence is wrong")
        states = Counter(link.get("state") for link in links)
        if chain.get("link_state_counts") != {state: states[state] for state in LINK_STATES}:
            failures.append(f"{name}: link state counts are wrong")
        if any(link.get("state") not in LINK_STATES for link in links):
            continue
        resolved_links = [link for link in links if link["state"] != "unresolved"]
        unresolved_links = [link for link in links if link["state"] == "unresolved"]
        weakest = (
            unresolved_links[0]
            if unresolved_links
            else min(resolved_links, key=lambda x: DEPTH_RANK[x["state"]])
        )
        expected_weakest = (
            {"topic_id": weakest["topic_id"], "depth": weakest["state"]} if weakest else None
        )
        if chain.get("weakest_link") != expected_weakest:
            failures.append(f"{name}: weakest link is wrong")
        strongest = max((DEPTH_RANK[x["state"]] for x in resolved_links), default=None)
        below = (
            len(unresolved_links) + sum(DEPTH_RANK[x["state"]] < strongest for x in resolved_links)
            if strongest is not None
            else 0
        )
        if chain.get("below_strongest_count") != below:
            failures.append(f"{name}: below-strongest count is wrong")
        comparisons = Counter(link.get("comparison") for link in links)
        expected_counts = {
            state: comparisons[state] for state in ("agree", "reading_shallower", "reading_deeper")
        }
        if chain.get("comparison_counts") != expected_counts:
            failures.append(f"{name}: comparison counts are wrong")
        if chain.get("supported_claim") is not all(x["resolved"] for x in links):
            failures.append(f"{name}: unresolved link reported as supported claim")
        if chain.get("claim_scope") != "named-topic-material-only":
            failures.append(f"{name}: biological or unbounded claim refused")
    return failures
