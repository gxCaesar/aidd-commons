"""Copy the validated affinity snapshot into this lab's separate cache."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.skempi_affinity.data import (  # noqa: E402
    CACHE_FILENAME,
    download_and_cache,
    parse_payload,
    validate_size,
)
from aidd_commons.specificity_margin_audit.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
CACHE = ROOT / ".cache/specificity_margin_audit"
SIBLING_CACHE = ROOT / ".cache/skempi_affinity"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    args = parser.parse_args()
    if args.action != "download":
        return 2
    try:
        load_protocol(LAB / "protocol.json")
        destination = CACHE / CACHE_FILENAME
        if destination.is_file():
            payload = destination.read_bytes()
            validate_size(payload)
            parse_payload(payload)
        else:
            sibling = SIBLING_CACHE / CACHE_FILENAME
            if sibling.is_file():
                payload = sibling.read_bytes()
                validate_size(payload)
            else:
                payload = download_and_cache(CACHE).read_bytes()
            parse_payload(payload)
            if not destination.is_file():
                CACHE.mkdir(parents=True, exist_ok=True)
                if sibling.is_file():
                    destination.write_bytes(payload)
                validate_size(destination.read_bytes())
        print(f"cached_bytes={destination.stat().st_size}")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
