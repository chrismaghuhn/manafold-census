"""Discover the configured Scryfall bulk source and propose refresh locks."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import urlopen as stdlib_urlopen
from uuid import UUID

from ..models import SourceArtifact, SourceLock
from .config import AcquisitionSpec, load_acquisition_spec
from .errors import SourceAcquisitionError
from .transfer import download_source, write_source_lock

_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True, slots=True)
class BulkDataObservation:
    """The source-provided facts needed to refresh one bulk snapshot."""

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


def parse_oracle_cards_metadata(
    document: object, *, spec: AcquisitionSpec | None = None
) -> BulkDataObservation:
    """Parse the current configured Scryfall bulk-data contract only."""

    source_spec = spec or load_acquisition_spec()
    if not isinstance(document, dict) or document.get("object") != "list":
        raise SourceAcquisitionError("bulk discovery response must be a list object")
    raw_data = document.get("data")
    if not isinstance(raw_data, list):
        raise SourceAcquisitionError("bulk discovery response data must be an array")
    matches = [
        item
        for item in raw_data
        if isinstance(item, dict) and item.get("type") == source_spec.bulk_type
    ]
    if len(matches) != 1:
        raise SourceAcquisitionError(
            f"bulk discovery must contain exactly one {source_spec.bulk_type} entry; "
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
    download_uri = entry.get(source_spec.download_field)
    if not isinstance(download_uri, str) or not download_uri.strip():
        raise SourceAcquisitionError(
            f"oracle_cards {source_spec.download_field} is required"
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
        bulk_type=source_spec.bulk_type,
        name=name,
        updated_at=updated_at,
        download_uri=download_uri,
        download_field=source_spec.download_field,
        advertised_format=source_spec.expected_format,
        compressed_size=compressed_size,
    )


def _discovery_request(spec: AcquisitionSpec) -> Request:
    return Request(
        spec.discovery_uri,
        headers={
            "User-Agent": spec.user_agent,
            "Accept": spec.discovery_accept,
        },
    )


def discover_oracle_cards(
    *,
    opener: _Urlopen | None = None,
    spec: AcquisitionSpec | None = None,
) -> BulkDataObservation:
    """Perform one read-only discovery request using the committed config."""

    source_spec = spec or load_acquisition_spec()
    open_url = opener or _DEFAULT_OPENER
    request = _discovery_request(source_spec)
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
    return parse_oracle_cards_metadata(document, spec=source_spec)


def refresh_current_source(
    *,
    cache_root: str | Path,
    proposal_path: str | Path,
    opener: _Urlopen | None = None,
    spec: AcquisitionSpec | None = None,
) -> tuple[BulkDataObservation, SourceArtifact, SourceLock]:
    """Discover current bytes, cache them by digest, and write a proposal."""

    source_spec = spec or load_acquisition_spec()
    observation = discover_oracle_cards(opener=opener, spec=source_spec)
    artifact = download_source(observation, cache_root, opener=opener, spec=source_spec)
    lock = write_source_lock(proposal_path, artifact)
    return observation, artifact, lock
