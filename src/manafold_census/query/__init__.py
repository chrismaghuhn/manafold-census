"""Read-only derived query/index primitives reserved for later M5 slices."""

from .indexes import (
    CARD_NAME_INDEX_SCHEMA,
    CARD_ORACLE_INDEX_SCHEMA,
    CARDS_BY_CAPABILITY_SCHEMA,
    LINKS_BY_REQUIREMENT_SCHEMA,
    REQUIREMENTS_BY_CARD_SCHEMA,
    DerivedIndexRowsV1,
    build_index_rows,
    validate_index_row,
)

__all__ = [
    "CARD_NAME_INDEX_SCHEMA",
    "CARD_ORACLE_INDEX_SCHEMA",
    "CARDS_BY_CAPABILITY_SCHEMA",
    "LINKS_BY_REQUIREMENT_SCHEMA",
    "REQUIREMENTS_BY_CARD_SCHEMA",
    "DerivedIndexRowsV1",
    "build_index_rows",
    "validate_index_row",
]
