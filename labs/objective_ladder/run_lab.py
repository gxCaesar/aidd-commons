"""Fetch the public records the objective ladder reads.

    python labs/objective_ladder/run_lab.py download

Writes every retrieved record into `.cache/objective_ladder/` and records the
date it was read. The download is resumable: a cached record whose byte length
still matches the protocol is not fetched again. The first run contacts four
public archives, so it needs the network; the second does not.

The affinity snapshot is the one the affinity laboratory already reads. It is
kept under this laboratory's own cache and its byte length is checked on every
run, so a partial download is refused rather than read.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidd_commons.objective_ladder.data import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    download_affinity_snapshot,
    find_structures,
    read_affinity_records,
    read_alphafold,
    read_coordinates,
    read_date,
    read_entry_accessions,
    read_structure,
    read_uniprot,
)
from aidd_commons.objective_ladder.protocol import load_protocol  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    download = subparsers.add_parser("download", help="fetch every declared record")
    download.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    arguments = parser.parse_args()
    cache_dir = arguments.cache_dir

    protocol = load_protocol()
    read_date(cache_dir)

    snapshot = download_affinity_snapshot(cache_dir)
    print(f"the affinity snapshot is {snapshot.stat().st_size} bytes")

    affinity = read_affinity_records(cache_dir)
    print(f"the affinity archive holds {len(affinity)} rows")

    for target in protocol.targets:
        record = read_uniprot(target.accession, cache_dir)
        print(
            f"{target.symbol}: UniProt {record.name[:52]} "
            f"({len(record.ec_numbers)} catalogue numbers, {record.sequence_length} residues)"
        )

        prediction = read_alphafold(target.accession, cache_dir)
        if prediction is None:
            print(f"{target.symbol}: the model archive holds no prediction")
        else:
            print(f"{target.symbol}: model {prediction.entry_id} dated {prediction.model_created}")

        structure = read_structure(target.structure_id, cache_dir)
        print(
            f"{target.symbol}: structure {structure.entry_id} by {structure.method}, "
            f"bound components {', '.join(structure.ligand_ids) or 'none'}"
        )

        structures = find_structures(target.accession, cache_dir)
        print(f"{target.symbol}: the archive holds {len(structures)} structures for this accession")

        coordinates = read_coordinates(target.structure_id, cache_dir)
        print(f"{target.symbol}: coordinates {len(coordinates)} characters")

        named = sorted({row.structure_code for row in affinity if row.structure_code in structures})
        for code in named:
            accessions = read_entry_accessions(code, cache_dir)
            mark = "names" if target.accession in accessions else "does not name"
            print(f"{target.symbol}: the affinity rows name {code}, and the entry {mark} it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
