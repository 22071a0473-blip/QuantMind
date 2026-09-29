from __future__ import annotations

import os
from dataclasses import dataclass

from hindsight_client import Hindsight


@dataclass(slots=True)
class RecalledMemory:
    bank_id: str
    texts: list[str]


class HindsightMemory:
    """Direct Hindsight Cloud adapter; the demo never silently falls back."""

    def __init__(self) -> None:
        url = os.environ["HINDSIGHT_API_URL"]
        token = os.environ["HINDSIGHT_API_TOKEN"]
        self._client = Hindsight(base_url=url, api_key=token)

    @staticmethod
    def bank_id(asset: str) -> str:
        return f"quantmind-{asset.lower()}"

    async def recall(self, asset: str, query: str) -> RecalledMemory:
        bank_id = self.bank_id(asset)
        response = await self._client.arecall(
            bank_id=bank_id,
            query=query,
            budget="high",
            max_tokens=6000,
            include_chunks=True,
        )
        return RecalledMemory(
            bank_id=bank_id,
            texts=[result.text for result in (response.results or [])],
        )

    async def retain(self, asset: str, report_json: str) -> None:
        await self._client.aretain(
            bank_id=self.bank_id(asset),
            content=report_json,
            context="QuantMind market event, evidence, drivers, leadership, roadmap, and outcome calibration.",
        )
