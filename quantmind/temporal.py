"""Point-in-time rules shared by providers, research, memory, and evaluation."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class TemporalMetadata(BaseModel):
    """The timestamps needed to decide whether evidence was knowable."""

    occurred_at: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    temporal_uncertainty: bool = False


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
