"""Print the synthetic teaching campaign; no network or real-data mode."""

import json

from aidd_commons.pool_budget import campaign_summary

if __name__ == "__main__":
    print(json.dumps(campaign_summary(), indent=2, allow_nan=False))
