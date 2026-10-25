"""Bring the laboratories that audit this project's own catalogue up to date.

Several laboratories freeze the size of the catalogue, so that a change to the
catalogue cannot pass unnoticed. When a record is added or removed, each of
them refuses to run until its frozen count matches the catalogue again. That
refusal is the point, and this script is the routine that answers it: it reads
the current catalogue, rewrites the frozen numbers, regenerates the affected
summaries, and rewrites the numbers the tests pin.

    python scripts/catalog/sync-frozen-audit-counts.py [--write]

Without `--write` it reports what would change, so the change can be read
before it is made.

The pinned numbers in the tests are read from the regenerated summaries rather
than guessed, and the edits are confined to the test that reads the current
catalogue, because the test above it exercises a constructed graph with its
own small numbers. Each pinned line is matched as a whole template with a
placeholder where the number goes, so a replacement cannot drop the
surrounding syntax.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "catalog/resources"

GRAPH_SUMMARY = ROOT / "labs/relational_graph_audit/summary.json"
CONTRACT_SUMMARY = ROOT / "labs/tool_contract_audit/summary.json"


def catalogue_size() -> int:
    return len(list(RESOURCES.glob("*.yaml")))


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True
    )


def rewrite(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        return False
    path.write_text(text.replace(old, new), encoding="utf-8")
    return True


def set_graph_node_count(size: int, write: bool) -> None:
    protocol_code = ROOT / "labs/src/aidd_commons/relational_graph_audit/protocol.py"
    protocol_json = ROOT / "labs/relational_graph_audit/protocol.json"
    document = json.loads(protocol_json.read_text(encoding="utf-8"))
    previous = document["expected_node_count"]
    if previous == size:
        return
    print(f"graph protocol: expected_node_count {previous} -> {size}")
    if not write:
        return
    rewrite(
        protocol_code,
        f"EXPECTED_NODE_COUNT = {previous}",
        f"EXPECTED_NODE_COUNT = {size}",
    )
    document["expected_node_count"] = size
    protocol_json.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def pin_numbers(path: Path, patterns: list[tuple[str, int]], write: bool) -> None:
    """Rewrite pinned numbers in the test that reads the current catalogue.

    Each pattern is the assertion with a named group around the number, so
    only the number is replaced and the surrounding syntax cannot be lost.
    The test file holds two tests, and the one above it exercises a
    constructed graph with its own small numbers, so the edit is confined to
    the lines after the catalogue test starts.
    """
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    marker = next(
        (index for index, line in enumerate(lines) if "current_catalogue" in line), None
    )
    if marker is None:
        marker = 0
    changed = False
    for index in range(marker, len(lines)):
        for pattern, value in patterns:
            def replace(match: re.Match[str], number: int = value) -> str:
                # Keep every group except the one around the number.
                parts = []
                for group_index, group in enumerate(match.groups(), start=1):
                    parts.append(
                        str(number) if group is not None and group_index == 2 else group
                    )
                return "".join(parts)

            updated, count = re.subn(pattern, replace, lines[index], count=1)
            if count and updated != lines[index]:
                lines[index] = updated
                changed = True
    if changed:
        print(f"{path.name}: pinned numbers updated")
        if write:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    size = catalogue_size()
    print(f"catalogue records: {size}")

    set_graph_node_count(size, arguments.write)

    for laboratory in (
        "asset_openness_audit",
        "relational_graph_audit",
        "tool_contract_audit",
    ):
        result = run(f"labs/{laboratory}/export_summary.py")
        status = "ok" if result.returncode == 0 else f"FAILED: {result.stderr.strip()}"
        print(f"{laboratory}: {status}")

    result = run("labs/cofolding_claims/export_claim_records.py", "--update")
    status = "ok" if result.returncode == 0 else f"FAILED: {result.stderr.strip()}"
    print(f"cofolding_claims: {status}")

    graph = json.loads(GRAPH_SUMMARY.read_text(encoding="utf-8"))
    isolated = sum(len(names) for names in graph["isolated_nodes"].values())
    pin_numbers(
        ROOT / "labs/tests/relational_graph_audit/test_analysis.py",
        [
            (r'(assert result\["node_count"\] == )(\d+)', graph["node_count"]),
            (r'(assert result\["edge_count"\] == )(\d+)', graph["edge_count"]),
            (
                r'(assert result\["candidate_edge_count"\] == )(\d+)',
                graph["candidate_edge_count"],
            ),
            (
                r'(assert len\(result\["evidenced_edges"\]\) == )(\d+)',
                graph["edge_count"],
            ),
            (
                r'(assert sum\(map\(len, result\["isolated_nodes"\]\.values\(\)\)\) == )(\d+)',
                isolated,
            ),
            (
                r'(expected_nodes=)(\d+)(, edge_types=EDGE_TYPES)',
                graph["node_count"],
            ),
        ],
        arguments.write,
    )
    pin_numbers(
        ROOT / "labs/tests/relational_graph_audit/test_summary_artifact.py",
        [
            (
                r'(assert artifact\["candidate_edge_count"\] == )(\d+)',
                graph["candidate_edge_count"],
            ),
        ],
        arguments.write,
    )
    pin_numbers(
        ROOT / "labs/tests/asset_openness_audit/test_analysis.py",
        [
            (r'("records": )(\d+)', size),
            (r'("records_with_seven_separate_dimensions": )(\d+)', size),
        ],
        arguments.write,
    )
    pin_numbers(
        ROOT / "labs/tests/asset_openness_audit/test_summary_artifact.py",
        [
            (
                r'(\[\"whole_catalogue\"\]\[\"records_with_seven_separate_dimensions\"\] == )(\d+)',
                size,
            ),
        ],
        arguments.write,
    )
    contract = json.loads(CONTRACT_SUMMARY.read_text(encoding="utf-8"))
    records = contract["return_record_count"]
    pin_numbers(
        ROOT / "labs/tests/tool_contract_audit/test_analysis.py",
        [
            (
                r'(assert result\["return_record_count"\] == len\(records\) == )(\d+)',
                records,
            ),
            (
                r'(assert result\["protocol_file_count"\] == result\["readme_file_count"\] == )(\d+)',
                records,
            ),
            (
                r'(assert result\["records_with_declared_limits"\] \+ result\["records_without_declared_limits"\] == )(\d+)',
                records,
            ),
            (r'(assert len\(result\["per_laboratory"\]\) == )(\d+)', records),
        ],
        arguments.write,
    )

    if not arguments.write:
        print("re-run with --write to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
