"""Optional Groq synthesis with strict JSON validation and safe fallback."""

from __future__ import annotations

import json
import os
from typing import Any

import aiohttp

from .models import Report
from .sources import evidence_as_prompt


class GroqSynthesizer:
    """Let Groq explain supplied evidence; never let it calculate missing facts."""

    def __init__(self) -> None:
        self._api_key = os.getenv("GROQ_API_KEY")
        self._model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    async def enrich(self, report: Report, evidence: list[Any]) -> Report:
        if not self._api_key or not evidence:
            return report
        prompt = (
            "Rewrite only the narrative strings in this report using the supplied evidence. "
            "Do not add people, numbers, claims, or sources. If evidence is insufficient, say so. "
            "Return JSON matching the existing schema exactly.\n\n"
            f"EVIDENCE:\n{evidence_as_prompt(evidence)}\n\n"
            f"REPORT:\n{report.model_dump_json()}"
        )
        body = {
            "model": self._model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a cautious financial research editor."},
                {"role": "user", "content": prompt},
            ],
        }
        timeout = aiohttp.ClientTimeout(total=45)
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions", json=body, headers=headers
                ) as response:
                    if response.status != 200:
                        return report
                    payload: dict[str, Any] = await response.json()
            content = payload["choices"][0]["message"]["content"]
            return Report.model_validate(json.loads(content))
        except (aiohttp.ClientError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return report
