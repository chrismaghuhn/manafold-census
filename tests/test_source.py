import gzip
import hashlib
import io
import json
from email.message import Message
from pathlib import Path

import pytest

from manafold_census.models import SourceArtifact, SourceLock
from manafold_census.source.scryfall import (
    BulkDataObservation,
    SourceAcquisitionError,
    acquire_current_source,
    cache_path_for,
    discover_oracle_cards,
    download_source,
    parse_oracle_cards_metadata,
    write_source_lock,
)

BULK_ID = "11111111-1111-4111-8111-111111111111"
DOWNLOAD_URI = "https://data.scryfall.io/oracle-cards/oracle-cards-test.jsonl.gz"


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        headers: dict[str, str] | None = None,
        status: int = 200,
    ) -> None:
        self._stream = io.BytesIO(body)
        message = Message()
        for name, value in (headers or {}).items():
            message[name] = value
        self.headers = message
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, amount: int = -1) -> bytes:
        return self._stream.read(amount)


def _metadata(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "object": "bulk_data",
        "id": BULK_ID,
        "type": "oracle_cards",
        "name": "Oracle Cards",
        "updated_at": "2026-09-12T09:01:52.708+00:00",
        "jsonl_download_uri": DOWNLOAD_URI,
        "compressed_size": 10,
    }
    entry.update(overrides)
    return {"object": "list", "data": [entry]}


def _gzip_payload() -> bytes:
    raw = (
        b'{"object":"card","oracle_id":"00000000-0000-4000-8000-000000000000",'
        b'"id":"00000000-0000-4000-8000-000000000001","name":"Test Card"}\n'
    )
    return gzip.compress(raw)


def test_discovery_selects_exact_oracle_cards_entry_and_sends_headers() -> None:
    requests: list[object] = []

    def opener(request: object, **_kwargs: object) -> FakeResponse:
        requests.append(request)
        return FakeResponse(json.dumps(_metadata()).encode("utf-8"))

    observation = discover_oracle_cards(opener=opener)

    assert observation == BulkDataObservation(
        source_id=BULK_ID,
        bulk_type="oracle_cards",
        name="Oracle Cards",
        updated_at="2026-09-12T09:01:52.708+00:00",
        download_uri=DOWNLOAD_URI,
        download_field="jsonl_download_uri",
        advertised_format="gzip-jsonl",
        compressed_size=10,
    )
    request = requests[0]
    assert request.full_url == "https://api.scryfall.com/bulk-data"  # type: ignore[attr-defined]
    assert request.get_header("User-agent") == (  # type: ignore[attr-defined]
        "manafold-census/0.1.0 (Task 01 source acquisition)"
    )
    assert request.get_header("Accept") == "application/json"  # type: ignore[attr-defined]


def test_metadata_parser_rejects_missing_or_duplicate_oracle_cards_entries() -> None:
    missing = {"object": "list", "data": []}
    duplicate = _metadata()
    duplicate["data"] = [duplicate["data"][0], duplicate["data"][0]]  # type: ignore[index]

    with pytest.raises(SourceAcquisitionError, match="oracle_cards entry"):
        parse_oracle_cards_metadata(missing)
    with pytest.raises(SourceAcquisitionError, match="exactly one"):
        parse_oracle_cards_metadata(duplicate)


@pytest.mark.parametrize(
    "mutation",
    [
        {"jsonl_download_uri": None},
        {"jsonl_download_uri": "http://data.example/source.jsonl.gz"},
        {"id": "not-a-uuid"},
        {"type": "unique_artwork"},
    ],
)
def test_metadata_parser_rejects_unsupported_current_contract(
    mutation: dict[str, object],
) -> None:
    document = _metadata(**mutation)
    with pytest.raises(SourceAcquisitionError):
        parse_oracle_cards_metadata(document)


def test_discovery_http_failure_is_explicit() -> None:
    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        raise OSError("network unavailable")

    with pytest.raises(SourceAcquisitionError, match="discovery failed"):
        discover_oracle_cards(opener=opener)


def test_download_streams_exact_bytes_and_promotes_atomically(tmp_path: Path) -> None:
    payload = _gzip_payload()
    observation = parse_oracle_cards_metadata(_metadata(compressed_size=len(payload)))
    requests: list[object] = []

    def opener(request: object, **_kwargs: object) -> FakeResponse:
        requests.append(request)
        return FakeResponse(
            payload,
            headers={
                "Content-Type": "application/gzip",
                "Content-Length": str(len(payload)),
            },
        )

    destination = tmp_path / "oracle-cards.jsonl.gz"
    artifact = download_source(observation, destination, opener=opener)

    assert destination.read_bytes() == payload
    assert artifact == SourceArtifact(
        source_id=BULK_ID,
        locator=DOWNLOAD_URI,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
        media_type="application/gzip",
    )
    assert not list(tmp_path.glob("*.tmp"))
    request = requests[0]
    assert request.get_header("User-agent") == (  # type: ignore[attr-defined]
        "manafold-census/0.1.0 (Task 01 source acquisition)"
    )
    assert request.get_header("Accept") == "application/gzip"  # type: ignore[attr-defined]


def test_download_rejects_truncated_gzip_without_promoting_it(tmp_path: Path) -> None:
    payload = _gzip_payload()[:-8]
    observation = parse_oracle_cards_metadata(_metadata(compressed_size=None))
    destination = tmp_path / "oracle-cards.jsonl.gz"

    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        return FakeResponse(payload, headers={"Content-Type": "application/gzip"})

    with pytest.raises(SourceAcquisitionError, match="gzip"):
        download_source(observation, destination, opener=opener)
    assert not destination.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_download_http_failure_does_not_mutate_existing_destination(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "oracle-cards.jsonl.gz"
    observation = parse_oracle_cards_metadata(_metadata(compressed_size=None))

    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        raise OSError("download unavailable")

    with pytest.raises(SourceAcquisitionError, match="download failed"):
        download_source(observation, destination, opener=opener)
    assert not destination.exists()


def test_existing_cache_requires_and_matches_expected_identity(tmp_path: Path) -> None:
    payload = _gzip_payload()
    destination = tmp_path / "oracle-cards.jsonl.gz"
    destination.write_bytes(payload)
    observation = parse_oracle_cards_metadata(_metadata(compressed_size=len(payload)))

    reused = download_source(
        observation,
        destination,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        expected_byte_length=len(payload),
        opener=lambda *_args, **_kwargs: pytest.fail("cache should be reused"),
    )
    assert reused.sha256 == hashlib.sha256(payload).hexdigest()

    destination.write_bytes(b"wrong cache")
    with pytest.raises(SourceAcquisitionError, match="cached source digest mismatch"):
        download_source(
            observation,
            destination,
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            expected_byte_length=len(payload),
            opener=lambda *_args, **_kwargs: pytest.fail(
                "wrong cache must fail closed"
            ),
        )


def test_source_lock_creation_round_trips_exact_source_artifact(tmp_path: Path) -> None:
    payload = _gzip_payload()
    source_path = tmp_path / "source.jsonl.gz"
    source_path.write_bytes(payload)
    observation = parse_oracle_cards_metadata(_metadata(compressed_size=len(payload)))
    artifact = SourceArtifact(
        source_id=observation.source_id,
        locator=observation.download_uri,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
        media_type="application/gzip",
    )
    lock_path = tmp_path / "scryfall-oracle-v1.json"

    lock = write_source_lock(lock_path, artifact)
    restored = SourceLock.from_wire(json.loads(lock_path.read_text(encoding="utf-8")))

    assert restored == lock
    assert restored.digest() == lock.digest()
    assert restored.artifacts[0].sha256 == hashlib.sha256(payload).hexdigest()


def test_acquire_current_source_writes_cache_and_lock(tmp_path: Path) -> None:
    payload = _gzip_payload()
    metadata = _metadata(compressed_size=len(payload))
    responses = [
        FakeResponse(json.dumps(metadata).encode("utf-8")),
        FakeResponse(payload, headers={"Content-Type": "application/gzip"}),
    ]

    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        return responses.pop(0)

    lock_path = tmp_path / "source-locks" / "scryfall-oracle-v1.json"
    observation, artifact, lock = acquire_current_source(
        cache_root=tmp_path / ".cache" / "sources" / "scryfall",
        lock_path=lock_path,
        opener=opener,
    )

    assert observation.source_id == BULK_ID
    assert artifact.sha256 == hashlib.sha256(payload).hexdigest()
    assert cache_path_for(
        tmp_path / ".cache" / "sources" / "scryfall", BULK_ID
    ).is_file()
    assert lock.artifacts == (artifact,)
    assert (
        json.loads(lock_path.read_text(encoding="utf-8"))["artifacts"][0]["source_id"]
        == BULK_ID
    )
