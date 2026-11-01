"""Verify the QuantMind Hindsight write/read boundary without exposing credentials."""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from dotenv import load_dotenv
from hindsight_client import Hindsight
from quantmind.event_memory import EVENTS_BANK_ID

load_dotenv()


@dataclass(slots=True)
class VerificationReport:
    bank_id: str
    configured: bool
    bank_accessible: bool
    write_succeeded: bool
    recall_succeeded: bool
    marker_retrieved: bool
    repeated_write_count: int | None
    temporal_cutoff_supported: bool
    cleanup_supported: bool
    operation_status_supported: bool
    notes: list[str]


async def verify() -> VerificationReport:
    url = os.environ.get("HINDSIGHT_API_URL")
    token = os.environ.get("HINDSIGHT_API_TOKEN")
    report = VerificationReport(
        bank_id=EVENTS_BANK_ID,
        configured=bool(url and token),
        bank_accessible=False,
        write_succeeded=False,
        recall_succeeded=False,
        marker_retrieved=False,
        repeated_write_count=None,
        temporal_cutoff_supported=False,
        cleanup_supported=False,
        operation_status_supported=False,
        notes=[],
    )
    if not url or not token:
        report.notes.append("HINDSIGHT_API_URL or HINDSIGHT_API_TOKEN is missing.")
        return report

    client = Hindsight(base_url=url, api_key=token)
    try:
        await client.aget_bank_config(bank_id=EVENTS_BANK_ID)
        report.bank_accessible = True
    except Exception as exc:
        report.notes.append(f"Bank access failed: {type(exc).__name__}.")
        return report

    marker = f"quantmind-verification-{uuid4().hex}"
    document_id = f"quantmind-verification-{uuid4().hex}"
    timestamp = datetime.now(UTC)
    try:
        await client.aretain(
            bank_id=EVENTS_BANK_ID,
            content=f"Verification marker {marker}.",
            timestamp=timestamp,
            context="QuantMind Hindsight integration verification.",
            document_id=document_id,
            metadata={"type": "verification", "marker": marker},
            tags=["quantmind-verification"],
            update_mode="replace",
        )
        report.write_succeeded = True
    except Exception as exc:
        report.notes.append(f"Write failed: {type(exc).__name__}.")
        return report

    try:
        recalled = await client.arecall(
            bank_id=EVENTS_BANK_ID,
            query=marker,
            budget="low",
            max_tokens=1000,
            tags=["quantmind-verification"],
            tags_match="all",
            include_chunks=True,
        )
        report.recall_succeeded = True
        report.marker_retrieved = any(marker in result.text for result in recalled.results)
    except Exception as exc:
        report.notes.append(f"Recall failed: {type(exc).__name__}.")

    try:
        await client.aretain(
            bank_id=EVENTS_BANK_ID,
            content=f"Verification marker {marker}.",
            timestamp=timestamp,
            context="QuantMind Hindsight integration verification.",
            document_id=document_id,
            metadata={"type": "verification", "marker": marker},
            tags=["quantmind-verification"],
            update_mode="replace",
        )
        listed = await client.alist_memories(
            bank_id=EVENTS_BANK_ID,
            search_query=marker,
            limit=100,
        )
        report.repeated_write_count = listed.total
    except Exception as exc:
        report.notes.append(f"Idempotency check failed: {type(exc).__name__}.")

    try:
        await client.arecall(
            bank_id=EVENTS_BANK_ID,
            query=marker,
            query_timestamp=(timestamp - timedelta(minutes=1)).isoformat(),
            temporal_window={"start_date": "1900-01-01", "end_date": "1900-01-02"},
            budget="low",
            max_tokens=500,
        )
        report.temporal_cutoff_supported = True
    except Exception as exc:
        report.notes.append(f"Temporal cutoff probe failed: {type(exc).__name__}.")

    report.notes.append("The installed SDK exposes no delete-memory or operation-status method.")
    return report


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()
    report = await verify()
    if args.json:
        import json

        print(json.dumps(asdict(report), indent=2))
    else:
        for key, value in asdict(report).items():
            print(f"{key}={value}")


if __name__ == "__main__":
    asyncio.run(main())
