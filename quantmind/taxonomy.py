"""Stable event taxonomy used by the historical memory backfill."""

from typing import Literal

EventType = Literal[
    "earnings_release",
    "restructuring_layoffs",
    "material_agreement",
    "merger_acquisition",
    "price_only",
    "contract_win",
    "major_partnership_deal",
    "earnings",
    "earnings_beat",
    "earnings_miss",
    "layoffs_restructuring",
    "leadership_change",
    "m_and_a",
    "cyber_incident",
    "regulatory_legal",
    "guidance_raise",
    "guidance_cut",
    "board_change",
    "price_move",
]

FILING_ITEM_TYPES: dict[str, EventType] = {
    "1.01": "material_agreement",
    "2.02": "earnings_release",
    "2.05": "restructuring_layoffs",
    "5.02": "leadership_change",
    "2.01": "merger_acquisition",
    "1.05": "cyber_incident",
}

MANDATORY_EVENT_TYPES = frozenset(
    {"material_agreement", "restructuring_layoffs", "leadership_change", "earnings_release"}
)

LEGACY_EVENT_TYPE_ALIASES: dict[str, EventType] = {
    "contract_win": "material_agreement",
    "layoffs_restructuring": "restructuring_layoffs",
    "m_and_a": "merger_acquisition",
    "price_move": "price_only",
}


def canonical_event_type(event_type: str) -> EventType:
    return LEGACY_EVENT_TYPE_ALIASES.get(event_type, event_type)  # type: ignore[return-value]
