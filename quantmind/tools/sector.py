from __future__ import annotations

from dataclasses import dataclass

from ._base import ToolResult


@dataclass(frozen=True, slots=True)
class SectorToolResult(ToolResult):
    sector: str | None = None


def sector_unavailable() -> SectorToolResult:
    return SectorToolResult("unavailable", "sector", reason="no verified sector classification supplied")

