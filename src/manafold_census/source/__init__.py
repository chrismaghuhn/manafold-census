"""Primary external source acquisition for Census."""

from .config import AcquisitionConfigError, AcquisitionSpec, load_acquisition_spec
from .scryfall import (
    BulkDataObservation,
    SourceAcquisitionError,
    discover_oracle_cards,
    parse_oracle_cards_metadata,
    refresh_current_source,
)
from .transfer import (
    cache_path_for,
    download_source,
    fetch_pinned_source,
    write_source_lock,
)

__all__ = [
    "AcquisitionConfigError",
    "AcquisitionSpec",
    "BulkDataObservation",
    "SourceAcquisitionError",
    "cache_path_for",
    "discover_oracle_cards",
    "download_source",
    "fetch_pinned_source",
    "load_acquisition_spec",
    "parse_oracle_cards_metadata",
    "refresh_current_source",
    "write_source_lock",
]
