"""Frozen ChEMBL 37 EGFR representation-baseline lab."""

from aidd_commons.chembl_egfr.data import (
    AssayDataset,
    DataAudit,
    DataContractError,
    ParentActivityRecord,
)
from aidd_commons.chembl_egfr.protocol import PROTOCOL_VERSION

__all__ = [
    "AssayDataset",
    "DataAudit",
    "DataContractError",
    "PROTOCOL_VERSION",
    "ParentActivityRecord",
]
