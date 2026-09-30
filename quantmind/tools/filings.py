from __future__ import annotations

from dataclasses import dataclass

from ._base import ToolResult


@dataclass(frozen=True, slots=True)
class FilingsToolResult(ToolResult):
    filing_count: int = 0


def filings_unavailable() -> FilingsToolResult:
    return FilingsToolResult("unavailable", "filings", reason="SEC filing payload was not supplied")

