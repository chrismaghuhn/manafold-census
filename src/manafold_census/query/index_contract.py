"""Names shared by the five frozen M5-06 index files."""

CARD_NAME_INDEX_SCHEMA = "census.cards-by-name.v1"
CARD_ORACLE_INDEX_SCHEMA = "census.cards-by-oracle-id.v1"
REQUIREMENTS_BY_CARD_SCHEMA = "census.requirements-by-card.v1"
LINKS_BY_REQUIREMENT_SCHEMA = "census.links-by-requirement.v1"
CARDS_BY_CAPABILITY_SCHEMA = "census.cards-by-capability.v1"

INDEX_PATHS = (
    "indexes/cards-by-name.jsonl",
    "indexes/cards-by-oracle-id.jsonl",
    "indexes/requirements-by-card.jsonl",
    "indexes/links-by-requirement.jsonl",
    "indexes/cards-by-capability.jsonl",
)

__all__ = [
    "CARD_NAME_INDEX_SCHEMA",
    "CARD_ORACLE_INDEX_SCHEMA",
    "CARDS_BY_CAPABILITY_SCHEMA",
    "INDEX_PATHS",
    "LINKS_BY_REQUIREMENT_SCHEMA",
    "REQUIREMENTS_BY_CARD_SCHEMA",
]
