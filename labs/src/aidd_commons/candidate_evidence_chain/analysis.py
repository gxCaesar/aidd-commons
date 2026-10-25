"""Assemble eight links for selected parents without filling evidence gaps."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .protocol import EXAMPLE_PARENTS, LINKS, STATES

ACTIVITY_SCOPE = "Observed in vitro response potency in the named assay and document only."
SELECTIVITY_SCOPE = "Observed CYP3A4 versus CYP2D6 inhibition in the same document only."
EXPOSURE_SCOPE = "Observed in vitro intrinsic clearance in the named assay system only."


def _link(
    name: str,
    state: str,
    *,
    scope: str | None = None,
    source: str | None = None,
    measurements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "state": state,
        "scope": scope,
        "source": source,
        "measurements": measurements or [],
    }


def _selectivity_measurements(profile: dict[str, Any]) -> list[dict[str, Any]]:
    interaction = profile["interaction"]
    if interaction is None:
        return []
    rows = interaction["measurements"]
    if len(rows) != 2 or {row["target"] for row in rows} != {"CYP3A4", "CYP2D6"}:
        return []
    if any(row["contributing_activity_count"] != 1 for row in rows):
        return []
    if len(rows[0]["document_chembl_ids"]) != 1 or (
        rows[0]["document_chembl_ids"] != rows[1]["document_chembl_ids"]
    ):
        return []
    return [
        {
            "value": row["value"],
            "unit": row["unit"],
            "target": row["target"],
            "assay_chembl_id": row["assay_chembl_ids"][0],
            "document_chembl_id": row["document_chembl_ids"][0],
        }
        for row in rows
    ]


def make_chain(profile: dict[str, Any]) -> dict[str, Any]:
    """Use a validated integration profile, retaining source measurements."""
    activity = profile["efficacy"]
    clearance = profile["exposure"]
    selectivity = _selectivity_measurements(profile)
    links = [
        _link("mechanism", "not covered"),
        _link("target", "not covered"),
        _link(
            "activity",
            "measured" if activity else "absent",
            scope=ACTIVITY_SCOPE if activity else None,
            source="decision_unit_scope" if activity else None,
            measurements=activity["measurements"] if activity else [],
        ),
        _link(
            "selectivity",
            "measured" if selectivity else "absent",
            scope=SELECTIVITY_SCOPE if selectivity else None,
            source="cyp_assay_system" if selectivity else None,
            measurements=selectivity,
        ),
        _link(
            "exposure",
            "measured" if clearance else "absent",
            scope=EXPOSURE_SCOPE if clearance else None,
            source="az_clearance_system" if clearance else None,
            measurements=[
                {
                    "value": row["value"],
                    "unit": row["unit"],
                    "assay_chembl_id": row["assay_chembl_id"],
                    "assay_system": row["assay_system"],
                    "document_chembl_id": "CHEMBL3301361",
                }
                for row in clearance["measurements"]
            ]
            if clearance
            else [],
        ),
        _link("safety", "not covered"),
        _link("synthesis", "not covered"),
        _link("reproducibility", "not covered"),
    ]
    counts = Counter(link["state"] for link in links)
    first_non_measured = next((link["name"] for link in links if link["state"] != "measured"), None)
    return {
        "parent_chembl_id": profile["parent_chembl_id"],
        "links": links,
        "counts": {state: counts[state] for state in STATES},
        "first_non_measured": first_non_measured,
        "supports_claim": first_non_measured is None,
        "bounded_claim": links[0]["scope"] if first_non_measured is None else None,
    }


def make_chains(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {profile["parent_chembl_id"]: profile for profile in profiles}
    if len(by_id) != len(profiles):
        raise ValueError("duplicate parent profile")
    if any(parent not in by_id for parent in EXAMPLE_PARENTS):
        raise ValueError("declared example parent is missing")
    chains = [make_chain(by_id[parent]) for parent in EXAMPLE_PARENTS]
    audit_chains(chains)
    return chains


def audit_chains(chains: list[dict[str, Any]]) -> None:
    """Recompute the claim gate and reject filled missing or constructed links."""
    if not chains or len({chain["parent_chembl_id"] for chain in chains}) != len(chains):
        raise ValueError("chain units are missing or duplicated")
    for chain in chains:
        links = chain["links"]
        if [link["name"] for link in links] != list(LINKS):
            raise ValueError("chain links differ from frozen order")
        for link in links:
            state = link["state"]
            if state not in STATES or set(link) != {
                "name",
                "state",
                "scope",
                "source",
                "measurements",
            }:
                raise ValueError("link state or fields are invalid")
            if state == "measured":
                if not link["measurements"] or not link["source"] or not link["scope"]:
                    raise ValueError("measured link lacks provenance or scope")
                for row in link["measurements"]:
                    if not all(key in row for key in ("value", "unit", "document_chembl_id")):
                        raise ValueError("measured link lacks value, unit or document")
                    if not ("assay_chembl_id" in row or "target" in row):
                        raise ValueError("measured link lacks assay or target")
            elif link["measurements"] or link["scope"]:
                raise ValueError("unmeasured link carries a measurement or claim scope")
            elif state == "constructed" and not link["source"]:
                raise ValueError("constructed link lacks teaching source")
            elif state in {"absent", "not covered"} and link["source"] is not None:
                raise ValueError("missing link has an evidence source")
        counts = Counter(link["state"] for link in links)
        if chain["counts"] != {state: counts[state] for state in STATES}:
            raise ValueError("per-chain state counts differ")
        first = next((link["name"] for link in links if link["state"] != "measured"), None)
        if chain["first_non_measured"] != first:
            raise ValueError("first non-measured link differs")
        if chain["supports_claim"] is not (first is None):
            raise ValueError("claim crosses an unmeasured link")
        allowed_scope = links[0]["scope"] if first is None else None
        if chain["bounded_claim"] != allowed_scope:
            raise ValueError("claim exceeds the first measured link's scope")
