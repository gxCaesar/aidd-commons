"""Confirm that the owning L1000 snapshot is already cached without writing data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.l1000_perturbation_context.protocol import FILES  # noqa: E402
from aidd_commons.mechanism_consistency.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/l1000_perturbation_context"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        load_protocol(LAB / "protocol.json")
        for key, (name, expected_bytes) in FILES.items():
            path = args.cache_dir / name
            if not path.is_file() or path.stat().st_size != expected_bytes:
                raise ValueError(f"{key} is absent or differs from the owning snapshot contract")
        print(f"PASS: {len(FILES)} owning snapshot files are cached; no download or copy")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
