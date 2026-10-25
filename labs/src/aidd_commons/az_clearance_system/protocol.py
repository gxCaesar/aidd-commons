"""Frozen constants for the AstraZeneca intrinsic-clearance assay-system comparison.

Every constant here traces to one real, citable ChEMBL dataset deposition
(document CHEMBL3301361, "Experimental in vitro DMPK and physicochemical data
on a set of publicly disclosed compounds", AstraZeneca, 2016), not to a
paywalled journal article. This narrows the topic to intrinsic clearance
only: it does not cover absorption, distribution or oral bioavailability,
which this repository has not yet found a source for that survives its own
licence check (see docs/ROADMAP_V0.2.md, 2026-09-12).
"""

from __future__ import annotations

PROTOCOL_ID = "chembl37-az-clearance-system-v1"
CHEMBL_VERSION = "ChEMBL_37"
CHEMBL_RELEASE_DATE = "2026-05-01"
CHEMBL_API_ROOT = "https://www.ebi.ac.uk"
CHEMBL_STATUS_URL = f"{CHEMBL_API_ROOT}/chembl/api/data/status.json"

DOCUMENT_CHEMBL_ID = "CHEMBL3301361"

# assay_chembl_id -> (system label, species, matrix)
SYSTEMS = {
    "CHEMBL3301370": ("Human liver microsomes", "human", "microsome"),
    "CHEMBL3301371": ("Rat hepatocytes", "rat", "hepatocyte"),
    "CHEMBL3301372": ("Human hepatocytes", "human", "hepatocyte"),
}

ACTIVITY_FIELDS = (
    "activity_id",
    "assay_chembl_id",
    "document_chembl_id",
    "canonical_smiles",
    "data_validity_comment",
    "molecule_chembl_id",
    "parent_molecule_chembl_id",
    "potential_duplicate",
    "standard_flag",
    "standard_relation",
    "standard_type",
    "standard_units",
    "standard_value",
    "value",
    "units",
)

VALUE_CONSISTENCY_TOLERANCE = 1e-6
