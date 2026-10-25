"""Frozen constants for the PubChem BioAssay assay-endpoint-and-controls comparison.

Every number here is a property of the archived PubChem BioAssay FTP release
that this protocol reads, measured on 2026-10-21 by fetching the named member
out of the named ranged zip with HTTP range requests. The byte lengths are the
lengths of the members as they sit inside the container zips, and the
decompressed lengths are the lengths of the bytes this lab caches.

Nothing in this module fetches anything. `ranged_zip.py` reads the container,
`data.py` caches and parses the members, and `analysis.py` computes the
descriptive read-outs.
"""

from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_ID = "pubchem-bioassay-endpoint-controls-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.assay-endpoint-controls-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.assay-endpoint-controls-summary.v1"

#: The PubChem BioAssay FTP area that holds the per-assay records. The data
#: area carries the per-assay result CSV, the description area carries the
#: per-assay description XML. Both are ranged zips: one member per assay.
DATA_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/pubchem/Bioassay/CSV/Data/"
DESCRIPTION_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/pubchem/Bioassay/CSV/Description/"

#: Measured on 2026-10-21. The ranged-zip member reader checks the container
#: length, the member length and the member CRC-32 on every run.
CONTAINER_BYTES = {
    "0000001_0001000": {
        "data": 779560315,
        "description": 2872234,
    },
    "0001001_0002000": {
        "data": 1313522439,
        "description": 4357168,
    },
}

#: Control regimes. The regime is a property of the archived record, declared
#: here and re-checked against the archived protocol text at run time.
CONTROL_REGIMES = (
    "positive_and_negative_reference",
    "single_positive_reference",
    "none_declared",
)

#: Keywords used to decide whether an archived protocol text declares a
#: control or a vehicle. Frozen so that the check is a rule and not a
#: reading of the record.
CONTROL_KEYWORDS = (
    "control",
    "vehicle",
    "untreated",
)

#: Words that can mean a control in an assay protocol but that the archive
#: also uses for other things. They are reported for the reader and are not
#: used to decide whether a control is declared, because assay 691 uses
#: "blank" for an empty table cell.
AMBIGUOUS_CONTROL_WORDS = ("blank",)

#: The named reference wells an archived protocol can declare. The count of
#: these that appear in the archived protocol text is the number of reference
#: wells the record states, which the lab compares with the declared regime.
REFERENCE_KEYWORDS = (
    "positive control",
    "negative control",
    "high_control",
    "low_control",
    "maximum stimulation control",
    "minimum stimulation control",
    "50% stimulation control",
)

#: Normalisation equations. Each id names a function in `normalisation.py`.
NORMALISATION_EQUATIONS = (
    "wells_relative_to_two_references",
    "archived_pka_equation",
    "relative_to_one_reference",
    "not_declared",
)

#: The deterministic compound-level split. Compounds are assigned to the
#: held-out half by the parity of a SHA-256 digest of the seed and the PubChem
#: compound identifier, so the assignment does not depend on row order, on the
#: number of compounds, or on any fitted quantity.
SPLIT_RULE = "sha256-seed-parity-by-compound"
SPLIT_SEED = 20261021

#: Tolerance, in response percentage points, used when the lab reports how far
#: a recomputed concentration-response curve sits from the archived curve.
CURVE_TOLERANCE_POINTS = 5.0

#: Tolerance, in response percentage points, used when the lab asks whether
#: the archived normalisation equation agrees with the archived data. The
#: equation's values at the reference wells are compared with the data's own
#: extremes under the better of the two possible pairings.
EQUATION_SCALE_BAND_POINTS = 25.0

#: The fraction of the archived per-concentration values that must fall
#: inside the range the archived equation describes, for the equation and the
#: data to be judged consistent.
EQUATION_SCALE_FRACTION = 0.95

#: How a concentration-response curve is obtained for one assay.
#: ``recompute`` means the archive carries the endpoint, the Hill slope and
#: both asymptotes, so the curve is recomputed from them.
#: ``fixed_range`` means the archive fixes the bottom and the top of the
#: response, so a fit holds them fixed.
#: ``free`` means the archive fits the bottom and the top freely.
HILL_FIT_MODES = ("recompute", "fixed_range", "free")

#: Minimum number of distinct concentrations a row must carry to be admitted.
MINIMUM_CONCENTRATIONS = 5


@dataclass(frozen=True)
class AssaySource:
    """One archived member of one ranged container zip.

    The member is itself a gzip file, so there are three lengths and they are
    not interchangeable. ``compressed_bytes`` is the length the container's
    central directory records for the member's stored form,
    ``member_bytes`` is the length of that stored form once the container's
    own compression is undone, and ``record_bytes`` is the length of the
    archived record after the gzip layer is undone, which is what this lab
    caches. ``crc32`` is the CRC-32 the container records for the member.
    """

    container: str
    member: str
    compressed_bytes: int
    member_bytes: int
    record_bytes: int
    crc32: int


@dataclass(frozen=True)
class AssaySpec:
    """The frozen description of one declared assay."""

    aid: int
    name: str
    endpoint_columns: tuple[str, ...]
    endpoint_units: tuple[str, ...]
    endpoint_labels: tuple[str, ...]
    qualifier_column: str
    direction: str
    control_regime: str
    normalisation_equation: str
    archived_normalisation_text: str
    replicate_declaration: str
    determination_column: str
    determination_kind: str
    concentration_columns_are_numeric: bool
    hill_parameter_columns: tuple[str, ...]
    hill_fit_mode: str
    source_data: AssaySource
    source_description: AssaySource

    @property
    def endpoint_label(self) -> str:
        return "+".join(self.endpoint_labels)


def _source(
    container: str,
    member_suffix: str,
    compressed: int,
    member_bytes: int,
    record_bytes: int,
    crc: int,
) -> AssaySource:
    return AssaySource(
        container=container,
        member=f"{container}/{member_suffix}",
        compressed_bytes=compressed,
        member_bytes=member_bytes,
        record_bytes=record_bytes,
        crc32=crc,
    )


ASSAYS: dict[int, AssaySpec] = {
    519: AssaySpec(
        aid=519,
        name="Dose Response Assay for Formylpeptide Receptor (FPR) Ligands",
        endpoint_columns=("IC50_MICROM", "KI_MICROM"),
        endpoint_units=("uM", "uM"),
        endpoint_labels=("IC50", "Ki"),
        qualifier_column="ACTIVITY_QUALIFIER",
        direction="inhibition",
        control_regime="positive_and_negative_reference",
        normalisation_equation="wells_relative_to_two_references",
        archived_normalisation_text=(
            "%Inhibition = 100 x [1 - (MFI_test - MFI_PC)/(MFI_NC - MFI_PC)], where MFI_PC is "
            "the average median fluorescence intensity of positive control wells (unlabeled "
            "receptor-blocking peptide) and MFI_NC is the average median fluorescence "
            "intensity of negative control wells (buffer)."
        ),
        replicate_declaration="each compound was tested in duplicate to result in 18 data points",
        determination_column="N_POINTS",
        determination_kind="data_points_per_curve",
        concentration_columns_are_numeric=True,
        hill_parameter_columns=("HILLSLOPE",),
        hill_fit_mode="fixed_range",
        source_data=_source("0000001_0001000", "519.csv.gz", 15482, 15482, 45668, 4146980699),
        source_description=_source(
            "0000001_0001000", "519.descr.xml.gz", 6870, 6870, 40283, 3619756491
        ),
    ),
    1277: AssaySpec(
        aid=1277,
        name=(
            "Dose response cell-based screening assay for antagonists of "
            "neuropeptide Y receptor Y1"
        ),
        endpoint_columns=("IC50",),
        endpoint_units=("uM",),
        endpoint_labels=("IC50",),
        qualifier_column="Qualifier",
        direction="inhibition",
        control_regime="positive_and_negative_reference",
        normalisation_equation="wells_relative_to_two_references",
        archived_normalisation_text=(
            "Ratio = (T45 / T0); %Inhibition = [1-((Ratio Test_Compound - "
            "Median_Ratio_High_Control)/(Median_Ratio_Low_Control - "
            "Median_Ratio_High_Control))]*100, where Low_Control is wells containing DMSO, "
            "NPY and isoproterenol and High_Control is wells containing DMSO and "
            "isoproterenol."
        ),
        replicate_declaration=(
            "test compounds were assayed in triplicate in a 10-point, 1:3 dilution series"
        ),
        determination_column="Number of DataPoints",
        determination_kind="data_points_per_curve",
        concentration_columns_are_numeric=True,
        hill_parameter_columns=("Hill Slope",),
        hill_fit_mode="free",
        source_data=_source("0001001_0002000", "1277.csv.gz", 5038, 5038, 13508, 1850989069),
        source_description=_source(
            "0001001_0002000", "1277.descr.xml.gz", 7049, 7049, 37306, 3923934143
        ),
    ),
    548: AssaySpec(
        aid=548,
        name="Dose-response biochemical assay for inhibitors of protein kinase A (PKA) activity",
        endpoint_columns=("IC50",),
        endpoint_units=("uM",),
        endpoint_labels=("IC50",),
        qualifier_column="Activity Qualifier",
        direction="inhibition",
        control_regime="positive_and_negative_reference",
        normalisation_equation="archived_pka_equation",
        archived_normalisation_text=(
            "%inhibition = (test_compound - median_positive_control)/"
            "(median_positive_control - median_negative_control)*100, where positive control is "
            "Staurosporine and negative control is DMSO only."
        ),
        replicate_declaration="each compound dilution was assayed in triplicate",
        determination_column="Number of Datapoints",
        determination_kind="data_points_per_curve",
        concentration_columns_are_numeric=True,
        hill_parameter_columns=("Hill Coefficient", "Hill S0", "Hill Sinf"),
        hill_fit_mode="recompute",
        source_data=_source("0000001_0001000", "548.csv.gz", 6880, 6880, 18331, 86429493),
        source_description=_source(
            "0000001_0001000", "548.descr.xml.gz", 4186, 4186, 22562, 2733274616
        ),
    ),
    439: AssaySpec(
        aid=439,
        name="S1P3 Agonist Dose-Response Potency Assay",
        endpoint_columns=("EC50",),
        endpoint_units=("uM",),
        endpoint_labels=("EC50",),
        qualifier_column="Activity Qualifier",
        direction="activation",
        control_regime="single_positive_reference",
        normalisation_equation="relative_to_one_reference",
        archived_normalisation_text=(
            "All data reported was normalized on a per-plate basis to wells that contained "
            "cells in the presence of 1 micromolar S1P (i.e. 100% activation)."
        ),
        replicate_declaration="each compound dilution series was assayed in triplicate",
        determination_column="Number of Points",
        determination_kind="data_points_per_curve",
        concentration_columns_are_numeric=True,
        hill_parameter_columns=("Hill Coefficient", "Hill S0", "Hill Sinf"),
        hill_fit_mode="recompute",
        source_data=_source("0000001_0001000", "439.csv.gz", 5915, 5915, 15725, 1480847838),
        source_description=_source(
            "0000001_0001000", "439.descr.xml.gz", 6827, 6827, 32180, 323608409
        ),
    ),
    464: AssaySpec(
        aid=464,
        name="Cell Proliferation & Viability (Cytotoxicity) Dose Response Assay 60K MLSMR",
        endpoint_columns=("AC50",),
        endpoint_units=("uM",),
        endpoint_labels=("AC50",),
        qualifier_column="Qualifier",
        direction="inhibition",
        control_regime="single_positive_reference",
        normalisation_equation="relative_to_one_reference",
        archived_normalisation_text=(
            "Percent inhibition was calculated from the median of the positive control "
            "doxorubicin at 4 micromolar final screening concentration."
        ),
        replicate_declaration=(
            "750 of 765 compounds were serially diluted ten times at three fold-dilutions"
        ),
        determination_column="N DataPoints",
        determination_kind="data_points_per_curve",
        concentration_columns_are_numeric=True,
        hill_parameter_columns=("Hill Slope", "Hill S0", "Hill Sinf"),
        hill_fit_mode="recompute",
        source_data=_source("0000001_0001000", "464.csv.gz", 43276, 43266, 126194, 1917588181),
        source_description=_source(
            "0000001_0001000", "464.descr.xml.gz", 4094, 4094, 20295, 281820707
        ),
    ),
    691: AssaySpec(
        aid=691,
        name="Zebrafish Lipid Metabolism Assay - Dose-Response Confirmation",
        endpoint_columns=("Mean MIC",),
        endpoint_units=("uM",),
        endpoint_labels=("MIC",),
        qualifier_column="Qualifier",
        direction="categorical",
        control_regime="none_declared",
        normalisation_equation="not_declared",
        archived_normalisation_text="",
        replicate_declaration="compounds that gave a measurable MIC were retested a second time",
        determination_column="Number of MIC determinations",
        determination_kind="independent_determinations",
        concentration_columns_are_numeric=False,
        hill_parameter_columns=(),
        hill_fit_mode="free",
        source_data=_source("0000001_0001000", "691.csv.gz", 2282, 2282, 12490, 3212126635),
        source_description=_source(
            "0000001_0001000", "691.descr.xml.gz", 3393, 3393, 22919, 2336650284
        ),
    ),
}

#: The declared assay set, in the order the protocol presents it.
DECLARED_ASSAYS: tuple[int, ...] = tuple(sorted(ASSAYS))


def container_url(base: str, container: str) -> str:
    """The exact URL of one ranged container zip."""
    return f"{base}{container}.zip"


def cache_file_names(aid: int) -> tuple[str, str]:
    """The two file names this lab caches for one assay."""
    return f"aid{aid}.csv", f"aid{aid}.descr.xml"
