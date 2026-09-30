"""Verify the shared QuantMind event bank and report its current contents."""

from __future__ import annotations

import argparse
import asyncio
import os

from hindsight_client import Hindsight
from quantmind.event_memory import EVENTS_BANK_ID


async def verify(limit: int) -> None:
    client = Hindsight(base_url=os.environ["HINDSIGHT_API_URL"], api_key=os.environ["HINDSIGHT_API_TOKEN"])
    response = await client.alist_memories(bank_id=EVENTS_BANK_ID, limit=limit)
    print(f"bank={EVENTS_BANK_ID}")
    print(f"total={response.total}")
    for item in response.items:
        print(f"{item.document_id}: {item.text[:160].replace(chr(10), ' ')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    asyncio.run(verify(parser.parse_args().limit))
