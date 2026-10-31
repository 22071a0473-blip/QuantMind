"""Run reproducible point-in-time features, analogue searches, and evaluation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, time
from pathlib import Path
from uuid import UUID

from quantmind.historical import (
    WalkForwardConfig,
    compute_features,
    save_evaluation,
    save_feature_snapshot,
    search_analogues,
    walk_forward_evaluate,
)
from quantmind.storage import SQLiteStore


def _cutoff(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("features", "analogues", "evaluate", "dossier"))
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--horizon", type=int, default=20)
    args = parser.parse_args()
    store = SQLiteStore(args.database)
    try:
        security = store.find_security(args.ticker)
        if security is None:
            raise SystemExit(f"No canonical security mapping found for {args.ticker}.")
        bars = store.market_bars_for_security(security.security_id)
        if not bars:
            raise SystemExit(f"No market bars found for {args.ticker}.")
        if args.command == "features":
            features = compute_features(bars)
            for feature in features:
                save_feature_snapshot(store, feature)
            print(json.dumps([feature.model_dump(mode="json") for feature in features[-args.limit :]], indent=2))
            return
        if args.command == "evaluate":
            evaluation = walk_forward_evaluate(
                bars,
                WalkForwardConfig(horizon=args.horizon),
            )
            save_evaluation(store, evaluation)
            print(evaluation.model_dump_json(indent=2))
            return
        if args.date is None:
            raise SystemExit("--date is required for analogue and dossier commands.")
        cutoff = _cutoff(args.date)
        query = search_analogues(
            target_bars=bars,
            comparable_bars=[bars],
            target_date=args.date,
            cutoff=cutoff,
            limit=args.limit,
        )
        if args.command == "analogues":
            print(query.model_dump_json(indent=2))
            return
        dossier = {
            "target_security": args.ticker.upper(),
            "decision_timestamp": cutoff.isoformat(),
            "coverage": {
                "bars": len(bars),
                "first_observation": bars[0].observed_at.isoformat(),
                "latest_observation": bars[-1].observed_at.isoformat(),
            },
            "current_features": compute_features(bars, start=args.date, end=args.date),
            "historical_analogues": query,
            "methodology": {
                "feature_version": "phase3-v1",
                "price_basis": "adjusted_close_fallback",
                "limitations": [
                    "This dossier uses only the requested security because no peer universe was supplied.",
                    "Analogue similarity is a transparent baseline, not a causal or calibrated forecast.",
                ],
            },
        }
        print(json.dumps(dossier, default=lambda item: item.model_dump(mode="json"), indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
