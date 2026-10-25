"""Frozen constants for the LINCS L1000 cross-cell-line signature comparison.

Every file named here traces to one real, versioned GEO series deposition,
GSE70138 ("L1000 Connectivity Map perturbational profiles from Broad
Institute LINCS Center for Transcriptomics LINCS PHASE II"), not a third-
party aggregator. The 2015-dated Level 2 release for this same series uses a
simplified column-label scheme ("A375-trt_cp-5") that does not join to the
2017-dated metadata files; this protocol uses only the 2017-03-06 files,
whose expression-matrix column IDs are real `inst_id` values that join
directly to `inst_info`.
"""

from __future__ import annotations

PROTOCOL_ID = "lincs-l1000-perturbation-context-v1"
GEO_SERIES = "GSE70138"
GEO_SERIES_URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE70138"
GEO_SUPPL_BASE_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl"

# filename -> declared byte size, both fixed at fetch time. A future GEO
# update would ship under a different filename (as it did between the 2015
# and 2017 releases of this same series), so a changed size for the same
# name is treated as a contract violation rather than silently accepted.
FILES = {
    "inst_info": ("GSE70138_Broad_LINCS_inst_info_2017-03-06.txt.gz", 4783200),
    "cell_info": ("GSE70138_Broad_LINCS_cell_info_2017-04-28.txt.gz", 2528),
    "gene_info": ("GSE70138_Broad_LINCS_gene_info_2017-03-06.txt.gz", 216692),
    "pert_info": ("GSE70138_Broad_LINCS_pert_info_2017-03-06.txt.gz", 82376),
    "level2_gctx": (
        "GSE70138_Broad_LINCS_Level2_GEX_n345976x978_2017-03-06.gctx.gz",
        668884165,
    ),
}

CELL_LINE_A = "MCF7"
CELL_LINE_B = "PC3"
FIXED_TIME = "24.0"
FIXED_TIME_UNIT = "h"
FIXED_DOSE = "10.0"
FIXED_DOSE_UNIT = "um"

# A single fixed cyclic rotation of the sorted shared-compound list pairs
# each compound's cell-A profile with a different, deterministic compound's
# cell-B profile. No random state is used anywhere in this protocol.
NULL_ROTATION = 1
