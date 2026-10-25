"""Fetch a page and print the sentences that mention its terms.

Several catalogue records carry an unverified access level because the page
that states the terms could not be read on the day it was checked. The reason
is usually mechanical rather than substantive: a redirect, a certificate that
expired, a page that renders through JavaScript, or a host that refuses the
client. This script fetches the page and prints the sentences around the
words that carry terms, so a reader can see what the page says without
scrolling.

    python scripts/catalog/read-terms.py <url> [<url> ...]

It prints the HTTP status, the size, the plain text of the page, and the
passages around each match for a licence, a copyright, a term of use, a
citation, an access statement or a download statement. A page that refuses the
connection is reported as such, because "the page would not load" is itself
the finding the catalogue has to record.
"""

from __future__ import annotations

import html
import re
import ssl
import sys
import urllib.error
import urllib.request

#: The words that usually carry the terms a catalogue record needs.
TERMS = re.compile(
    r"licen[cs]e|copyright|terms of use|terms of service|creative commons"
    r"|\bCC BY\b|\bCC0\b|\bCC-BY\b|public domain|attribution|citation"
    r"|cite\b|access(?:ible)?|download|open access|registration required"
    r"|no account|free of charge|all rights reserved",
    re.IGNORECASE,
)


def plain_text(markup: str) -> str:
    """The readable text of a page, with its scripts and styles removed."""
    without_scripts = re.sub(r"<script.*?</script>", " ", markup, flags=re.S | re.I)
    without_styles = re.sub(r"<style.*?</style>", " ", without_scripts, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", without_styles))
    return re.sub(r"\s+", " ", text)


def fetch(url: str) -> tuple[int | None, str, str]:
    """Fetch a URL, following redirects, and return its status, body and note."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AIDD Commons catalogue review)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return response.status, body, ""
    except urllib.error.HTTPError as error:
        return error.code, "", error.reason if isinstance(error.reason, str) else str(error.reason)
    except ssl.SSLCertVerificationError as error:
        return None, "", f"certificate verification failed: {error}"
    except urllib.error.URLError as error:
        return None, "", f"{error.reason}"
    except (TimeoutError, OSError) as error:
        return None, "", str(error)


def report(url: str, limit: int = 12) -> None:
    """Print what a page says about its own terms."""
    status, body, note = fetch(url)
    print(f"=== {url}")
    if note:
        print(f"    FAILED: {note}")
        return
    print(f"    status {status}, {len(body)} bytes")
    text = plain_text(body)
    print(f"    text: {text[:400]}")
    shown = 0
    for match in TERMS.finditer(text):
        start = max(0, match.start() - 130)
        end = min(len(text), match.end() + 210)
        print(f"    * {text[start:end].strip()[:340]}")
        shown += 1
        if shown >= limit:
            break
    if shown == 0:
        print("    (no term-bearing sentence found in the rendered text)")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: read-terms.py <url> [<url> ...]")
        return 2
    for url in sys.argv[1:]:
        report(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
