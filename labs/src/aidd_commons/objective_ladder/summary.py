"""The committed projection of the laboratory's reading.

The summary is small on purpose. It carries the protocol identifier, the date
the reading was computed, the software it was computed with, and for each
examined entity the six outcomes and what the run found in total. It carries no
raw archive payload.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from aidd_commons.objective_ladder.analysis import TargetLadder
from aidd_commons.objective_ladder.protocol import OBJECTIVES


def build_summary(
    ladders: list[TargetLadder],
    *,
    protocol_id: str,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Project the reading into the committed shape."""
    targets: list[dict[str, Any]] = []
    for ladder in ladders:
        outcomes = []
        for name in OBJECTIVES:
            outcome = ladder.outcomes[name]
            outcomes.append(
                {
                    "objective": outcome.objective,
                    "found": outcome.found,
                    "record": outcome.record,
                    "detail": outcome.detail,
                    "absence_reason": outcome.absence_reason,
                }
            )
        targets.append(
            {
                "accession": ladder.accession,
                "symbol": ladder.symbol,
                "name": ladder.name,
                "structure_id": ladder.structure_id,
                "evidenced_objectives": ladder.evidenced,
                "empty_objectives": ladder.empty,
                "outcomes": outcomes,
            }
        )

    cells = len(ladders) * len(OBJECTIVES)
    filled = sum(target["evidenced_objectives"] for target in targets)
    per_objective = {
        name: sum(1 for target in targets if target["outcomes"][index]["found"])
        for index, name in enumerate(OBJECTIVES)
    }
    return {
        "schema_version": "aidd-commons.objective-ladder-summary.v1",
        "protocol_id": protocol_id,
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or {},
        "objectives": list(OBJECTIVES),
        "targets": targets,
        "counts": {
            "targets": len(targets),
            "objectives": len(OBJECTIVES),
            "cells": cells,
            "filled_cells": filled,
            "empty_cells": cells - filled,
            "filled_per_objective": per_objective,
        },
    }
