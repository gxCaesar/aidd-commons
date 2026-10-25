"""The objective-ladder laboratory: six objectives, read apart.

A curriculum topic in this track asks a reader to separate sequence recovery,
folding, structural plausibility, binding, catalysis and biological function.
This package states the separation as a machine-readable contract, reads the
public records that could carry evidence for each objective, and reports which
objectives have a record and which do not.
"""

from aidd_commons.objective_ladder.analysis import (
    TargetEvidence,
    TargetLadder,
    audit_recovery,
    audit_structure,
    build_ladder,
)
from aidd_commons.objective_ladder.protocol import (
    OBJECTIVE_SOURCES,
    OBJECTIVES,
    ContractError,
    Protocol,
    Target,
    load_protocol,
)
from aidd_commons.objective_ladder.runner import read_ladders

__all__ = [
    "OBJECTIVES",
    "OBJECTIVE_SOURCES",
    "ContractError",
    "Protocol",
    "Target",
    "TargetEvidence",
    "TargetLadder",
    "audit_recovery",
    "audit_structure",
    "build_ladder",
    "load_protocol",
    "read_ladders",
]
