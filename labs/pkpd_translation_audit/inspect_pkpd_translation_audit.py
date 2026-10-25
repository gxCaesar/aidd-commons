"""Show the explicit model or recompute its frozen invariants."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.az_clearance_system.data import (  # noqa: E402
    DataContractError,
    DataDownloadError,
)
from aidd_commons.pkpd_translation_audit.analysis import (  # noqa: E402
    AnalysisError,
    analyse,
    check_analysis,
    load_from_cache,
)
from aidd_commons.pkpd_translation_audit.model import ModelError  # noqa: E402
from aidd_commons.pkpd_translation_audit.protocol import (  # noqa: E402
    ProtocolError,
    load_protocol,
)
from aidd_commons.pkpd_translation_audit.summary import check_summary  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parent
CACHE = ROOT / ".cache/az_clearance_system"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    args = parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        result = analyse(load_from_cache(CACHE, protocol["source"]), protocol)
        failures = check_analysis(result)
        if args.action == "check":
            failures.extend(check_summary(LAB / "protocol.json", CACHE, LAB / "summary.json"))
    except (
        ProtocolError,
        AnalysisError,
        ModelError,
        DataContractError,
        DataDownloadError,
        KeyError,
        TypeError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.action == "check":
        if failures:
            for failure in failures:
                print(f"FAIL {failure}")
            return 1
        print("PASS cache, assay units, cohort partition, leave-one-out species step, ")
        print("     uncertainty propagation and committed summary")
        print(protocol["boundary"])
        return 0
    print("PK/PD TRANSLATION MODEL")
    for equation in protocol["model"]["equations"]:
        print(equation)
    print("\nMeasured inputs")
    for name, spec in protocol["model"]["measured_inputs"].items():
        print(f"{name}: {spec['value']} {spec['unit']} | {spec['source']}")
    print("\nDerived input")
    for name, spec in protocol["model"]["derived_input"].items():
        print(f"{name}: {spec['value']} {spec['unit']} | {spec['source']}")
    print("\nParameters")
    for name, spec in protocol["model"]["parameters"].items():
        print(f"{name}: {spec['value']} {spec['unit']} | {spec['source']}")
    print("\nCohort")
    for name, value in result.cohort.items():
        print(f"{name}: {value}")
    print(f"not modelled: {result.uncarried_reasons}")
    print("\nPer-compound results at 24 h")
    print(
        "parent | human CL uL/min/10^6 cells | rat CL uL/min/10^6 cells | "
        "observed H/R | species factor [lower, upper] | "
        "translated CL L/h | total C at 0, 12, 24 h umol/L | free umol/L | occupancy | "
        "effect [lower, upper]"
    )
    for row in result.modelled:
        print(
            f"{row.parent_molecule_chembl_id} | {row.human_hepatocyte_clearance:.4g} | "
            f"{row.rat_hepatocyte_clearance:.4g} | {row.observed_human_to_rat_ratio:.3g} | "
            f"{row.translation_factor:.3g} [{row.translation_factor_lower:.3g}, "
            f"{row.translation_factor_upper:.3g}] | {row.modelled_clearance_l_h:.4g} | "
            f"{row.concentration_0h_umol_l:.4g}, "
            f"{row.concentration_12h_umol_l:.4g}, "
            f"{row.concentration_24h_umol_l:.4g} | "
            f"{row.free_concentration_24h_umol_l:.4g} | {row.occupancy_24h:.4g} | "
            f"{row.effect_24h:.4g} [{row.effect_24h_lower:.4g}, "
            f"{row.effect_24h_upper:.4g}]"
        )
    print("\n" + protocol["boundary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
