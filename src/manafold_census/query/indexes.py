"""Canonical derived indexes for the validated Census 0.1 bundle."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from ..analysis.model import CardAnalysisRecordV1, card_source_key
from ..canonical import JSONValue, canonical_json_bytes
from ..capability.build import _RereadResult
from ..capability.link import RequirementCapabilityLinkV1
from ..capability.mapping import MappingDispositionV1, RequirementMappingDecisionV1
from ..capability.model import CapabilityRefV1
from ..semantic.identity import wire_digest_for
from ..semantic.model import RequirementV1
from ..structural.model import StructuralCardRecordV1
from .index_contract import (
    CARD_NAME_INDEX_SCHEMA,
    CARD_ORACLE_INDEX_SCHEMA,
    CARDS_BY_CAPABILITY_SCHEMA,
    INDEX_PATHS,
    LINKS_BY_REQUIREMENT_SCHEMA,
    REQUIREMENTS_BY_CARD_SCHEMA,
)
from .index_validation import validate_index_row


def _identity(record: StructuralCardRecordV1) -> dict[str, JSONValue]:
    return {
        "oracle_id": record.oracle_id,
        "source_card_id": record.source_card_id,
        "source_record_sha256": record.source_record_sha256,
        "name": record.name,
    }


def _source_key(record: StructuralCardRecordV1) -> tuple[str, str, str, str]:
    return (
        StructuralCardRecordV1.SCHEMA,
        record.oracle_id,
        record.source_card_id,
        record.source_record_sha256,
    )


def _source_identity(record: StructuralCardRecordV1) -> tuple[str, str, str]:
    return (record.oracle_id, record.source_card_id, record.source_record_sha256)


def _ref_key(ref: CapabilityRefV1) -> tuple[str, int, str]:
    return (ref.capability_family_id, ref.capability_version, ref.claim_digest)


def _link_key(link: RequirementCapabilityLinkV1) -> tuple[str, str, bytes, str]:
    return (
        link.requirement_id,
        link.relation.value,
        canonical_json_bytes(link.capability.to_wire()),
        link.link_id,
    )


def _mapped_links(reread: _RereadResult) -> tuple[RequirementCapabilityLinkV1, ...]:
    by_id = {item.link_id: item for item in reread.links}
    values: list[RequirementCapabilityLinkV1] = []
    seen: set[str] = set()
    for decision in reread.decisions:
        if decision.disposition is not MappingDispositionV1.MAPPED:
            continue
        for link_id in decision.active_link_ids:
            link = by_id.get(link_id)
            if link is None:
                raise ValueError("MAPPED decision references an unknown link")
            if link_id not in seen:
                values.append(link)
                seen.add(link_id)
    return tuple(sorted(values, key=_link_key))


def _card_rows(
    records: Sequence[StructuralCardRecordV1],
    analyses: Mapping[tuple[str, str, str, str], CardAnalysisRecordV1],
    requirement_ids: Mapping[tuple[str, str, str, str], Sequence[str]],
    decisions: Mapping[str, RequirementMappingDecisionV1],
    active_refs: Mapping[tuple[str, str, str, str], Sequence[CapabilityRefV1]],
) -> tuple[dict[str, JSONValue], ...]:
    rows: list[dict[str, JSONValue]] = []
    for record in sorted(records, key=lambda item: item.oracle_id):
        key = _source_key(record)
        ids = tuple(requirement_ids.get(key, ()))
        dispositions = [decisions[item].disposition.value for item in ids]
        refs = sorted(active_refs.get(key, ()), key=_ref_key)
        rows.append(
            {
                "schema": CARD_ORACLE_INDEX_SCHEMA,
                **_identity(record),
                "analysis_outcome": analyses[key].outcome.value,
                "requirement_ids": cast(JSONValue, list(ids)),
                "mapping_dispositions": cast(JSONValue, dispositions),
                "active_capability_refs": [item.to_wire() for item in refs],
            }
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class DerivedIndexRowsV1:
    """All five ordered JSONL index row collections."""

    cards_by_name: tuple[dict[str, JSONValue], ...]
    cards_by_oracle_id: tuple[dict[str, JSONValue], ...]
    requirements_by_card: tuple[dict[str, JSONValue], ...]
    links_by_requirement: tuple[dict[str, JSONValue], ...]
    cards_by_capability: tuple[dict[str, JSONValue], ...]

    def by_path(self) -> dict[str, tuple[dict[str, JSONValue], ...]]:
        return {
            INDEX_PATHS[0]: self.cards_by_name,
            INDEX_PATHS[1]: self.cards_by_oracle_id,
            INDEX_PATHS[2]: self.requirements_by_card,
            INDEX_PATHS[3]: self.links_by_requirement,
            INDEX_PATHS[4]: self.cards_by_capability,
        }


def build_index_rows(
    structural_records: Sequence[StructuralCardRecordV1],
    analysis_records: Sequence[CardAnalysisRecordV1],
    requirements: Sequence[RequirementV1],
    reread: _RereadResult,
) -> DerivedIndexRowsV1:
    """Build indexes from typed records without creating semantic values."""

    analyses = {card_source_key(item.source): item for item in analysis_records}
    if len(analyses) != len(analysis_records):
        raise ValueError("analysis records contain duplicate source identities")
    structural_by_source = {_source_key(item): item for item in structural_records}
    if set(analyses) != set(structural_by_source):
        raise ValueError("M1 and M3 index identities differ")

    requirements_by_source: dict[tuple[str, str, str, str], list[str]] = defaultdict(
        list
    )
    requirements_by_id = {item.requirement_id: item for item in requirements}
    for requirement in requirements:
        requirements_by_source[card_source_key(requirement.source)].append(
            requirement.requirement_id
        )
    for requirement_ids_for_source in requirements_by_source.values():
        requirement_ids_for_source.sort()

    decisions = {item.requirement_id: item for item in reread.decisions}
    links_by_requirement: dict[str, list[RequirementCapabilityLinkV1]] = defaultdict(
        list
    )
    for link in reread.links:
        links_by_requirement[link.requirement_id].append(link)
    for links_for_requirement in links_by_requirement.values():
        links_for_requirement.sort(key=_link_key)

    active_refs: dict[tuple[str, str, str, str], list[CapabilityRefV1]] = defaultdict(
        list
    )
    mapped_links = _mapped_links(reread)
    for link in mapped_links:
        matched_requirement = requirements_by_id.get(link.requirement_id)
        if matched_requirement is None:
            raise ValueError("M4 link references an unknown Requirement")
        key = card_source_key(matched_requirement.source)
        if link.capability not in active_refs[key]:
            active_refs[key].append(link.capability)

    cards_by_name = tuple(
        {"schema": CARD_NAME_INDEX_SCHEMA, **_identity(record)}
        for record in sorted(
            structural_records,
            key=lambda item: (item.name, item.oracle_id, item.source_card_id),
        )
    )
    cards_by_oracle_id = _card_rows(
        structural_records,
        analyses,
        requirements_by_source,
        decisions,
        active_refs,
    )
    requirements_by_card = tuple(
        {
            "schema": REQUIREMENTS_BY_CARD_SCHEMA,
            **_identity(record),
            "analysis_outcome": analyses[_source_key(record)].outcome.value,
            "requirement_ids": cast(
                JSONValue, list(requirements_by_source.get(_source_key(record), ()))
            ),
        }
        for record in sorted(structural_records, key=lambda item: item.oracle_id)
    )

    links_rows: list[dict[str, JSONValue]] = []
    for requirement in sorted(requirements, key=lambda item: item.requirement_id):
        links_rows.append(
            {
                "schema": LINKS_BY_REQUIREMENT_SCHEMA,
                "requirement_id": requirement.requirement_id,
                "requirement_wire_digest": wire_digest_for(requirement),
                "source": requirement.source.to_wire(),
                "links": cast(
                    JSONValue,
                    [
                        item.to_wire()
                        for item in links_by_requirement.get(
                            requirement.requirement_id, ()
                        )
                    ],
                ),
                "mapping_decision": decisions[requirement.requirement_id].to_wire(),
            }
        )

    mapped_by_capability: dict[CapabilityRefV1, list[tuple[str, RequirementV1]]] = (
        defaultdict(list)
    )
    for link in mapped_links:
        mapped_by_capability[link.capability].append(
            (link.link_id, requirements_by_id[link.requirement_id])
        )
    cards_by_capability: list[dict[str, JSONValue]] = []
    mapped_requirement_count = sum(
        item.disposition is MappingDispositionV1.MAPPED for item in reread.decisions
    )
    for definition in sorted(
        reread.definitions, key=lambda item: _ref_key(item.capability_ref)
    ):
        selected = mapped_by_capability.get(definition.capability_ref, [])
        selected_requirements = {
            requirement.requirement_id: requirement
            for _link_id, requirement in selected
        }
        cards = {
            _source_identity(
                structural_by_source[card_source_key(requirement.source)]
            ): structural_by_source[card_source_key(requirement.source)]
            for requirement in selected_requirements.values()
        }
        cards_by_capability.append(
            {
                "schema": CARDS_BY_CAPABILITY_SCHEMA,
                "capability": definition.capability_ref.to_wire(),
                "display_name": definition.display_name,
                "lifecycle": definition.lifecycle.value,
                "card_refs": [
                    _identity(card)
                    for card in sorted(cards.values(), key=lambda item: item.oracle_id)
                ],
                "requirement_ids": cast(JSONValue, sorted(selected_requirements)),
                "link_ids": cast(JSONValue, sorted(link_id for link_id, _ in selected)),
                "mapped_requirement_count": len(selected_requirements),
                "denominator": mapped_requirement_count,
                "denominator_label": "MAPPED_REQUIREMENTS",
            }
        )

    return DerivedIndexRowsV1(
        cards_by_name=cards_by_name,
        cards_by_oracle_id=cards_by_oracle_id,
        requirements_by_card=tuple(
            cast(dict[str, JSONValue], row) for row in requirements_by_card
        ),
        links_by_requirement=tuple(links_rows),
        cards_by_capability=tuple(cards_by_capability),
    )


__all__ = [
    "CARD_NAME_INDEX_SCHEMA",
    "CARD_ORACLE_INDEX_SCHEMA",
    "CARDS_BY_CAPABILITY_SCHEMA",
    "DerivedIndexRowsV1",
    "INDEX_PATHS",
    "LINKS_BY_REQUIREMENT_SCHEMA",
    "REQUIREMENTS_BY_CARD_SCHEMA",
    "build_index_rows",
    "validate_index_row",
]
