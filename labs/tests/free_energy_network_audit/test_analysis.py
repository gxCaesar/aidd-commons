"""Constructed bookkeeping cases and one real archive reader case."""

from __future__ import annotations

from pathlib import Path

import pytest
from aidd_commons.free_energy_network_audit.analysis import (
    BindingEdge,
    DataContractError,
    LegEdge,
    cycle_basis,
    pair_binding_edges,
    parse_archive,
)
from aidd_commons.free_energy_network_audit.protocol import SOURCE_FILES, source_filename

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / ".cache/free_energy_network_audit"


def _binding(name: str, a: str, b: str, mean: float) -> BindingEdge:
    return BindingEdge(name, a, b, a, b, mean, 0.1)


def test_cycle_basis_and_closure_rule() -> None:
    edges = (
        _binding("A_B", "A", "B", 1.0),
        _binding("B_C", "B", "C", 1.0),
        _binding("C_A", "C", "A", -2.0),
    )
    closed = cycle_basis(edges)
    assert len(closed) == 1
    assert closed[0]["closed"] is True
    assert closed[0]["signed_sum_kcal_mol"] == 0
    bad = cycle_basis(edges[:2] + (_binding("C_A", "C", "A", -1.0),))
    assert len(bad) == 1
    assert bad[0]["closed"] is False
    assert bad[0]["discrepancy_size_kcal_mol"] == 1.0
    assert bad[0]["tolerance_kcal_mol"] < 1.0


def test_solvent_and_complex_are_paired_then_subtracted() -> None:
    solvent = LegEdge("solvent_A_B", "solvent", "a", "b", "A", "B", "map", 3, 0, 2.0, 0.2)
    complex_leg = LegEdge("complex_A_B", "complex", "a", "b", "A", "B", "map", 3, 0, 3.0, 0.3)
    binding = pair_binding_edges((solvent, complex_leg))
    assert len(binding) == 1
    assert binding[0].mean == 1.0
    assert binding[0].standard_error == pytest.approx((0.2**2 + 0.3**2) ** 0.5)
    with pytest.raises(DataContractError, match="missing solvent or complex"):
        pair_binding_edges((solvent,))
    reversed_leg = LegEdge("complex_A_B", "complex", "b", "a", "A", "B", "map", 3, 0, 3.0, 0.3)
    with pytest.raises(DataContractError, match="different ordered endpoints"):
        pair_binding_edges((solvent, reversed_leg))


@pytest.mark.skipif(not CACHE.is_dir(), reason="the free-energy source archives are not cached")
def test_real_archive_recovers_referenced_edges() -> None:
    system, key, size = SOURCE_FILES[0]
    payload = (CACHE / source_filename(system, key)).read_bytes()
    legs = parse_archive(payload, expected_bytes=size)
    assert len(legs) == 54
    assert sum(edge.kind == "solvent" for edge in legs) == 27
    assert sum(edge.kind == "complex" for edge in legs) == 27
    assert sum(edge.estimate_count for edge in legs) == 162
