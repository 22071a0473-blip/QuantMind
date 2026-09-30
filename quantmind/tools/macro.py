from __future__ import annotations

from dataclasses import dataclass

from ._base import ToolResult


@dataclass(frozen=True, slots=True)
class MacroToolResult(ToolResult):
    regime: str | None = None


def macro_unavailable() -> MacroToolResult:
    return MacroToolResult("unavailable", "macro", reason="no verified macro series supplied")

