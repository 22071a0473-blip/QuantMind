import os
from dataclasses import dataclass


@dataclass
class MemoryResult:
    items: list[str]
    source: str


class MemoryService:
    """Small boundary around Hindsight, with a safe local demo fallback."""

    def __init__(self) -> None:
        self._local: dict[str, list[str]] = {}
        self._client = None
        url = os.getenv("HINDSIGHT_API_URL")
        if url:
            try:
                from hindsight_client import Hindsight

                self._client = Hindsight(
                    base_url=url,
                    api_key=os.getenv("HINDSIGHT_API_TOKEN"),
                )
            except ImportError:
                self._client = None

    async def recall(self, asset: str, query: str) -> MemoryResult:
        if self._client is None:
            return MemoryResult(self._local.get(asset, []), "local-demo")
        response = await self._client.arecall(bank_id=asset.lower(), query=query)
        items = [result.text for result in (response.results or [])]
        return MemoryResult(items, "hindsight")

    async def retain(self, asset: str, content: str) -> None:
        if self._client is None:
            self._local.setdefault(asset, []).append(content)
            return
        await self._client.aretain(bank_id=asset.lower(), content=content)

    async def reflect(self, asset: str, query: str) -> str:
        if self._client is None:
            memories = self._local.get(asset, [])
            return memories[-1] if memories else "No recalled memory is available yet."
        response = await self._client.areflect(bank_id=asset.lower(), query=query)
        return response.text
