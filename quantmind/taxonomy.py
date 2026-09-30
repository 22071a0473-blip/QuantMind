"""Stable event taxonomy used by the historical memory backfill."""

from typing import Literal

EventType = Literal[
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
    "1.01": "contract_win",
    "2.02": "earnings",
    "2.05": "layoffs_restructuring",
    "5.02": "leadership_change",
    "2.01": "m_and_a",
    "1.05": "cyber_incident",
}

MANDATORY_EVENT_TYPES = frozenset({"contract_win", "layoffs_restructuring", "leadership_change", "earnings_beat", "earnings_miss"})
