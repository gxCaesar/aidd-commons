"""Quantity and date context for live catalogue and retained-reading plots.

Catalogue counts use the canonical resources.v1 projection, not a named release
snapshot. Record verification dates describe the evidence in that projection;
they are not an export timestamp or a claim that every record was reviewed anew.
The second-reading series retains its original date while accumulating later
per-topic re-readings. Its current aggregate therefore has a separate as-of date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogueProjection:
    records: int
    verified_from: str
    verified_through: str

    def source_note(self) -> str:
        return (
            "The source is the canonical Atlas resources.v1 projection; individual record "
            f"verification dates range from {self.verified_from} to {self.verified_through}."
        )


def catalogue_projection(resources: list[dict]) -> CatalogueProjection:
    if not resources:
        raise ValueError("The catalogue projection has no records")
    ids = [record["id"] for record in resources]
    if len(set(ids)) != len(ids):
        raise ValueError("The catalogue projection contains duplicate record ids")
    dates = sorted(record["last_verified"] for record in resources)
    return CatalogueProjection(len(resources), dates[0], dates[-1])


def validate_openness_join(resources: list[dict], openness: list[dict]) -> None:
    resource_ids = {record["id"] for record in resources}
    if len(resource_ids) != len(resources):
        raise ValueError("The catalogue projection contains duplicate record ids")
    openness_ids = [record["id"] for record in openness]
    if len(set(openness_ids)) != len(openness_ids):
        raise ValueError("The openness projection contains duplicate record ids")
    missing = sorted(resource_ids - set(openness_ids))
    unexpected = sorted(set(openness_ids) - resource_ids)
    if missing or unexpected:
        raise ValueError(
            f"Catalogue/openness projection ids differ: missing {missing}; unexpected {unexpected}"
        )


@dataclass(frozen=True)
class ReadingSeries:
    aggregate_as_of: str
    initiated_on: str
    documented_through: str
    topics: int


def reading_series(payload: dict, reading: dict) -> ReadingSeries:
    topics = payload["taxonomy"]["topics"]
    if reading["cells"] != topics:
        raise ValueError("The retained reading does not cover the comparison topic denominator")
    outcomes = [reading[key] for key in ("equal", "reading_deeper", "reading_shallower")]
    if sum(outcomes) != topics:
        raise ValueError("Reading outcome counts do not sum to the topic denominator")
    for threshold in reading["thresholds"]:
        if not all(0 <= threshold[key] <= topics for key in ("recorded", "reading")):
            raise ValueError("A reading threshold count is outside the topic denominator")
    documented_dates = re.findall(
        r"\bbatch on (\d{4}-\d{2}-\d{2})\b", reading["reviewer"], flags=re.IGNORECASE
    )
    return ReadingSeries(
        payload["as_of"],
        reading["reviewed_on"],
        max([reading["reviewed_on"], *documented_dates]),
        topics,
    )


def validate_count_bounds(counts: list[int], limits: tuple[float, float]) -> None:
    outside = [count for count in counts if not limits[0] <= count <= limits[1]]
    if outside:
        raise ValueError(f"Topic counts {outside} fall outside the plotted axis limits {limits}")
