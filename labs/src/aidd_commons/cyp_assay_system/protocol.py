"""Frozen constants for the CYP3A4-versus-CYP2D6 assay-system comparison.

This is a new, separate protocol. It reads the same live ChEMBL API this
project's other ChEMBL-derived labs already use, under the same release, but
defines its own targets, its own admission rule and its own entity unit. It
does not import, call or modify anything in the `chembl_egfr` package.
"""

from __future__ import annotations

PROTOCOL_ID = "chembl37-cyp-assay-system-v1"
CHEMBL_VERSION = "ChEMBL_37"
CHEMBL_RELEASE_DATE = "2026-05-01"
CHEMBL_API_ROOT = "https://www.ebi.ac.uk"
CHEMBL_STATUS_URL = f"{CHEMBL_API_ROOT}/chembl/api/data/status.json"

TARGETS = {
    "CHEMBL340": "CYP3A4",
    "CHEMBL289": "CYP2D6",
}

ACTIVITY_FIELDS = (
    "activity_id",
    "assay_chembl_id",
    "document_chembl_id",
    "canonical_smiles",
    "data_validity_comment",
    "molecule_chembl_id",
    "parent_molecule_chembl_id",
    "pchembl_value",
    "potential_duplicate",
    "standard_flag",
    "standard_relation",
    "standard_type",
    "standard_units",
    "standard_value",
)

# The admission rule below is the one this project's ChEMBL EGFR representation
# protocol already established (labs/chembl_egfr/data.py: normalise_activity_rows):
# exact IC50 in nM, standard_flag 1, potential_duplicate 0, no data validity
# comment, molecule_chembl_id equal to parent_molecule_chembl_id, a valid RDKit
# structure, and pChEMBL consistent with standard_value to within this tolerance.
PCHEMBL_CONSISTENCY_TOLERANCE = 0.011
