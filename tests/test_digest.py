import hashlib

import pytest

from manafold_census.canonical import canonical_json_bytes
from manafold_census.digest import (
    domain_digest,
    measure_file,
    sha256_bytes,
    sha256_file,
)


def test_sha256_bytes_matches_known_digest() -> None:
    assert sha256_bytes(b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_sha256_file_hashes_streamed_file_contents(tmp_path) -> None:
    path = tmp_path / "large-fixture.bin"
    data = (b"0123456789abcdef" * 131073) + b"tail"
    path.write_bytes(data)

    assert sha256_file(path) == hashlib.sha256(data).hexdigest()


def test_measure_file_returns_digest_and_length_from_one_measurement(tmp_path) -> None:
    path = tmp_path / "measured.bin"
    data = b"one-pass source bytes"
    path.write_bytes(data)

    measurement = measure_file(path)

    assert measurement.sha256 == hashlib.sha256(data).hexdigest()
    assert measurement.byte_length == len(data)


def test_domain_digest_uses_ascii_domain_separator_and_canonical_payload() -> None:
    payload = {"b": 2, "a": 1}
    expected = hashlib.sha256(
        b"census.test.v1\x00" + canonical_json_bytes(payload)
    ).hexdigest()

    assert domain_digest("census.test.v1", payload) == expected


@pytest.mark.parametrize("domain", ["census.test", "", "census.T.test.v1", "ä.v1"])
def test_domain_digest_rejects_non_versioned_domains(domain: str) -> None:
    with pytest.raises(ValueError, match="versioned"):
        domain_digest(domain, {})
