"""Read OpenFE archives and audit a relative binding free-energy cycle basis."""

from __future__ import annotations

import bz2
import json
import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Any, cast


class DataContractError(ValueError):
    """An archive does not meet the declared source or endpoint contract."""


@dataclass(frozen=True)
class LegEdge:
    name: str
    kind: str
    a_key: str
    b_key: str
    a_label: str
    b_label: str
    mapping_key: str
    estimate_count: int
    unestimated_unit_count: int
    mean: float
    standard_error: float


@dataclass(frozen=True)
class BindingEdge:
    name: str
    a_key: str
    b_key: str
    a_label: str
    b_label: str
    mean: float
    standard_error: float


def _reference(value: Any, context: str) -> str:
    if not isinstance(value, dict) or not isinstance(value.get(":gufe-key:"), str):
        raise DataContractError(f"{context}: missing gufe reference")
    return cast(str, value[":gufe-key:"])


def _finite_quantity(value: Any, context: str, *, positive: bool = False) -> float:
    if not isinstance(value, dict) or value.get("unit") != "kilocalorie_per_mole":
        raise DataContractError(f"{context}: unsupported or missing unit")
    number = value.get("magnitude")
    if isinstance(number, bool) or not isinstance(number, (float, int)):
        raise DataContractError(f"{context}: missing magnitude")
    result = float(number)
    if not math.isfinite(result) or (positive and result <= 0):
        raise DataContractError(f"{context}: nonfinite or nonpositive magnitude")
    return result


def _repeat_estimate(records: list[tuple[float, float, int]]) -> tuple[float, float]:
    if len(records) != 3 or len({repeat for _, _, repeat in records}) != 3:
        raise DataContractError("each transformation needs three distinct repeat estimates")
    values = [value for value, _, _ in records]
    mean = math.fsum(values) / 3
    reported_sem = math.sqrt(math.fsum(error * error for _, error, _ in records)) / 3
    between_sem = math.sqrt(math.fsum((value - mean) ** 2 for value in values) / 6)
    return mean, max(reported_sem, between_sem)


def parse_archive(payload: bytes, *, expected_bytes: int | None = None) -> tuple[LegEdge, ...]:
    """Follow archive references instead of inferring edges from result names."""
    if expected_bytes is not None and len(payload) != expected_bytes:
        raise DataContractError(f"archive byte length {len(payload)} differs from {expected_bytes}")
    try:
        pairs = json.loads(bz2.decompress(payload))
    except (OSError, EOFError, ValueError, UnicodeError) as error:
        raise DataContractError("archive cannot be decompressed and parsed") from error
    if not isinstance(pairs, list) or not all(
        isinstance(item, list)
        and len(item) == 2
        and isinstance(item[0], str)
        and isinstance(item[1], dict)
        for item in pairs
    ):
        raise DataContractError("archive must be a list of keyed objects")
    objects = dict(pairs)
    if len(objects) != len(pairs):
        raise DataContractError("duplicate archive key")
    archives = [value for key, value in objects.items() if key.startswith("AlchemicalArchive-")]
    networks = [
        (key, value) for key, value in objects.items() if key.startswith("AlchemicalNetwork-")
    ]
    if len(archives) != 1 or len(networks) != 1:
        raise DataContractError("archive needs one network and one result index")
    archive, (network_key, network) = archives[0], networks[0]
    if _reference(archive.get("network"), "archive network") != network_key:
        raise DataContractError("archive network reference is inconsistent")
    edge_refs = network.get("edges")
    node_refs = network.get("nodes")
    if not isinstance(edge_refs, list) or not isinstance(node_refs, list):
        raise DataContractError("network edges or nodes are missing")
    edge_keys = [_reference(item, "network edge") for item in edge_refs]
    node_keys = {_reference(item, "network node") for item in node_refs}
    if len(set(edge_keys)) != len(edge_keys) or not edge_keys:
        raise DataContractError("duplicate or empty network edges")
    result_index = archive.get("transformation_results")
    if not isinstance(result_index, list):
        raise DataContractError("transformation results are missing")
    results: dict[str, list[str]] = {}
    for item in result_index:
        if not isinstance(item, list) or len(item) != 2 or not isinstance(item[1], list):
            raise DataContractError("malformed transformation result index")
        key = _reference(item[0], "result transformation")
        if key in results:
            raise DataContractError("duplicate transformation result index")
        results[key] = [_reference(ref, "DAG result") for ref in item[1]]
    if set(results) != set(edge_keys):
        raise DataContractError("network edges and result transformations differ")
    legs: list[LegEdge] = []
    for key in edge_keys:
        transformation = objects.get(key)
        if not isinstance(transformation, dict):
            raise DataContractError(f"{key}: missing transformation")
        name = transformation.get("name")
        if not isinstance(name, str) or not name.startswith(("solvent_", "complex_")):
            raise DataContractError(f"{key}: invalid transformation name")
        kind = name.split("_", 1)[0]
        state_a = _reference(transformation.get("stateA"), f"{name} stateA")
        state_b = _reference(transformation.get("stateB"), f"{name} stateB")
        if state_a not in node_keys or state_b not in node_keys:
            raise DataContractError(f"{name}: state outside network")
        system_a, system_b = objects.get(state_a), objects.get(state_b)
        if not isinstance(system_a, dict) or not isinstance(system_b, dict):
            raise DataContractError(f"{name}: missing chemical system")
        components_a, components_b = system_a.get("components"), system_b.get("components")
        if not isinstance(components_a, dict) or not isinstance(components_b, dict):
            raise DataContractError(f"{name}: missing system components")
        a_key = _reference(components_a.get("ligand"), f"{name} ligand A")
        b_key = _reference(components_b.get("ligand"), f"{name} ligand B")
        if a_key == b_key or not all(ligand in objects for ligand in (a_key, b_key)):
            raise DataContractError(f"{name}: invalid ligand endpoints")
        labels = []
        for ligand_key in (a_key, b_key):
            ligand = objects[ligand_key]
            properties = ligand.get("molprops") if isinstance(ligand, dict) else None
            label = properties.get("ofe-name") if isinstance(properties, dict) else None
            if isinstance(label, int) and not isinstance(label, bool):
                label = str(label)
            if not isinstance(label, str) or not label:
                raise DataContractError(f"{name}: missing ligand source label")
            labels.append(label)
        a_label, b_label = labels
        if name != f"{kind}_{a_label}_{b_label}":
            raise DataContractError(f"{name}: name disagrees with ordered ligand labels")
        if ("protein" in components_a) != (kind == "complex") or ("protein" in components_b) != (
            kind == "complex"
        ):
            raise DataContractError(f"{name}: leg and system context disagree")
        mapping_key = _reference(transformation.get("mapping"), f"{name} mapping")
        mapping = objects.get(mapping_key)
        if not isinstance(mapping, dict) or (
            _reference(mapping.get("componentA"), f"{name} map A") != a_key
            or _reference(mapping.get("componentB"), f"{name} map B") != b_key
        ):
            raise DataContractError(f"{name}: mapping does not match ordered ligands")
        records: list[tuple[float, float, int]] = []
        estimate_count = 0
        unestimated_unit_count = 0
        for dag_key in results[key]:
            dag = objects.get(dag_key)
            if not isinstance(dag, dict) or dag.get("transformation_key") != key:
                raise DataContractError(f"{name}: DAG belongs to a different transformation")
            units = dag.get("protocol_unit_results")
            if not isinstance(units, list) or not units:
                raise DataContractError(f"{name}: missing units for a repeat")
            generations: dict[int, tuple[float, float, int]] = {}
            for unit_ref in units:
                unit = objects.get(_reference(unit_ref, f"{name} unit"))
                if not isinstance(unit, dict):
                    raise DataContractError(f"{name}: missing unit")
                outputs = unit.get("outputs")
                if not isinstance(outputs, dict) or "unit_estimate" not in outputs:
                    unestimated_unit_count += 1
                    continue
                repeat = outputs.get("repeat_id")
                generation = outputs.get("generation")
                if isinstance(repeat, bool) or not isinstance(repeat, int):
                    raise DataContractError(f"{name}: missing repeat ID")
                if (
                    isinstance(generation, bool)
                    or not isinstance(generation, int)
                    or generation < 0
                ):
                    raise DataContractError(f"{name}: invalid generation")
                if generation in generations:
                    raise DataContractError(f"{name}: duplicate generation in a repeat")
                generations[generation] = (
                    _finite_quantity(outputs.get("unit_estimate"), f"{name} estimate"),
                    _finite_quantity(
                        outputs.get("unit_estimate_error"), f"{name} error", positive=True
                    ),
                    repeat,
                )
            if not generations or set(generations) != set(range(max(generations) + 1)):
                raise DataContractError(f"{name}: missing intermediate generation")
            if len({record[2] for record in generations.values()}) != 1:
                raise DataContractError(f"{name}: mixed repeat IDs in one DAG")
            estimate_count += len(generations)
            records.append(generations[max(generations)])
        mean, standard_error = _repeat_estimate(records)
        legs.append(
            LegEdge(
                name,
                kind,
                a_key,
                b_key,
                a_label,
                b_label,
                mapping_key,
                estimate_count,
                unestimated_unit_count,
                mean,
                standard_error,
            )
        )
    if len({leg.name for leg in legs}) != len(legs):
        raise DataContractError("duplicate transformation name")
    return tuple(legs)


def pair_binding_edges(legs: tuple[LegEdge, ...]) -> tuple[BindingEdge, ...]:
    pairs: dict[str, dict[str, LegEdge]] = defaultdict(dict)
    for leg in legs:
        suffix = leg.name.split("_", 1)[1]
        if leg.kind in pairs[suffix]:
            raise DataContractError(f"{suffix}: duplicate {leg.kind} leg")
        pairs[suffix][leg.kind] = leg
    binding: list[BindingEdge] = []
    for suffix, pair in sorted(pairs.items()):
        if set(pair) != {"solvent", "complex"}:
            raise DataContractError(f"{suffix}: missing solvent or complex leg")
        solvent, complex_leg = pair["solvent"], pair["complex"]
        if (
            solvent.a_key,
            solvent.b_key,
            solvent.a_label,
            solvent.b_label,
            solvent.mapping_key,
        ) != (
            complex_leg.a_key,
            complex_leg.b_key,
            complex_leg.a_label,
            complex_leg.b_label,
            complex_leg.mapping_key,
        ):
            raise DataContractError(f"{suffix}: paired legs have different ordered endpoints")
        binding.append(
            BindingEdge(
                suffix,
                solvent.a_key,
                solvent.b_key,
                solvent.a_label,
                solvent.b_label,
                complex_leg.mean - solvent.mean,
                math.hypot(complex_leg.standard_error, solvent.standard_error),
            )
        )
    return tuple(binding)


def _signed(edge: BindingEdge, origin: str, destination: str) -> float:
    if (edge.a_key, edge.b_key) == (origin, destination):
        return edge.mean
    if (edge.b_key, edge.a_key) == (origin, destination):
        return -edge.mean
    raise DataContractError("cycle path does not follow an edge")


def cycle_basis(edges: tuple[BindingEdge, ...]) -> list[dict[str, Any]]:
    """Use each chord and its unique sorted spanning-tree path once."""
    labels: dict[str, str] = {}
    parent: dict[str, str] = {}

    def root(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            node = parent[node]
        return node

    tree: dict[str, list[tuple[str, BindingEdge]]] = defaultdict(list)
    chords: list[BindingEdge] = []
    for edge in sorted(edges, key=lambda item: item.name):
        for key, label in ((edge.a_key, edge.a_label), (edge.b_key, edge.b_label)):
            if key in labels and labels[key] != label:
                raise DataContractError("one ligand has conflicting source labels")
            labels[key] = label
        a_root, b_root = root(edge.a_key), root(edge.b_key)
        if a_root == b_root:
            chords.append(edge)
        else:
            parent[a_root] = b_root
            tree[edge.a_key].append((edge.b_key, edge))
            tree[edge.b_key].append((edge.a_key, edge))
    cycles: list[dict[str, Any]] = []
    for chord in chords:
        queue = deque([chord.b_key])
        previous: dict[str, tuple[str, BindingEdge] | None] = {chord.b_key: None}
        while queue and chord.a_key not in previous:
            node = queue.popleft()
            for neighbor, edge in tree[node]:
                if neighbor not in previous:
                    previous[neighbor] = (node, edge)
                    queue.append(neighbor)
        if chord.a_key not in previous:
            raise DataContractError("spanning tree has no path for a cycle")
        path: list[tuple[str, str, BindingEdge]] = []
        node = chord.a_key
        while node != chord.b_key:
            step = previous[node]
            if step is None:
                raise DataContractError("broken cycle path")
            origin, edge = step
            path.append((origin, node, edge))
            node = origin
        path.reverse()
        signed_sum = math.fsum(
            [_signed(chord, chord.a_key, chord.b_key)]
            + [_signed(edge, origin, destination) for origin, destination, edge in path]
        )
        standard_error = math.sqrt(
            math.fsum([chord.standard_error**2] + [edge.standard_error**2 for _, _, edge in path])
        )
        tolerance = 2 * standard_error
        closed = abs(signed_sum) <= tolerance
        vertices = [chord.a_key, chord.b_key] + [destination for _, destination, _ in path]
        cycles.append(
            {
                "name": " -> ".join(labels[key] for key in vertices),
                "edge_count": 1 + len(path),
                "signed_sum_kcal_mol": round(signed_sum, 6),
                "standard_error_kcal_mol": round(standard_error, 6),
                "tolerance_kcal_mol": round(tolerance, 6),
                "closed": closed,
                "discrepancy_size_kcal_mol": round(abs(signed_sum), 6),
            }
        )
    return cycles


def audit_network(payload: bytes, system: str, expected_bytes: int) -> dict[str, Any]:
    legs = parse_archive(payload, expected_bytes=expected_bytes)
    binding = pair_binding_edges(legs)
    cycles = cycle_basis(binding)
    solvent = [edge for edge in legs if edge.kind == "solvent"]
    complex_legs = [edge for edge in legs if edge.kind == "complex"]
    failed = [cycle for cycle in cycles if not cycle["closed"]]
    return {
        "system": system,
        "edge_count": len(legs),
        "solvent_edges": len(solvent),
        "complex_edges": len(complex_legs),
        "binding_edges": len(binding),
        "estimate_count": sum(edge.estimate_count for edge in legs),
        "solvent_estimates": sum(edge.estimate_count for edge in solvent),
        "complex_estimates": sum(edge.estimate_count for edge in complex_legs),
        "estimates_per_edge": dict(
            sorted(Counter(str(edge.estimate_count) for edge in legs).items())
        ),
        "selected_repeat_estimates": 3 * len(legs),
        "unestimated_unit_records": sum(edge.unestimated_unit_count for edge in legs),
        "cycle_count": len(cycles),
        "closed_cycle_count": len(cycles) - len(failed),
        "failed_cycle_count": len(failed),
        "cycles": cycles,
        "failed_cycles": [
            {"name": cycle["name"], "discrepancy_size_kcal_mol": cycle["discrepancy_size_kcal_mol"]}
            for cycle in failed
        ],
    }
