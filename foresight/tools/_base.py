from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Status = Literal["available", "unavailable"]


@dataclass(frozen=True, slots=True)
class ToolResult:
    status: Status
    source: str
    reason: str | None = None

