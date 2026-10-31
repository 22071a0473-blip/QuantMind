from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from hindsight_client import Hindsight

from .models import HistoricalPrecedent, PrecedentMove, SourceCitation


@dataclass(slots=True)
class MemoryRecord:
    text: str
    date: str | None


@dataclass(slots=True)
class RecalledMemory:
    bank_id: str
    records: list[MemoryRecord]
    total_count: int
    meta_insight: str | None = None

    @property
    def texts(self) -> list[str]:
        return [record.text for record in self.records]


class HindsightMemory:
    """Direct Hindsight Cloud adapter; missing or failed Cloud access is explicit."""

    def __init__(self) -> None:
        self._base_url = os.getenv("HINDSIGHT_API_URL", "").strip()
        self._api_key = os.getenv("HINDSIGHT_API_TOKEN", "").strip()
        self._client = (
            Hindsight(base_url=self._base_url, api_key=self._api_key) if self._base_url and self._api_key else None
        )

    @property
    def configured(self) -> bool:
        return self._client is not None

    async def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            await self._client.aget_bank_config(bank_id=self.bank_id("health"))
        except Exception as exc:
            status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            if status_code != 404:
                raise
        return True

    def _require_client(self) -> Hindsight:
        if self._client is None:
            raise RuntimeError("Hindsight is not configured.")
        return self._client

    @staticmethod
    def bank_id(asset: str) -> str:
        return f"quantmind-{asset.lower()}"

    async def _ensure_bank(self, bank_id: str) -> None:
        client = self._require_client()
        try:
            await client.aget_bank_config(bank_id=bank_id)
        except Exception as exc:
            status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            response = getattr(exc, "response", None)
            if status_code is None and response is not None:
                status_code = getattr(response, "status", None)
            if status_code != 404:
                raise
            await client.acreate_bank(
                bank_id=bank_id,
                name=f"QuantMind {bank_id.removeprefix('quantmind-').upper()}",
                mission="Build evidence-grounded market research from live data and historical memory.",
                reflect_mission="Identify recurring market catalysts, regime shifts, and confidence failures.",
            )

    async def recall(self, asset: str, query: str, limit: int = 5) -> RecalledMemory:
        bank_id = self.bank_id(asset)
        client = self._require_client()
        await self._ensure_bank(bank_id)
        response = await client.arecall(
            bank_id=bank_id,
            query=query,
            budget="high",
            max_tokens=6000,
            include_chunks=True,
        )
        records = [
            MemoryRecord(text=result.text, date=result.occurred_start or result.mentioned_at)
            for result in response.results[:limit]
        ]
        meta_insight = next(
            (
                record.text.removeprefix("META-INSIGHT: ").strip()
                for record in records
                if record.text.startswith("META-INSIGHT:")
            ),
            None,
        )
        count_response = await client.alist_memories(bank_id=bank_id, limit=1)
        return RecalledMemory(
            bank_id=bank_id,
            records=[record for record in records if not record.text.startswith("META-INSIGHT:")],
            total_count=count_response.total,
            meta_insight=meta_insight,
        )

    async def retain(
        self,
        asset: str,
        report_json: str,
        price_change: float,
        primary_reason: str,
        research_id: UUID | str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> int:
        bank_id = self.bank_id(asset)
        client = self._require_client()
        await self._ensure_bank(bank_id)
        retention_metadata = {
            "type": "market_event",
            "generated_at": datetime.now(UTC).date().isoformat(),
            "price_change": f"{price_change:.6f}",
            "primary_reason": primary_reason,
        }
        if metadata:
            retention_metadata.update(metadata)
        document_id = f"research-{research_id}" if research_id else None
        await client.aretain(
            bank_id=bank_id,
            content=report_json,
            context="QuantMind market event and evidence-grounded report.",
            document_id=document_id,
            metadata=retention_metadata,
            tags=["research-report", f"ticker:{asset.upper()}", f"reason:{primary_reason}"],
            update_mode="replace",
        )
        response = await client.alist_memories(bank_id=bank_id, type="market_event", limit=1)
        return response.total

    async def reflect(self, asset: str, query: str) -> str:
        await self._ensure_bank(self.bank_id(asset))
        response = await self._require_client().areflect(
            bank_id=self.bank_id(asset),
            query=query,
            budget="high",
            max_tokens=2500,
        )
        return response.text if hasattr(response, "text") else str(response)

    async def retain_insight(self, asset: str, insight: str, based_on_count: int) -> None:
        await self._ensure_bank(self.bank_id(asset))
        await self._require_client().aretain(
            bank_id=self.bank_id(asset),
            content=f"META-INSIGHT: {insight}",
            context="QuantMind derived meta-pattern from prior market event reports.",
            metadata={
                "type": "insight",
                "generated_at": datetime.now(UTC).date().isoformat(),
                "based_on_count": str(based_on_count),
            },
        )

    async def list_memories(self, asset: str, limit: int = 100) -> dict[str, Any]:
        await self._ensure_bank(self.bank_id(asset))
        response = await self._require_client().alist_memories(bank_id=self.bank_id(asset), limit=limit)
        return {
            "bank_id": self.bank_id(asset),
            "total": response.total,
            "items": [item.model_dump() for item in response.items],
        }


def summarize_precedent(
    ticker: str,
    records: list[MemoryRecord],
    meta_insight: str | None = None,
) -> HistoricalPrecedent:
    moves: list[PrecedentMove] = []
    pattern = re.compile(
        r"\[EVENT\]\s+date=(?P<date>\S+)\s+change_pct=(?P<change>[-+]?\d+(?:\.\d+)?)\s+"
        r"reason=(?P<reason>\S+)(?:\s+forward_5d=(?P<forward>\S+))?"
    )
    for record in records:
        match = pattern.search(record.text)
        if match is None:
            continue
        forward = match.group("forward")
        follow_through = None if not forward or forward == "unavailable" else float(forward)
        moves.append(
            PrecedentMove(
                date=match.group("date")[:10],
                price_change=float(match.group("change")),
                reason=match.group("reason").replace("_", " "),
                outcome=None,
                follow_through_5d=follow_through,
                source=SourceCitation(
                    source_type="memory",
                    date=match.group("date")[:10],
                    headline=f"Prior {ticker} QuantMind event",
                ),
            )
        )
    follow_through = [move.follow_through_5d for move in moves]
    known = [value for value in follow_through if value is not None]
    if not moves:
        narrative = (
            "No historical precedent in memory yet. This is the first recorded instance of this pattern. "
            "Future analyses will compare against this one."
        )
    else:
        average = sum(known) / len(known) if known else None
        average_text = f"{average:.2f}%" if average is not None else "not yet observable"
        narrative = (
            f"Hindsight returned {len(moves)} retained event records for {ticker}. "
            f"The observed average 5-day follow-through was {average_text}."
        )
    return HistoricalPrecedent(
        count=len(moves),
        dates=[move.date for move in moves],
        price_changes=[move.price_change for move in moves],
        reasons=[move.reason for move in moves],
        follow_through_5d=follow_through,
        average_follow_through=sum(known) / len(known) if known else None,
        moves=moves,
        narrative=narrative,
        meta_insight=meta_insight,
    )
