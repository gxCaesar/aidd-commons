"""Report the evidence `supports` groups a catalogue record names outside the schema.

The resource schema accepts exactly ten metadata groups in an evidence entry's
`supports` list: the fields a piece of evidence can establish. A record that
names `openness`, `licenses` or `access_level` there fails the catalogue
validator, but only after the record has been written, and the message names
the schema rather than the rule.

    python scripts/catalog/check-evidence-supports.py [catalog/resources]

Exits non-zero when any record names a group outside the ten, and prints the
record, the evidence entry and the offending group. A record that passes here
can still fail the catalogue validator for other reasons; this check exists
because this one mistake is the most frequent one when a record is written.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

#: The metadata groups an evidence entry may establish, from
#: `catalog/schema/resource.ts`.
SUPPORT_GROUPS = {
    "name",
    "kind",
    "summary",
    "identifiers",
    "stages",
    "modalities",
    "tasks",
    "relations",
    "caveats",
    "acknowledgements",
}


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("catalog/resources")
    findings: list[str] = []
    for path in sorted(root.glob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            continue
        for entry in record.get("evidence", []) or []:
            if not isinstance(entry, dict):
                continue
            for group in entry.get("supports", []) or []:
                if group not in SUPPORT_GROUPS:
                    findings.append(
                        f"{path.name}: evidence {entry.get('id')!r} names "
                        f"{group!r}, which is not one of the ten metadata groups"
                    )
    for finding in findings:
        print(finding)
    print(
        f"checked {len(list(root.glob('*.yaml')))} records, "
        f"{len(findings)} findings"
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
