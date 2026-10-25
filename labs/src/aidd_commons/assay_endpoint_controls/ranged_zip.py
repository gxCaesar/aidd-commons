"""Read one member out of a remote zip container with HTTP range requests.

The PubChem BioAssay FTP area stores the per-assay records inside ranged
container zips: one zip holds every assay in a block of one thousand assay
identifiers, and each assay is one gzip member inside that zip. The first
container this lab reads is 779,560,315 bytes and the second is 1,313,522,439
bytes, so downloading a whole container to obtain one 13 kilobyte assay record
is not an option. This module reads the container's end-of-central-directory
record and its central directory with byte-range requests, locates the one
member, and then reads only that member's bytes.

The reader is deliberately small and does nothing else: it does not know about
assays, it does not decompress gzip, and it never writes to disk. The caller
decides what a member means.

Nothing here is specific to PubChem; the same reader works for any zip served
over HTTP with byte-range support.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Callable
from dataclasses import dataclass

#: Signature of an end-of-central-directory record.
_EOCD_SIGNATURE = b"PK\x05\x06"
#: Signature of a central-directory file header.
_CENTRAL_SIGNATURE = b"PK\x01\x02"
#: Signature of a local file header.
_LOCAL_SIGNATURE = b"PK\x03\x04"
#: The longest possible trailing comment, which bounds where the
#: end-of-central-directory record can sit.
_MAX_COMMENT_BYTES = 0xFFFF
#: Every member of the containers this lab reads is below this size, so the
#: 32-bit fields in the central directory are exact.
_MAX_MEMBER_BYTES = 0xFFFFFFFF

RangeFetcher = Callable[[str, int, int], bytes]


class RemoteZipError(RuntimeError):
    """Raised when a remote container cannot be read as a zip archive."""


@dataclass(frozen=True)
class ZipEntry:
    """One member of a zip archive, as described by the central directory."""

    name: str
    compression_method: int
    compressed_size: int
    uncompressed_size: int
    crc32: int
    local_header_offset: int


def _read_range(url: str, start: int, end: int, fetch: RangeFetcher) -> bytes:
    """Read the inclusive byte range ``start`` to ``end`` from ``url``."""
    if end < start:
        raise RemoteZipError(f"invalid byte range {start}-{end} for {url}")
    payload = fetch(url, start, end)
    expected = end - start + 1
    if len(payload) != expected:
        raise RemoteZipError(
            f"range {start}-{end} of {url} returned {len(payload)} bytes, expected {expected}"
        )
    return payload


def read_central_directory(
    url: str,
    container_bytes: int,
    *,
    fetch: RangeFetcher,
) -> dict[str, ZipEntry]:
    """Return every member of the remote container, keyed by member name.

    ``container_bytes`` is the length of the container as declared by the
    protocol. The reader uses it to locate the end-of-central-directory record
    and checks that the central directory it reads lies inside the container,
    so a container that has been reissued under the same name is a contract
    violation rather than a silent change.
    """
    if container_bytes < 22:
        raise RemoteZipError(f"container {url} is too short to be a zip archive")

    tail_start = max(0, container_bytes - (_MAX_COMMENT_BYTES + 22))
    tail = _read_range(url, tail_start, container_bytes - 1, fetch)
    eocd_offset = tail.rfind(_EOCD_SIGNATURE)
    if eocd_offset < 0:
        raise RemoteZipError(f"container {url} has no end-of-central-directory record")
    eocd = tail[eocd_offset : eocd_offset + 22]
    if len(eocd) < 22:
        raise RemoteZipError(f"container {url} has a truncated end-of-central-directory record")
    (
        _signature,
        _disk,
        _central_disk,
        _entries_on_disk,
        entry_count,
        central_size,
        central_offset,
        comment_length,
    ) = struct.unpack("<IHHHHIIH", eocd)
    if comment_length > _MAX_COMMENT_BYTES:
        raise RemoteZipError(f"container {url} declares an impossible comment length")
    if entry_count == 0xFFFF or central_size == 0xFFFFFFFF or central_offset == 0xFFFFFFFF:
        raise RemoteZipError(
            f"container {url} needs the zip64 format, which this reader does not implement"
        )
    if central_offset + central_size > container_bytes:
        raise RemoteZipError(f"container {url} declares a central directory past its own end")

    central = _read_range(url, central_offset, central_offset + central_size - 1, fetch)
    entries: dict[str, ZipEntry] = {}
    position = 0
    while position < len(central):
        if central[position : position + 4] != _CENTRAL_SIGNATURE:
            raise RemoteZipError(f"container {url} has a malformed central directory")
        (
            _version_made,
            _version_needed,
            _flags,
            compression_method,
            _modified_time,
            _modified_date,
            crc32,
            compressed_size,
            uncompressed_size,
            name_length,
            extra_length,
            member_comment_length,
            _disk_start,
            _internal_attributes,
            _external_attributes,
            local_header_offset,
        ) = struct.unpack("<HHHHHHIIIHHHHHII", central[position + 4 : position + 46])
        name_start = position + 46
        name = central[name_start : name_start + name_length].decode("utf-8")
        if compressed_size > _MAX_MEMBER_BYTES or uncompressed_size > _MAX_MEMBER_BYTES:
            raise RemoteZipError(f"member {name} of {url} needs the zip64 format")
        entries[name] = ZipEntry(
            name=name,
            compression_method=compression_method,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            crc32=crc32,
            local_header_offset=local_header_offset,
        )
        position = name_start + name_length + extra_length + member_comment_length
    if len(entries) != entry_count:
        raise RemoteZipError(
            f"container {url} declares {entry_count} members but its central directory "
            f"describes {len(entries)}"
        )
    return entries


def read_member(url: str, entry: ZipEntry, *, fetch: RangeFetcher) -> bytes:
    """Read one member's bytes out of the remote container.

    The member's local file header is read first so that the data offset and
    the declared compression method come from the archive itself rather than
    from an assumption, and the CRC-32 of the stored bytes is checked against
    the value the central directory records.
    """
    header = _read_range(url, entry.local_header_offset, entry.local_header_offset + 29, fetch)
    if header[:4] != _LOCAL_SIGNATURE:
        raise RemoteZipError(f"member {entry.name} has no local file header")
    (
        _version,
        _flags,
        compression_method,
        _modified_time,
        _modified_date,
        _crc32,
        _compressed_size,
        _uncompressed_size,
        name_length,
        extra_length,
    ) = struct.unpack("<HHHHHIIIHH", header[4:30])
    if compression_method != entry.compression_method:
        raise RemoteZipError(
            f"member {entry.name} changes compression method between the central directory "
            "and its local file header"
        )
    data_start = entry.local_header_offset + 30 + name_length + extra_length
    data_end = data_start + entry.compressed_size - 1
    stored = _read_range(url, data_start, data_end, fetch)
    if compression_method == 0:
        payload = stored
    elif compression_method == 8:
        payload = zlib.decompress(stored, -15)
    else:
        raise RemoteZipError(
            f"member {entry.name} uses compression method {compression_method}, "
            "which this reader does not implement"
        )
    if len(payload) != entry.uncompressed_size:
        raise RemoteZipError(
            f"member {entry.name} decompressed to {len(payload)} bytes, "
            f"the archive declares {entry.uncompressed_size}"
        )
    if zlib.crc32(payload) & 0xFFFFFFFF != entry.crc32:
        raise RemoteZipError(f"member {entry.name} failed its CRC-32 check")
    return payload
