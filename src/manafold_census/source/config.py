"""Typed loading for the committed Scryfall acquisition specification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from ..resources import project_data_root

_CONFIG_RELATIVE_PATH = Path("config") / "sources" / "scryfall-oracle.v1.json"
_CONFIG_KEYS = {
    "schema",
    "source_family",
    "bulk_type",
    "discovery_uri",
    "expected_format",
    "download_field",
    "user_agent",
    "discovery_accept",
    "download_accept",
}


class AcquisitionConfigError(ValueError):
    """Raised when the committed acquisition configuration is invalid."""


def _required_text(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcquisitionConfigError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class AcquisitionSpec:
    """The source-discovery inputs shared by refresh and fetch operations."""

    schema: str
    source_family: str
    bulk_type: str
    discovery_uri: str
    expected_format: str
    download_field: str
    user_agent: str
    discovery_accept: str
    download_accept: str

    def __post_init__(self) -> None:
        if self.schema != "census.source-acquisition.v1":
            raise AcquisitionConfigError("unsupported acquisition config schema")
        if self.source_family != "scryfall":
            raise AcquisitionConfigError("Task 01 requires the Scryfall source family")
        if self.bulk_type != "oracle_cards":
            raise AcquisitionConfigError("Task 01 requires the oracle_cards bulk type")
        if self.expected_format != "gzip-jsonl":
            raise AcquisitionConfigError("Task 01 supports only gzip-jsonl")
        for field in (
            "discovery_uri",
            "download_field",
            "user_agent",
            "discovery_accept",
            "download_accept",
        ):
            _required_text(field, getattr(self, field))
        parsed_uri = urlsplit(self.discovery_uri)
        if parsed_uri.scheme != "https" or not parsed_uri.netloc:
            raise AcquisitionConfigError("discovery_uri must use HTTPS")


def load_acquisition_spec(path: str | Path | None = None) -> AcquisitionSpec:
    """Load the one committed source-discovery configuration."""

    config_path = (
        Path(path) if path is not None else project_data_root() / _CONFIG_RELATIVE_PATH
    )
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise AcquisitionConfigError(
            f"acquisition config could not be read: {error}"
        ) from error
    if not isinstance(document, dict):
        raise AcquisitionConfigError("acquisition config must be an object")
    if set(document) != _CONFIG_KEYS:
        raise AcquisitionConfigError(
            "acquisition config has missing or unexpected fields"
        )
    return AcquisitionSpec(
        schema=cast(str, document["schema"]),
        source_family=cast(str, document["source_family"]),
        bulk_type=cast(str, document["bulk_type"]),
        discovery_uri=cast(str, document["discovery_uri"]),
        expected_format=cast(str, document["expected_format"]),
        download_field=cast(str, document["download_field"]),
        user_agent=cast(str, document["user_agent"]),
        discovery_accept=cast(str, document["discovery_accept"]),
        download_accept=cast(str, document["download_accept"]),
    )
