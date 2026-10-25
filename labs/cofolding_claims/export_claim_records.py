"""Export the structure-family slice of the resource registry, and nothing else.

The published registry `site/public/data/resources.v1.json` is a build artifact and
is not committed, so a lab that reads it directly would not run from a clean
checkout. This script freezes the fields the claim inspector needs into
`claim-records.json`, which is committed and travels with the lab.

    python labs/cofolding_claims/export_claim_records.py
    python labs/cofolding_claims/export_claim_records.py --update

Without `--update` an existing extract is never overwritten: the script reports
which records would change and exits non-zero, so a registry edit cannot silently
move a number a lesson quotes.
"""

import argparse
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
SOURCE = ROOT / "site/public/data/resources.v1.json"
TARGET = LAB / "claim-records.json"

# Task labels grouped by the claim each one licenses. A record enters the extract
# only by declaring one of these; nothing is selected by name.
CLAIM_CLASSES = {
    "monomer prediction": ["structure-prediction"],
    "co-folded complex": ["co-folding"],
    "generated pose": ["molecular-docking"],
    "pose check": ["pose-validation"],
    "affinity estimate": ["affinity-prediction", "drug-target-affinity-prediction"],
}
OPENNESS_ORDER = (
    "inference_code",
    "training_code",
    "weights",
    "architecture",
    "data_recipe",
    "training_data",
    "evaluation_code",
)
KEPT = ("id", "name", "kind", "tasks", "modalities", "last_verified")


def slice_registry(records: list[dict]) -> dict:
    wanted = {task for tasks in CLAIM_CLASSES.values() for task in tasks}
    rows = []
    for record in sorted(records, key=lambda row: row["id"]):
        if not wanted & set(record.get("tasks") or ()):
            continue
        openness = record.get("openness") or {}
        rows.append(
            {
                **{key: record.get(key) for key in KEPT},
                "openness": {
                    name: (openness.get(name) or {}).get("value", "unverified")
                    for name in OPENNESS_ORDER
                },
            }
        )
    return {
        "source": str(SOURCE.relative_to(ROOT)),
        "source_records": len(records),
        "claim_classes": CLAIM_CLASSES,
        "openness_order": list(OPENNESS_ORDER),
        "records": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="replace a differing extract")
    update = parser.parse_args().update

    if SOURCE.is_symlink() or TARGET.is_symlink():
        raise ValueError("extract input and output must not be symlinks")
    if not SOURCE.is_file():
        raise SystemExit(f"{SOURCE.relative_to(ROOT)} is a build artifact; run the catalog export")

    extract = slice_registry(json.loads(SOURCE.read_text(encoding="utf-8")))
    if TARGET.is_file():
        current = json.loads(TARGET.read_text(encoding="utf-8"))
        if current == extract:
            count = len(extract["records"])
            print(f"{TARGET.name} already matches the registry ({count} records).")
            return
        before = {row["id"]: row for row in current["records"]}
        after = {row["id"]: row for row in extract["records"]}
        for identifier in sorted(set(before) | set(after)):
            if before.get(identifier) != after.get(identifier):
                print(f"  changed  {identifier}")
        if not update:
            print("Extract differs from the registry. Re-run with --update to replace it.")
            sys.exit(1)

    TARGET.write_text(json.dumps(extract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {TARGET.name} with {len(extract['records'])} records.")


if __name__ == "__main__":
    main()
