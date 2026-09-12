import gzip
import hashlib
import io
import json
from dataclasses import replace
from email.message import Message
from pathlib import Path

import pytest

from manafold_census.models import SourceArtifact, SourceLock
from manafold_census.source.config import load_acquisition_spec
from manafold_census.source.scryfall import (
    BulkDataObservation,
    SourceAcquisitionError,
    discover_oracle_cards,
    parse_oracle_cards_metadata,
    refresh_current_source,
)
from manafold_census.source.transfer import (
    cache_path_for,
    download_source,
    fetch_pinned_source,
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


def _gzip_payload(name: str = "Test Card") -> bytes:
    raw = (
        b'{"object":"card","oracle_id":"00000000-0000-4000-8000-000000000000",'
        b'"id":"00000000-0000-4000-8000-000000000001","name":"'
        + name.encode("utf-8")
        + b'"}\n'
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


def test_discovery_uses_the_loaded_acquisition_spec() -> None:
    spec = load_acquisition_spec()
    custom = replace(
        spec,
        discovery_uri="https://example.test/custom-bulk-data",
        user_agent="custom-census-agent/1.0",
        discovery_accept="application/custom+json",
    )
    requests: list[object] = []

    def opener(request: object, **_kwargs: object) -> FakeResponse:
        requests.append(request)
        return FakeResponse(json.dumps(_metadata()).encode("utf-8"))

    discover_oracle_cards(opener=opener, spec=custom)

    request = requests[0]
    assert request.full_url == "https://example.test/custom-bulk-data"  # type: ignore[attr-defined]
    assert request.get_header("User-agent") == "custom-census-agent/1.0"  # type: ignore[attr-defined]
    assert request.get_header("Accept") == "application/custom+json"  # type: ignore[attr-defined]


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

    cache_root = tmp_path / "cache"
    artifact = download_source(observation, cache_root, opener=opener)

    destination = cache_path_for(cache_root, artifact.sha256)
    assert destination.read_bytes() == payload
    assert artifact == SourceArtifact(
        source_id=BULK_ID,
        locator=DOWNLOAD_URI,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
        media_type="application/gzip",
    )
    assert not list(cache_root.glob("*.tmp"))
    request = requests[0]
    assert request.get_header("User-agent") == (  # type: ignore[attr-defined]
        "manafold-census/0.1.0 (Task 01 source acquisition)"
    )
    assert request.get_header("Accept") == "application/gzip"  # type: ignore[attr-defined]


def test_download_rejects_truncated_gzip_without_promoting_it(tmp_path: Path) -> None:
    payload = _gzip_payload()[:-8]
    observation = parse_oracle_cards_metadata(_metadata(compressed_size=None))
    cache_root = tmp_path / "cache"

    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        return FakeResponse(payload, headers={"Content-Type": "application/gzip"})

    with pytest.raises(SourceAcquisitionError, match="gzip"):
        download_source(observation, cache_root, opener=opener)
    assert not list(cache_root.glob("*.jsonl.gz"))
    assert not list(cache_root.glob("*.tmp"))


def test_download_http_failure_does_not_mutate_existing_destination(
    tmp_path: Path,
) -> None:
    cache_root = tmp_path / "cache"
    observation = parse_oracle_cards_metadata(_metadata(compressed_size=None))

    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        raise OSError("download unavailable")

    with pytest.raises(SourceAcquisitionError, match="download failed"):
        download_source(observation, cache_root, opener=opener)
    assert not list(cache_root.glob("*.jsonl.gz"))


def test_existing_cache_requires_and_matches_expected_identity(tmp_path: Path) -> None:
    payload = _gzip_payload()
    cache_root = tmp_path / "cache"
    destination = cache_path_for(cache_root, hashlib.sha256(payload).hexdigest())
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    artifact = SourceArtifact(
        source_id=BULK_ID,
        locator=DOWNLOAD_URI,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
        media_type="application/gzip",
    )

    reused = fetch_pinned_source(
        artifact,
        cache_root,
        opener=lambda *_args, **_kwargs: pytest.fail("cache should be reused"),
    )
    assert reused.sha256 == hashlib.sha256(payload).hexdigest()

    destination.write_bytes(b"wrong cache")
    with pytest.raises(SourceAcquisitionError, match="cached source digest mismatch"):
        fetch_pinned_source(
            artifact,
            cache_root,
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


def test_refresh_current_source_writes_content_addressed_cache_and_proposal(
    tmp_path: Path,
) -> None:
    payload = _gzip_payload()
    metadata = _metadata(compressed_size=len(payload))
    responses = [
        FakeResponse(json.dumps(metadata).encode("utf-8")),
        FakeResponse(payload, headers={"Content-Type": "application/gzip"}),
    ]

    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        return responses.pop(0)

    proposal_path = tmp_path / "source-locks" / "scryfall-oracle-v1.proposed.json"
    observation, artifact, lock = refresh_current_source(
        cache_root=tmp_path / ".cache" / "sources" / "scryfall",
        proposal_path=proposal_path,
        opener=opener,
    )

    assert observation.source_id == BULK_ID
    assert artifact.sha256 == hashlib.sha256(payload).hexdigest()
    assert cache_path_for(
        tmp_path / ".cache" / "sources" / "scryfall", artifact.sha256
    ).is_file()
    assert lock.artifacts == (artifact,)
    assert (
        json.loads(proposal_path.read_text(encoding="utf-8"))["artifacts"][0][
            "source_id"
        ]
        == BULK_ID
    )


def test_refresh_keeps_same_source_id_snapshots_separate(tmp_path: Path) -> None:
    payload_a = _gzip_payload()
    payload_b = _gzip_payload("Next Card")
    metadata_a = _metadata(
        jsonl_download_uri=DOWNLOAD_URI,
        compressed_size=len(payload_a),
    )
    metadata_b = _metadata(
        jsonl_download_uri=DOWNLOAD_URI.replace("test", "next"),
        compressed_size=len(payload_b),
    )
    responses = [
        FakeResponse(json.dumps(metadata_a).encode("utf-8")),
        FakeResponse(payload_a, headers={"Content-Type": "application/gzip"}),
        FakeResponse(json.dumps(metadata_b).encode("utf-8")),
        FakeResponse(payload_b, headers={"Content-Type": "application/gzip"}),
    ]

    def opener(_request: object, **_kwargs: object) -> FakeResponse:
        return responses.pop(0)

    cache_root = tmp_path / "cache"
    _, artifact_a, lock_a = refresh_current_source(
        cache_root=cache_root,
        proposal_path=tmp_path / "proposal-a.json",
        opener=opener,
    )
    _, artifact_b, lock_b = refresh_current_source(
        cache_root=cache_root,
        proposal_path=tmp_path / "proposal-b.json",
        opener=opener,
    )

    assert artifact_a.source_id == artifact_b.source_id == BULK_ID
    assert artifact_a.sha256 != artifact_b.sha256
    assert artifact_a.locator != artifact_b.locator
    assert cache_path_for(cache_root, artifact_a.sha256).is_file()
    assert cache_path_for(cache_root, artifact_b.sha256).is_file()
    assert lock_a.artifacts[0].locator == DOWNLOAD_URI
    assert lock_b.artifacts[0].locator == DOWNLOAD_URI.replace("test", "next")


def test_fetch_pinned_source_uses_lock_locator_without_discovery(
    tmp_path: Path,
) -> None:
    payload = _gzip_payload()
    artifact = SourceArtifact(
        source_id=BULK_ID,
        locator="https://data.scryfall.io/oracle-cards/pinned.jsonl.gz",
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
        media_type="application/gzip",
    )
    requests: list[object] = []

    def opener(request: object, **_kwargs: object) -> FakeResponse:
        requests.append(request)
        return FakeResponse(payload, headers={"Content-Type": "application/gzip"})

    fetched = fetch_pinned_source(artifact, tmp_path / "cache", opener=opener)

    assert fetched == artifact
    assert requests[0].full_url == artifact.locator  # type: ignore[attr-defined]
