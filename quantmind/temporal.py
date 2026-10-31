"""Point-in-time rules shared by providers, research, memory, and evaluation."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class TemporalMetadata(BaseModel):
    """The timestamps needed to decide whether evidence was knowable."""

    occurred_at: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    temporal_uncertainty: bool = False

    @field_validator("occurred_at", "published_at", "available_at", "ingested_at", mode="before")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)


class EligibilityDecision(BaseModel):
    eligible: bool
    reason: str
    available_at: datetime | None = None


def ensure_utc(value: datetime) -> datetime:
    """Normalize provider timestamps before comparing them to a research cutoff."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_eligible(metadata: TemporalMetadata, cutoff: datetime) -> bool:
    """Return whether evidence was available by the requested point in time."""

    available_at = metadata.available_at or metadata.published_at
    if available_at is None or metadata.temporal_uncertainty:
        return False
    return ensure_utc(available_at) <= ensure_utc(cutoff)


def eligibility_decision(metadata: TemporalMetadata, cutoff: datetime) -> EligibilityDecision:
    available_at = metadata.available_at or metadata.published_at
    if metadata.temporal_uncertainty:
        return EligibilityDecision(eligible=False, reason="temporal_uncertainty", available_at=available_at)
    if available_at is None:
        return EligibilityDecision(eligible=False, reason="missing_publication_timestamp")
    normalized = ensure_utc(available_at)
    if normalized > ensure_utc(cutoff):
        return EligibilityDecision(eligible=False, reason="published_after_cutoff", available_at=normalized)
    return EligibilityDecision(eligible=True, reason="available_by_cutoff", available_at=normalized)
