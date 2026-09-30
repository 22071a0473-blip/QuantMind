"""The shared Hindsight bank strategy for historical market events."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from hindsight_client import Hindsight

EVENTS_BANK_ID = "quantmind-events"


class QuantMindEventMemory:
    def __init__(self) -> None:
        self._client = Hindsight(
            base_url=os.environ["HINDSIGHT_API_URL"],
            api_key=os.environ["HINDSIGHT_API_TOKEN"],
        )

    async def ensure_bank(self) -> None:
        try:
            await self._client.aget_bank_config(bank_id=EVENTS_BANK_ID)
        except Exception as exc:
            status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            if status_code != 404:
                raise
            await self._client.acreate_bank(
                bank_id=EVENTS_BANK_ID,
                name="QuantMind Events",
                reflect_mission="Find recurring market event patterns and distinguish catalysts from noise.",
                retain_mission="Store one structured, source-backed market event per document ID.",
            )

    async def retain_batch(self, items: list[dict[str, object]], operation_id: str) -> int:
        await self.ensure_bank()
        response = await self._client.aretain_batch(
            bank_id=EVENTS_BANK_ID,
            items=items,
            document_tags=["quantmind", "market-event"],
            retain_async=False,
            operation_id=operation_id,
        )
        return response.items_count
