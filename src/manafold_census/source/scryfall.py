"""Acquisition of the observed Scryfall ``oracle_cards`` bulk source."""

from __future__ import annotations

import gzip
import json
import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import urlopen as stdlib_urlopen
from uuid import UUID

from ..canonical import canonical_json_bytes
from ..digest import measure_file
from ..models import SourceArtifact, SourceLock

DISCOVERY_URI = "https://api.scryfall.com/bulk-data"
USER_AGENT = "manafold-census/0.1.0 (Task 01 source acquisition)"
DISCOVERY_ACCEPT = "application/json"
DOWNLOAD_ACCEPT = "application/gzip"
EXPECTED_FORMAT = "gzip-jsonl"
DOWNLOAD_FIELD = "jsonl_download_uri"
_STREAM_CHUNK_SIZE = 1024 * 1024
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class SourceAcquisitionError(RuntimeError):
    """Raised when source discovery or acquisition cannot complete safely."""


@dataclass(frozen=True, slots=True)
class BulkDataObservation:
    """The deterministic, source-provided facts needed for one download."""

    source_id: str
    bulk_type: str
    name: str
    updated_at: str | None
    download_uri: str
    download_field: str
    advertised_format: str
    compressed_size: int | None


class _HttpResponse(Protocol):
    status: int
    headers: Message

    def read(self, amount: int = -1) -> bytes: ...

    def __enter__(self) -> _HttpResponse: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> None: ...


_Urlopen = Callable[..., _HttpResponse]
_DEFAULT_OPENER = cast(_Urlopen, stdlib_urlopen)


def _normalize_uuid(field: str, value: object) -> str:
    if not isinstance(value, str) or _UUID_PATTERN.fullmatch(value) is None:
        raise SourceAcquisitionError(f"{field} must be a canonical UUID")
    try:
        return str(UUID(value)).lower()
    except ValueError as error:
        raise SourceAcquisitionError(f"{field} must be a canonical UUID") from error


def _optional_nonnegative_int(field: str, value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise SourceAcquisitionError(f"{field} must be a non-negative integer")
    return value


def parse_oracle_cards_metadata(document: object) -> BulkDataObservation:
    """Parse only the currently observed Scryfall bulk-data contract."""

    if not isinstance(document, dict) or document.get("object") != "list":
        raise SourceAcquisitionError("bulk discovery response must be a list object")
    raw_data = document.get("data")
    if not isinstance(raw_data, list):
        raise SourceAcquisitionError("bulk discovery response data must be an array")
    matches = [
        item
        for item in raw_data
        if isinstance(item, dict) and item.get("type") == "oracle_cards"
    ]
    if len(matches) != 1:
        raise SourceAcquisitionError(
            "bulk discovery must contain exactly one oracle_cards entry; "
            f"found {len(matches)}"
        )
    entry = matches[0]
    if entry.get("object") != "bulk_data":
        raise SourceAcquisitionError("oracle_cards entry must be a bulk_data object")

    source_id = _normalize_uuid("oracle_cards id", entry.get("id"))
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SourceAcquisitionError("oracle_cards name must be non-empty")
    updated_at = entry.get("updated_at")
    if updated_at is not None and (
        not isinstance(updated_at, str) or not updated_at.strip()
    ):
        raise SourceAcquisitionError(
            "updated_at must be a non-empty string when supplied"
        )
    download_uri = entry.get(DOWNLOAD_FIELD)
    if not isinstance(download_uri, str) or not download_uri.strip():
        raise SourceAcquisitionError(
            f"oracle_cards {DOWNLOAD_FIELD} is required for the observed format"
        )
    parsed_uri = urlsplit(download_uri)
    if parsed_uri.scheme != "https" or not parsed_uri.netloc:
        raise SourceAcquisitionError("oracle_cards download URI must use HTTPS")
    if not download_uri.lower().split("?", 1)[0].endswith(".jsonl.gz"):
        raise SourceAcquisitionError("oracle_cards download URI is not gzip JSONL")
    compressed_size = _optional_nonnegative_int(
        "compressed_size", entry.get("compressed_size")
    )
    return BulkDataObservation(
        source_id=source_id,
        bulk_type="oracle_cards",
        name=name,
        updated_at=updated_at,
        download_uri=download_uri,
        download_field=DOWNLOAD_FIELD,
        advertised_format=EXPECTED_FORMAT,
        compressed_size=compressed_size,
    )


def _request(uri: str, accept: str) -> Request:
    return Request(uri, headers={"User-Agent": USER_AGENT, "Accept": accept})


def discover_oracle_cards(
    *,
    opener: _Urlopen | None = None,
    discovery_uri: str = DISCOVERY_URI,
) -> BulkDataObservation:
    """Perform one read-only discovery request for the Oracle bulk entry."""

    open_url = opener or _DEFAULT_OPENER
    request = _request(discovery_uri, DISCOVERY_ACCEPT)
    try:
        with open_url(request, timeout=30.0) as response:
            if not 200 <= response.status < 300:
                raise SourceAcquisitionError(
                    f"discovery failed with HTTP status {response.status}"
                )
            body = response.read()
    except SourceAcquisitionError:
        raise
    except (OSError, ValueError) as error:
        raise SourceAcquisitionError(f"discovery failed: {error}") from error
    try:
        document = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SourceAcquisitionError("discovery returned invalid JSON") from error
    return parse_oracle_cards_metadata(document)


def cache_path_for(cache_root: str | Path, source_id: str) -> Path:
    """Return the safe ignored-cache path for one validated bulk source ID."""

    normalized_id = _normalize_uuid("source_id", source_id)
    return Path(cache_root) / f"{normalized_id}.jsonl.gz"


def _header_content_type(headers: Message) -> str:
    raw_value = headers.get("Content-Type")
    if not isinstance(raw_value, str) or not raw_value.strip():
        return "application/gzip"
    return raw_value.split(";", 1)[0].strip() or "application/gzip"


def _header_length(headers: Message) -> int | None:
    raw_value = headers.get("Content-Length")
    if raw_value is None:
        return None
    try:
        length = int(raw_value)
    except (TypeError, ValueError) as error:
        raise SourceAcquisitionError("download Content-Length is invalid") from error
    if length < 0:
        raise SourceAcquisitionError("download Content-Length is negative")
    return length


def _verify_complete_gzip(path: Path) -> None:
    try:
        with gzip.open(path, "rb") as stream:
            while stream.read(_STREAM_CHUNK_SIZE):
                pass
    except (EOFError, OSError) as error:
        raise SourceAcquisitionError(
            "downloaded source is not a complete gzip stream"
        ) from error


def _check_measurement(
    measurement_sha256: str,
    measurement_length: int,
    *,
    expected_sha256: str | None,
    expected_byte_length: int | None,
    advertised_byte_length: int | None,
    content_length: int | None,
) -> None:
    if expected_sha256 is not None and measurement_sha256 != expected_sha256:
        raise SourceAcquisitionError("downloaded source digest mismatch")
    if expected_byte_length is not None and measurement_length != expected_byte_length:
        raise SourceAcquisitionError("downloaded source byte length mismatch")
    for label, expected in (
        ("advertised compressed_size", advertised_byte_length),
        ("download Content-Length", content_length),
    ):
        if expected is not None and measurement_length != expected:
            raise SourceAcquisitionError(f"{label} mismatch")


def download_source(
    observation: BulkDataObservation,
    destination: str | Path,
    *,
    expected_sha256: str | None = None,
    expected_byte_length: int | None = None,
    opener: _Urlopen | None = None,
) -> SourceArtifact:
    """Download one exact gzip payload, or safely reuse a matching cache file."""

    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        if not destination_path.is_file():
            raise SourceAcquisitionError("source cache destination is not a file")
        if expected_sha256 is None or expected_byte_length is None:
            raise SourceAcquisitionError(
                "existing cached source requires an expected lock identity"
            )
        measurement = measure_file(destination_path)
        if measurement.sha256 != expected_sha256:
            raise SourceAcquisitionError("cached source digest mismatch")
        if measurement.byte_length != expected_byte_length:
            raise SourceAcquisitionError("cached source byte length mismatch")
        if (
            observation.compressed_size is not None
            and measurement.byte_length != observation.compressed_size
        ):
            raise SourceAcquisitionError("cached source advertised length mismatch")
        _verify_complete_gzip(destination_path)
        return SourceArtifact(
            source_id=observation.source_id,
            locator=observation.download_uri,
            sha256=measurement.sha256,
            byte_length=measurement.byte_length,
            media_type="application/gzip",
        )

    open_url = opener or _DEFAULT_OPENER
    request = _request(observation.download_uri, DOWNLOAD_ACCEPT)
    temporary_path: Path | None = None
    media_type = "application/gzip"
    content_length: int | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{observation.source_id}.",
            suffix=".tmp",
            dir=destination_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with open_url(request, timeout=120.0) as response:
                if not 200 <= response.status < 300:
                    raise SourceAcquisitionError(
                        f"download failed with HTTP status {response.status}"
                    )
                media_type = _header_content_type(response.headers)
                content_length = _header_length(response.headers)
                while True:
                    chunk = response.read(_STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    if not isinstance(chunk, bytes):
                        raise SourceAcquisitionError("download returned non-byte data")
                    temporary.write(chunk)
        if temporary_path is None:
            raise SourceAcquisitionError("download temporary file was not created")
        measurement = measure_file(temporary_path)
        _check_measurement(
            measurement.sha256,
            measurement.byte_length,
            expected_sha256=expected_sha256,
            expected_byte_length=expected_byte_length,
            advertised_byte_length=observation.compressed_size,
            content_length=content_length,
        )
        _verify_complete_gzip(temporary_path)
        os.replace(temporary_path, destination_path)
        temporary_path = None
        return SourceArtifact(
            source_id=observation.source_id,
            locator=observation.download_uri,
            sha256=measurement.sha256,
            byte_length=measurement.byte_length,
            media_type=media_type,
        )
    except SourceAcquisitionError:
        raise
    except (OSError, ValueError) as error:
        raise SourceAcquisitionError(f"download failed: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_source_lock(path: str | Path, artifact: SourceArtifact) -> SourceLock:
    """Write one canonical generic SourceLock for the exact artifact."""

    lock = SourceLock.build((artifact,))
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))
    return lock


def _read_existing_lock(path: Path) -> SourceLock | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
        return SourceLock.from_wire(document)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SourceAcquisitionError(
            f"existing source lock is invalid: {error}"
        ) from error


def acquire_current_source(
    *,
    cache_root: str | Path,
    lock_path: str | Path,
    opener: _Urlopen | None = None,
) -> tuple[BulkDataObservation, SourceArtifact, SourceLock]:
    """Discover, download, and explicitly write the current source lock."""

    observation = discover_oracle_cards(opener=opener)
    destination = cache_path_for(cache_root, observation.source_id)
    existing_lock = _read_existing_lock(Path(lock_path))
    expected_sha256: str | None = None
    expected_byte_length: int | None = None
    if existing_lock is not None:
        for artifact in existing_lock.artifacts:
            if artifact.source_id == observation.source_id:
                expected_sha256 = artifact.sha256
                expected_byte_length = artifact.byte_length
                break
    artifact = download_source(
        observation,
        destination,
        expected_sha256=expected_sha256,
        expected_byte_length=expected_byte_length,
        opener=opener,
    )
    lock = write_source_lock(lock_path, artifact)
    return observation, artifact, lock
