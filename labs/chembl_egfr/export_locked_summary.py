"""Export already completed scores without running the ChEMBL evaluation."""

from pathlib import Path

from aidd_commons.locked_result_summaries import export_locked_summary

if __name__ == "__main__":
    export_locked_summary(Path(__file__).resolve().parent, kind="chembl", reviewed_on="2026-09-08")
    print("Verified aggregate-only locked-summary.json; no evaluation executed.")
