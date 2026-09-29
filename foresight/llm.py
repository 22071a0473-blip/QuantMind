from __future__ import annotations

import json
import os
from typing import Any

from groq import AsyncGroq

from .models import Report


class GroqResearcher:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
        self._model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    async def synthesize(
        self,
        asset: str,
        live_data: str,
        recalled_memory: str,
        deterministic_report: str,
    ) -> Report:
        system = (
            "You are QuantMind, a cautious institutional research analyst. Return only valid JSON "
            "matching the supplied Pydantic report schema. Use only live data and recalled memory. "
            "Never invent a person, number, deal, source, price, or historical case. If evidence is "
            "missing, state the gap. This is scenario analysis, never financial advice."
        )
        user = (
            f"Asset: {asset}\n\nLIVE DATA:\n{live_data}\n\nHINDSIGHT MEMORY:\n{recalled_memory}\n\n"
            f"DETERMINISTIC REPORT SHELL:\n{deterministic_report}\n\n"
            "Complete the five factors: primary drivers, deep research, leadership, success roadmap, "
            "and facts versus reality. Preserve the deterministic confidence object and snapshot."
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.1,
            max_tokens=8000,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty research response.")
        payload: dict[str, Any] = json.loads(content)
        return Report.model_validate(payload)
