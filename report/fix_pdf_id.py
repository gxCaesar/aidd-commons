#!/usr/bin/env python3
"""Give a PDF a deterministic document identifier.

The only part of the built report that changes between two runs of the same
source is the trailer's `/ID` array, which the engine derives from a clock
reading rather than from the document's content. Everything else, including
every figure, is already byte-identical between runs.

The identifier is replaced with a digest of the document itself, computed in
two passes: the identifier is first blanked, the remainder is digested, and
the digest becomes the identifier. The result is that two builds of the same
source produce the same bytes, and a build of a changed source produces a
different identifier, which is what an identifier is for.

    python report/fix_pdf_id.py <file.pdf>
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ID_PATTERN = re.compile(rb"/ID\s*\[\s*<([0-9A-Fa-f]*)>\s*<([0-9A-Fa-f]*)>\s*\]")
BLANK = b"0" * 32


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: fix_pdf_id.py <file.pdf>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = path.read_bytes()

    match = ID_PATTERN.search(data)
    if match is None:
        print(f"{path}: the document has no /ID array, nothing to do")
        return 0
    # Two hexadecimal strings of equal length are the shape of a PDF identifier
    # entry. An earlier version of this script wrote sixty-four characters,
    # and those documents are normalised to the canonical thirty-two.
    if len(match.group(1)) != len(match.group(2)) or len(match.group(1)) not in (32, 64):
        print(f"{path}: the /ID array is not the expected shape, refusing to rewrite it")
        return 1

    blanked = ID_PATTERN.sub(b"/ID[<" + BLANK + b"><" + BLANK + b">]", data)
    # A PDF identifier entry holds two sixteen-byte strings, so the identifier is
    # the first sixteen bytes of the summary and is written as thirty-two hex
    # characters, which is the shape this script accepts on a second run.
    identifier = hashlib.sha256(blanked).digest()[:16].hex().encode("ascii")
    fixed = ID_PATTERN.sub(b"/ID[<" + identifier + b"><" + identifier + b">]", data)

    if fixed == data:
        print(f"{path}: the identifier is already the digest of this document")
        return 0
    path.write_bytes(fixed)
    print(f"{path}: identifier set to {identifier.decode('ascii')[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
