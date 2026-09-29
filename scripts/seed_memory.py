"""Seed realistic, explicitly labeled demo theses into Hindsight Cloud."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from dotenv import load_dotenv

from foresight.config import Settings
from foresight.logging_config import configure_logging
from foresight.memory import HindsightMemory


def thesis(
    asset: str,
    catalyst: str,
    macro_theme: str,
    outcome: str,
    confidence: int,
    price_change: float,
    days: int,
) -> str:
    return json.dumps(
        {
            "generated_at": datetime.now(UTC).date().isoformat(),
            "snapshot": {
                "asset": asset,
                "kind": "stock" if asset == "PLTR" else "crypto",
                "price": 100.0,
                "change_pct": price_change,
                "history_days": 365,
            },
            "factor_1_why_it_moved": [
                {
                    "category": catalyst,
                    "probability": confidence / 100,
                    "explanation": (
                        f"Historical demo thesis: {catalyst}. Macro context: {macro_theme}. "
                        f"Observed outcome: {outcome} over {days} days."
                    ),
                    "evidence": [],
                }
            ],
            "memory_thesis": {
                "asset": asset,
                "catalyst": catalyst,
                "macro_theme": macro_theme,
                "outcome": outcome,
                "initial_confidence": confidence,
                "horizon_days": days,
                "demo_seed": True,
            },
        },
        separators=(",", ":"),
    )


async def main() -> None:
    load_dotenv()
    settings = Settings.from_env()
    configure_logging(settings)
    if not settings.hindsight_token:
        raise SystemExit("HINDSIGHT_API_TOKEN is required; set it in .env.")

    memory = HindsightMemory()
    seeds = [
        ("PLTR", "DoD AI TITAN Contract Win", "Defense budget expansion and geopolitical escalation",
         "+18% over 30 days", 88, 18.0, 30),
        ("PLTR", "Commercial AI platform adoption by Fortune 500", "Enterprise software rotation",
         "+12% over 14 days", 75, 12.0, 14),
        ("ONDO", "US Treasury Tokenization narrative + BlackRock partnership", "RWA institutional adoption",
         "+45% over 30 days", 92, 45.0, 30),
    ]
    for asset, catalyst, macro_theme, outcome, confidence, move, days in seeds:
        await memory.retain(
            asset=asset,
            report_json=thesis(asset, catalyst, macro_theme, outcome, confidence, move, days),
            price_change=move,
            primary_reason=catalyst,
            metadata={
                "asset": asset,
                "catalyst": catalyst,
                "macro_theme": macro_theme,
                "demo_seed": "true",
                "outcome": outcome,
                "initial_confidence": str(confidence),
            },
        )
        print(f"Seeded {asset}: {catalyst}")


if __name__ == "__main__":
    asyncio.run(main())
