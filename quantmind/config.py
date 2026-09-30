"""Typed configuration for the standalone QuantMind service."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    hindsight_url: str
    hindsight_token: str
    bank_prefix: str = "quantmind-"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    tavily_api_key: str | None = None
    cache_ttl_seconds: int = 300
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        def value(*names: str, default: str = "") -> str:
            for name in names:
                found = os.getenv(name)
                if found is not None:
                    return found
            return default

        return cls(
            hindsight_url=os.getenv("HINDSIGHT_API_URL", "http://localhost:8888").strip(),
            hindsight_token=os.getenv("HINDSIGHT_API_TOKEN", "").strip(),
            bank_prefix=os.getenv("HINDSIGHT_BANK_PREFIX", "quantmind-").strip(),
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
            tavily_api_key=os.getenv("TAVILY_API_KEY") or None,
            cache_ttl_seconds=max(0, int(value("QUANTMIND_CACHE_TTL_SECONDS", "QUANTMIND_CACHE_TTL", default="300"))),
            log_level=value("QUANTMIND_LOG_LEVEL", "LOG_LEVEL", default="INFO").strip().upper(),
        )


QuantMindSettings = Settings


def load_settings() -> Settings:
    return Settings.from_env()
