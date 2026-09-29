"""Seed a Hindsight bank from stdin or a file without embedding credentials."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from foresight.config import Settings
from foresight.logging_config import configure_logging
from foresight.memory import HindsightMemory


async def main(path: Path, asset: str) -> None:
    settings = Settings.from_env()
    configure_logging(settings)
    if not settings.hindsight_token:
        raise SystemExit("HINDSIGHT_API_TOKEN is required; set it in the environment.")
    memory = HindsightMemory()
    content = path.read_text(encoding="utf-8")
    await memory.retain(asset, content, 0.0, "seed")
    print(f"Seeded {asset} from {path}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    asyncio.run(main(args.file, args.asset))

