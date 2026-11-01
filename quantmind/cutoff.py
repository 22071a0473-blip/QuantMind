"""Immutable information cutoffs for point-in-time market analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


@dataclass(frozen=True, slots=True)
class Cutoff:
    """The exclusive timestamp at which an after-close forecast is made."""

    as_of: date
    information_cutoff: datetime

    def __post_init__(self) -> None:
        if self.information_cutoff.tzinfo is None:
            raise ValueError("information_cutoff must be timezone-aware")
        if self.information_cutoff.astimezone(UTC) != datetime.combine(
            self.as_of + timedelta(days=1), datetime.min.time(), tzinfo=UTC
        ):
            raise ValueError("information_cutoff must be the exclusive day after as_of")


def cutoff_for_as_of(as_of: date) -> Cutoff:
    """Return the exclusive UTC cutoff for a forecast made after ``as_of`` closes."""

    today = datetime.now(UTC).date()
    if as_of > today:
        raise ValueError("as_of cannot be in the future")
    return Cutoff(
        as_of=as_of,
        information_cutoff=datetime.combine(as_of + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
    )
