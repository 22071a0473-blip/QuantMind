from __future__ import annotations

from dataclasses import dataclass

from ._base import ToolResult


@dataclass(frozen=True, slots=True)
class FlowsToolResult(ToolResult):
    net_flow: float | None = None


def flows_unavailable() -> FlowsToolResult:
    return FlowsToolResult("unavailable", "flows", reason="no verified flow series supplied")

