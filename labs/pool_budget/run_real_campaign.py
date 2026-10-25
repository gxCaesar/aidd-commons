"""Separate, explicit one-time entry point; the synthetic simulator is unchanged."""

import argparse
import json
from pathlib import Path

from aidd_commons.pool_budget_runner import run_locked_campaign, validate_real_protocol


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-protocol", help="validate settings without reading assay data")
    evaluate = commands.add_parser("evaluate-locked", help="one-time paired real assay campaign")
    evaluate.add_argument("--confirm-locked-evaluation", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        if args.command == "validate-protocol":
            protocol = validate_real_protocol(root)
            print(
                json.dumps(
                    {
                        "protocol_id": protocol["protocol_id"],
                        "validation": "passed",
                        "assay_data": "not_read",
                        "campaign_execution": "not_requested",
                    },
                    indent=2,
                )
            )
        else:
            print(
                json.dumps(
                    run_locked_campaign(root, confirmed=args.confirm_locked_evaluation),
                    indent=2,
                    allow_nan=False,
                )
            )
    except (ValueError, OSError) as error:
        parser.exit(1, f"campaign refused or failed: {error}\n")


if __name__ == "__main__":
    main()
