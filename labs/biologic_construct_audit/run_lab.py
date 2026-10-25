"""Fetch the declared therapeutic records into this laboratory's committed snapshot."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.biologic_construct_audit.analysis import (  # noqa: E402
    audit_records,
    load_snapshot,
    render_snapshot,
    snapshot_file,
)
from aidd_commons.biologic_construct_audit.protocol import (  # noqa: E402
    PROTOCOL_ID,
    SNAPSHOT_SCHEMA_VERSION,
    load_protocol,
)

LAB = Path(__file__).resolve().parent


def fetch(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AIDD-Commons-construct-audit/0.2",
            "Accept": "application/json, application/xml",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read()
        final_url = response.geturl()
    if not body:
        raise ValueError(f"empty response from {url}")
    return body, final_url


def pharmaceutical_text(entry: dict[str, Any]) -> list[str]:
    texts = [
        item["value"]
        for comment in entry.get("comments", [])
        if comment.get("commentType") == "PHARMACEUTICAL"
        for item in comment.get("texts", [])
    ]
    if not texts or not all(isinstance(item, str) and item.strip() for item in texts):
        raise ValueError("UniProt entry has no pharmaceutical text")
    return texts


def get_uniprot(protocol: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source = protocol["sources"]["uniprot"]
    parameters = urllib.parse.urlencode(
        {
            "query": source["query"],
            "size": source["size"],
            "fields": source["fields"],
            "format": "json",
        }
    )
    search_url = f"{source['search_endpoint']}?{parameters}"
    raw, final_url = fetch(search_url)
    search = json.loads(raw)
    observed = sorted(item["primaryAccession"] for item in search["results"])
    if observed != sorted(source["accessions"]):
        raise ValueError(f"UniProt search returned {observed}, expected {source['accessions']}")
    receipt = {
        "url": final_url,
        "retrieved_bytes": len(raw),
        "result_accessions": observed,
    }
    records = []
    for accession in source["accessions"]:
        url = source["entry_pattern"].replace("<accession>", accession)
        entry_raw, entry_url = fetch(url)
        entry = json.loads(entry_raw)
        if entry.get("primaryAccession") != accession:
            raise ValueError(f"UniProt accession changed at {url}")
        description = entry.get("proteinDescription", {})
        name = description.get("recommendedName", {}).get("fullName", {}).get("value")
        if not name:
            name = description.get("submissionNames", [{}])[0].get("fullName", {}).get("value")
        audit = entry.get("entryAudit", {})
        records.append(
            {
                "source": "uniprot",
                "key": accession,
                "url": entry_url,
                "retrieved_bytes": len(entry_raw),
                "entry_type": entry.get("entryType"),
                "entry_version": audit.get("entryVersion"),
                "annotation_date": audit.get("lastAnnotationUpdateDate"),
                "protein_name": name,
                "pharmaceutical_text": pharmaceutical_text(entry),
            }
        )
    return receipt, records


def section_paragraphs(
    root: ElementTree.Element, code: str, count: int, namespace: str
) -> list[str]:
    ns = {"s": namespace}
    matching = [
        section
        for section in root.findall(".//s:section", ns)
        if (section.find("s:code", ns) is not None)
        and section.find("s:code", ns).get("code") == code  # type: ignore[union-attr]
    ]
    if len(matching) != 1:
        raise ValueError(f"DailyMed section {code} is absent or duplicated")
    text = matching[0].find("s:text", ns)
    if text is None:
        raise ValueError(f"DailyMed section {code} has no text")
    paragraphs = [
        " ".join(" ".join(node.itertext()).split()) for node in text.findall("s:paragraph", ns)
    ]
    if len(paragraphs) < count or not all(paragraphs[:count]):
        raise ValueError(f"DailyMed section {code} lacks {count} paragraphs")
    return paragraphs[:count]


def get_dailymed(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    source = protocol["sources"]["dailymed"]
    ns = {"s": source["namespace"]}
    records = []
    for label in source["labels"]:
        setid = label["setid"]
        url = source["endpoint_pattern"].replace("<setid>", setid)
        raw, final_url = fetch(url)
        root = ElementTree.fromstring(raw)
        if root.find("s:setId", ns) is None or root.find("s:setId", ns).get("root") != setid:  # type: ignore[union-attr]
            raise ValueError(f"DailyMed setid differs at {url}")
        identity = root.find("s:id", ns)
        version = root.find("s:versionNumber", ns)
        effective = root.find("s:effectiveTime", ns)
        codes = source["section_codes"]
        records.append(
            {
                "source": "dailymed",
                "key": setid,
                "url": final_url,
                "retrieved_bytes": len(raw),
                "document_id": identity.get("root") if identity is not None else None,
                "version": int(version.get("value")) if version is not None else None,
                "effective_time": effective.get("value") if effective is not None else None,
                "description": section_paragraphs(
                    root, codes["description"], label["description_paragraphs"], source["namespace"]
                ),
                "mechanism": section_paragraphs(
                    root, codes["mechanism"], label["mechanism_paragraphs"], source["namespace"]
                ),
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download",))
    parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        receipt, uniprot = get_uniprot(protocol)
        dailymed = get_dailymed(protocol)
        snapshot = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "protocol_id": PROTOCOL_ID,
            "fetched_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "uniprot_search": receipt,
            "records": [*uniprot, *dailymed],
        }
        result = audit_records(snapshot, protocol)
        target = snapshot_file(LAB, protocol)
        target.write_text(render_snapshot(snapshot), encoding="utf-8")
        audit_records(load_snapshot(LAB, protocol), protocol)
    except (OSError, ValueError, KeyError, TypeError, ElementTree.ParseError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        f"Fetched {len(snapshot['records'])} source records for {result['entity_count']} entities "
        f"at {snapshot['fetched_at_utc']}; wrote {target}"
    )
    for record in snapshot["records"]:
        print(
            f"{record['source']} {record['key']} {record['retrieved_bytes']} bytes {record['url']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
