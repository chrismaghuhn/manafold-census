"""SHA-256 helpers and domain-separated semantic digests."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .canonical import JSONValue, canonical_json_bytes

SOURCE_LOCK_DOMAIN: Final = "census.source-lock.v1"
DATASET_MANIFEST_DOMAIN: Final = "census.dataset-manifest.v1"
STUDY_SPEC_DOMAIN: Final = "census.study-spec.v1"
ARTIFACT_MANIFEST_DOMAIN: Final = "census.artifact-manifest.v1"
REPRODUCTION_DOMAIN: Final = "census.reproduction.v1"

_DOMAIN_PATTERN = re.compile(r"^census\.[a-z0-9]+(?:-[a-z0-9]+)*\.v[0-9]+$")
_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class FileMeasurement:
    """Digest and byte length measured from one complete file stream."""

    sha256: str
    byte_length: int


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of exact bytes."""

    if not isinstance(data, bytes):
        raise TypeError("sha256_bytes requires bytes")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Return a streamed SHA-256 digest for a file."""

    return measure_file(path).sha256


def measure_file(path: str | Path) -> FileMeasurement:
    """Measure digest and byte length from the same opened file stream."""

    digest = hashlib.sha256()
    byte_length = 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_SIZE):
            digest.update(chunk)
            byte_length += len(chunk)
    return FileMeasurement(sha256=digest.hexdigest(), byte_length=byte_length)


def domain_digest(domain: str, payload: JSONValue) -> str:
    """Hash a canonical payload under a versioned ASCII domain."""

    if not isinstance(domain, str) or not _DOMAIN_PATTERN.fullmatch(domain):
        raise ValueError("domain must be a non-empty versioned census domain")
    try:
        domain_bytes = domain.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError("domain must contain ASCII characters only") from error
    return sha256_bytes(domain_bytes + b"\x00" + canonical_json_bytes(payload))
