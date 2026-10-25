"""Recompute and validate the small committed network summary."""

from __future__ import annotations

import json
import platform
import urllib.request
from collections.abc import Callable
from datetime import date
from http.client import IncompleteRead
from importlib import metadata
from pathlib import Path
from typing import Any, cast

from .analysis import DataContractError, audit_network
from .protocol import PROTOCOL_ID, SUMMARY_SCHEMA_VERSION, load_protocol

PACKAGE_NAME = "aidd-commons-labs"
DECLARED_PACKAGE_VERSION = "0.2.0rc1"
BOUNDARY = (
    "This is a relative binding free-energy network consistency audit, not an absolute "
    "binding free energy or an experimental affinity. A closed cycle does not establish "
    "that any edge estimate is correct or converged."
)


def package_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return DECLARED_PACKAGE_VERSION


def snapshot_path(cache_dir: Path, filename: str) -> Path:
    return cache_dir / filename


def download_snapshots(
    protocol_path: Path,
    cache_dir: Path,
    *,
    fetch: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    """Cache each archive only after its own structural validation."""
    protocol = load_protocol(protocol_path)
    downloader = fetch or _fetch
    reports: list[dict[str, Any]] = []
    for source in protocol["source"]["files"]:
        filename = source["name"]
        path = snapshot_path(cache_dir, filename)
        if path.is_file():
            payload = path.read_bytes()
            origin = "cached"
        else:
            url = protocol["source"]["retrieval_route"].replace("<file name>", filename)
            payload = downloader(url)
            origin = "fetched"
        audit_network(payload, source["system"], source["bytes"])
        if origin == "fetched":
            cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        reports.append(
            {"system": source["system"], "name": filename, "bytes": len(payload), "origin": origin}
        )
    return reports


def _fetch(url: str) -> bytes:
    last_error: OSError | IncompleteRead | None = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                return cast(bytes, response.read())
        except (OSError, IncompleteRead) as error:
            last_error = error
    raise DataContractError(f"snapshot download failed: {last_error}")


def build_summary(
    lab_dir: Path, cache_dir: Path, *, computed_on: str | None = None
) -> dict[str, Any]:
    protocol = load_protocol(lab_dir / "protocol.json")
    systems = []
    for source in protocol["source"]["files"]:
        path = snapshot_path(cache_dir, source["name"])
        if not path.is_file():
            raise DataContractError(f"missing cached archive for {source['system']}; run download")
        systems.append(audit_network(path.read_bytes(), source["system"], source["bytes"]))
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {
            "python": platform.python_version(),
            "aidd_commons_labs": package_version(),
        },
        "endpoint_kind": protocol["endpoint_rule"]["kind"],
        "boundary_statement": BOUNDARY,
        "enforced_rules": {
            "endpoint": protocol["endpoint_rule"]["pairing"],
            "cycle_tolerance": protocol["cycle_rule"]["tolerance"],
            "closure": protocol["cycle_rule"]["closure"],
        },
        "totals": {
            "systems": len(systems),
            "edges": sum(item["edge_count"] for item in systems),
            "estimates": sum(item["estimate_count"] for item in systems),
            "unestimated_unit_records": sum(item["unestimated_unit_records"] for item in systems),
            "cycles": sum(item["cycle_count"] for item in systems),
            "closed_cycles": sum(item["closed_cycle_count"] for item in systems),
            "failed_cycles": sum(item["failed_cycle_count"] for item in systems),
        },
        "systems": systems,
    }


def validate_summary(summary: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary schema version")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary protocol identifier")
    try:
        date.fromisoformat(summary["computed_on"])
    except (KeyError, TypeError, ValueError):
        failures.append("computation date")
    if summary.get("endpoint_kind") != protocol["endpoint_rule"]["kind"]:
        failures.append("endpoint kind")
    if summary.get("boundary_statement") != BOUNDARY:
        failures.append("boundary statement")
    rules = summary.get("enforced_rules")
    if rules != {
        "endpoint": protocol["endpoint_rule"]["pairing"],
        "cycle_tolerance": protocol["cycle_rule"]["tolerance"],
        "closure": protocol["cycle_rule"]["closure"],
    }:
        failures.append("enforced rules")
    software = summary.get("software")
    if not isinstance(software, dict) or not all(
        isinstance(software.get(key), str) and software[key]
        for key in ("python", "aidd_commons_labs")
    ):
        failures.append("software versions")
    systems = summary.get("systems")
    if not isinstance(systems, list) or len(systems) != len(protocol["source"]["files"]):
        return failures + ["system table"]
    expected_names = [item["system"] for item in protocol["source"]["files"]]
    if [
        item.get("system") if isinstance(item, dict) else None for item in systems
    ] != expected_names:
        failures.append("system order or identity")
    try:
        for system in systems:
            if system["edge_count"] != system["solvent_edges"] + system["complex_edges"]:
                failures.append(f"{system['system']}: edge count")
            if (
                system["binding_edges"] != system["solvent_edges"]
                or system["binding_edges"] != system["complex_edges"]
            ):
                failures.append(f"{system['system']}: leg pairing")
            if (
                system["estimate_count"]
                != system["solvent_estimates"] + system["complex_estimates"]
            ):
                failures.append(f"{system['system']}: estimate count")
            distribution = system["estimates_per_edge"]
            if (
                sum(distribution.values()) != system["edge_count"]
                or sum(int(count) * frequency for count, frequency in distribution.items())
                != system["estimate_count"]
            ):
                failures.append(f"{system['system']}: estimates-per-edge distribution")
            if system["selected_repeat_estimates"] != 3 * system["edge_count"]:
                failures.append(f"{system['system']}: selected repeat count")
            if system["unestimated_unit_records"] < 0:
                failures.append(f"{system['system']}: unestimated unit records")
            cycles = system["cycles"]
            failed = [item for item in cycles if not item["closed"]]
            if (
                system["cycle_count"] != len(cycles)
                or system["closed_cycle_count"] != (len(cycles) - len(failed))
                or system["failed_cycle_count"] != len(failed)
            ):
                failures.append(f"{system['system']}: cycle counts")
            if system["failed_cycles"] != [
                {
                    "name": item["name"],
                    "discrepancy_size_kcal_mol": item["discrepancy_size_kcal_mol"],
                }
                for item in failed
            ]:
                failures.append(f"{system['system']}: failed-cycle disclosure")
            for cycle in cycles:
                should_close = abs(cycle["signed_sum_kcal_mol"]) <= cycle["tolerance_kcal_mol"]
                if cycle["closed"] != should_close:
                    failures.append(f"{system['system']}: inconsistent cycle misclassified")
                if cycle["discrepancy_size_kcal_mol"] != abs(cycle["signed_sum_kcal_mol"]):
                    failures.append(f"{system['system']}: discrepancy size")
        totals = summary["totals"]
        for field, source in (
            ("edges", "edge_count"),
            ("estimates", "estimate_count"),
            ("unestimated_unit_records", "unestimated_unit_records"),
            ("cycles", "cycle_count"),
            ("closed_cycles", "closed_cycle_count"),
            ("failed_cycles", "failed_cycle_count"),
        ):
            if totals[field] != sum(system[source] for system in systems):
                failures.append(f"total {field}")
        if totals["systems"] != len(systems):
            failures.append("total systems")
    except (KeyError, TypeError, ValueError):
        failures.append("missing or invalid count field")
    return failures


def check_summary(lab_dir: Path, cache_dir: Path, artifact: Path) -> list[str]:
    protocol = load_protocol(lab_dir / "protocol.json")
    try:
        committed = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return [f"summary cannot be read: {error}"]
    if not isinstance(committed, dict):
        return ["summary must be an object"]
    failures = validate_summary(committed, protocol)
    recomputed = build_summary(lab_dir, cache_dir, computed_on=committed.get("computed_on"))
    if committed != recomputed:
        failures.append("summary differs from cached source snapshot")
    return failures


def export_summary(lab_dir: Path, cache_dir: Path, output: Path) -> dict[str, Any]:
    protocol = load_protocol(lab_dir / "protocol.json")
    summary = build_summary(lab_dir, cache_dir)
    failures = validate_summary(summary, protocol)
    if failures:
        raise DataContractError("; ".join(failures))
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary
