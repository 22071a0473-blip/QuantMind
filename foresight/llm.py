from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from groq import AsyncGroq

from .models import Report

logger = logging.getLogger(__name__)


class GroqResearcher:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
        self._model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    async def synthesize(
        self,
        asset: str,
        live_data: str,
        recalled_memory: str,
        deterministic_report: Report,
    ) -> Report:
        system = (
            "You are QuantMind, a cautious institutional research analyst. Return only valid JSON "
            "matching the supplied Pydantic report schema. Use only live data and recalled memory. "
            "For every factual claim, include a source object with source_type "
            "(news, sec_filing, price_data, macro_data, or memory), source_url if available, headline "
            "if news, and date. Never state a fact you cannot source from the provided evidence; say "
            "'insufficient evidence' instead of guessing. Preserve the deterministic snapshot and confidence."
        )
        user = (
            f"Asset: {asset}\n\nLIVE DATA:\n{live_data}\n\nHINDSIGHT MEMORY:\n{recalled_memory}\n\n"
            f"DETERMINISTIC REPORT SHELL:\n{deterministic_report.model_dump_json()}\n\n"
            "Complete factors 1, 2, and 5 plus extended_analysis. Factor 4 is the supplied historical "
            "precedent and must not be replaced with invented history."
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
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
                try:
                    payload: dict[str, Any] = json.loads(content)
                except json.JSONDecodeError:
                    markdown_match = re.search(
                        r"```json\s*(.*?)\s*```",
                        content,
                        flags=re.IGNORECASE | re.DOTALL,
                    )
                    if markdown_match is None:
                        raise
                    payload = json.loads(markdown_match.group(1))
                return Report.model_validate(payload)
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                last_error = exc
                logger.warning("Groq returned invalid report JSON on attempt %s: %s", attempt + 1, exc)
                if attempt == 1:
                    user += "\nReturn the complete JSON object again. Do not omit any required field."
                await asyncio.sleep(2**attempt)
            except Exception as exc:
                last_error = exc
                logger.warning("Groq synthesis failed on attempt %s: %s", attempt + 1, exc)
                await asyncio.sleep(2**attempt)
        deterministic.warning = f"Groq synthesis failed after retries: {last_error}"
        return deterministic
