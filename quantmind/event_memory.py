"""The shared Hindsight bank strategy for historical market events."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

from hindsight_client import Hindsight

EVENTS_BANK_ID = "quantmind-events"


@dataclass(slots=True)
class EventMemoryHit:
    result_id: str
    title: str
    snippet: str
    source_url: str | None
    ticker: str | None
    score: float


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

    async def search(self, query: str, limit: int = 20) -> list[EventMemoryHit]:
        await self.ensure_bank()
        response = await self._client.arecall(
            bank_id=EVENTS_BANK_ID,
            query=query,
            budget="low",
            max_tokens=3000,
            include_chunks=True,
        )
        hits: list[EventMemoryHit] = []
        for index, result in enumerate(response.results[:limit]):
            metadata = getattr(result, "metadata", None) or {}
            ticker = metadata.get("ticker") if isinstance(metadata, dict) else None
            source_url = metadata.get("source_url") if isinstance(metadata, dict) else None
            hits.append(
                EventMemoryHit(
                    result_id=str(getattr(result, "document_id", None) or f"memory-{index}"),
                    title=str(metadata.get("headline") if isinstance(metadata, dict) else "Historical market event"),
                    snippet=result.text,
                    source_url=str(source_url) if source_url else None,
                    ticker=str(ticker) if ticker else None,
                    score=max(0.0, 1.0 - index / max(len(response.results), 1)),
                )
            )
        return hits
