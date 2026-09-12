"""Stream, verify, and content-address Scryfall source byte artifacts."""

from __future__ import annotations

import gzip
import os
import re
import tempfile
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import urlopen as stdlib_urlopen

from ..canonical import canonical_json_bytes
from ..digest import measure_file
from ..models import SourceArtifact, SourceLock
from .config import AcquisitionSpec, load_acquisition_spec
from .errors import SourceAcquisitionError

_STREAM_CHUNK_SIZE = 1024 * 1024
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


class _CurrentSource(Protocol):
    @property
    def source_id(self) -> str: ...

    @property
    def download_uri(self) -> str: ...

    @property
    def compressed_size(self) -> int | None: ...


def cache_path_for(cache_root: str | Path, sha256: str) -> Path:
    """Return the content-addressed cache path for one exact byte digest."""

    if not isinstance(sha256, str) or _DIGEST_PATTERN.fullmatch(sha256) is None:
        raise SourceAcquisitionError(
            "cache identity must be a lowercase SHA-256 digest"
        )
    return Path(cache_root) / f"{sha256}.jsonl.gz"


def _request(uri: str, spec: AcquisitionSpec) -> Request:
    return Request(
        uri,
        headers={
            "User-Agent": spec.user_agent,
            "Accept": spec.download_accept,
        },
    )


def _header_content_type(headers: Message, fallback: str) -> str:
    raw_value = headers.get("Content-Type")
    if not isinstance(raw_value, str) or not raw_value.strip():
        return fallback
    return raw_value.split(";", 1)[0].strip() or fallback


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


def _verify_cached_source(
    path: Path,
    *,
    expected_sha256: str,
    expected_byte_length: int,
    source_id: str,
    locator: str,
    media_type: str,
) -> SourceArtifact:
    if not path.is_file():
        raise SourceAcquisitionError("source cache destination is not a file")
    measurement = measure_file(path)
    if measurement.sha256 != expected_sha256:
        raise SourceAcquisitionError("cached source digest mismatch")
    if measurement.byte_length != expected_byte_length:
        raise SourceAcquisitionError("cached source byte length mismatch")
    _verify_complete_gzip(path)
    return SourceArtifact(
        source_id=source_id,
        locator=locator,
        sha256=measurement.sha256,
        byte_length=measurement.byte_length,
        media_type=media_type,
    )


def _download_to_cache(
    *,
    locator: str,
    source_id: str,
    cache_root: str | Path,
    expected_sha256: str | None,
    expected_byte_length: int | None,
    advertised_byte_length: int | None,
    media_type: str | None,
    spec: AcquisitionSpec,
    opener: _Urlopen | None,
) -> SourceArtifact:
    cache_root_path = Path(cache_root)
    cache_root_path.mkdir(parents=True, exist_ok=True)
    if expected_sha256 is not None:
        destination = cache_path_for(cache_root_path, expected_sha256)
        if destination.exists():
            if expected_byte_length is None:
                raise SourceAcquisitionError(
                    "pinned source requires an expected byte length"
                )
            return _verify_cached_source(
                destination,
                expected_sha256=expected_sha256,
                expected_byte_length=expected_byte_length,
                source_id=source_id,
                locator=locator,
                media_type=media_type or "application/gzip",
            )

    open_url = opener or _DEFAULT_OPENER
    request = _request(locator, spec)
    temporary_path: Path | None = None
    response_media_type = media_type or "application/gzip"
    content_length: int | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{source_id}.",
            suffix=".tmp",
            dir=cache_root_path,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with open_url(request, timeout=120.0) as response:
                if not 200 <= response.status < 300:
                    raise SourceAcquisitionError(
                        f"download failed with HTTP status {response.status}"
                    )
                response_media_type = _header_content_type(
                    response.headers, response_media_type
                )
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
        if expected_sha256 is not None and measurement.sha256 != expected_sha256:
            raise SourceAcquisitionError("downloaded source digest mismatch")
        if (
            expected_byte_length is not None
            and measurement.byte_length != expected_byte_length
        ):
            raise SourceAcquisitionError("downloaded source byte length mismatch")
        if (
            advertised_byte_length is not None
            and measurement.byte_length != advertised_byte_length
        ):
            raise SourceAcquisitionError("advertised compressed_size mismatch")
        if content_length is not None and measurement.byte_length != content_length:
            raise SourceAcquisitionError("download Content-Length mismatch")
        _verify_complete_gzip(temporary_path)

        destination = cache_path_for(cache_root_path, measurement.sha256)
        if destination.exists():
            _verify_cached_source(
                destination,
                expected_sha256=measurement.sha256,
                expected_byte_length=measurement.byte_length,
                source_id=source_id,
                locator=locator,
                media_type=response_media_type,
            )
            temporary_path.unlink(missing_ok=True)
            temporary_path = None
        else:
            os.replace(temporary_path, destination)
            temporary_path = None
        return SourceArtifact(
            source_id=source_id,
            locator=locator,
            sha256=measurement.sha256,
            byte_length=measurement.byte_length,
            media_type=response_media_type,
        )
    except SourceAcquisitionError:
        raise
    except (OSError, ValueError) as error:
        raise SourceAcquisitionError(f"download failed: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def download_source(
    observation: _CurrentSource,
    cache_root: str | Path,
    *,
    opener: _Urlopen | None = None,
    spec: AcquisitionSpec | None = None,
) -> SourceArtifact:
    """Refresh one observed source into a SHA-256-addressed cache."""

    source_spec = spec or load_acquisition_spec()
    return _download_to_cache(
        locator=observation.download_uri,
        source_id=observation.source_id,
        cache_root=cache_root,
        expected_sha256=None,
        expected_byte_length=None,
        advertised_byte_length=observation.compressed_size,
        media_type=None,
        spec=source_spec,
        opener=opener,
    )


def fetch_pinned_source(
    artifact: SourceArtifact,
    cache_root: str | Path,
    *,
    opener: _Urlopen | None = None,
    spec: AcquisitionSpec | None = None,
) -> SourceArtifact:
    """Fetch exactly one locked locator and verify its digest and length."""

    source_spec = spec or load_acquisition_spec()
    parsed_uri = urlsplit(artifact.locator)
    if parsed_uri.scheme != "https" or not parsed_uri.netloc:
        raise SourceAcquisitionError("pinned source locator must use HTTPS")
    if not artifact.locator.lower().split("?", 1)[0].endswith(".jsonl.gz"):
        raise SourceAcquisitionError("pinned source locator is not gzip JSONL")
    return _download_to_cache(
        locator=artifact.locator,
        source_id=artifact.source_id,
        cache_root=cache_root,
        expected_sha256=artifact.sha256,
        expected_byte_length=artifact.byte_length,
        advertised_byte_length=None,
        media_type=artifact.media_type,
        spec=source_spec,
        opener=opener,
    )


def write_source_lock(path: str | Path, artifact: SourceArtifact) -> SourceLock:
    """Atomically write one canonical generic SourceLock."""

    lock = SourceLock.build((artifact,))
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{lock_path.name}.",
            suffix=".tmp",
            dir=lock_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(canonical_json_bytes(lock.to_wire()))
        if temporary_path is None:
            raise SourceAcquisitionError("source lock temporary file was not created")
        os.replace(temporary_path, lock_path)
        temporary_path = None
        return lock
    except (OSError, ValueError) as error:
        raise SourceAcquisitionError(f"source lock write failed: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
