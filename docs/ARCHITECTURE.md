# QuantMind architecture

## Current execution path

1. `quantmind.app` validates the requested ticker or crypto identifier.
2. `QuantMindEngine` asks `LiveMarketSources` for current price, volume,
   provider news and derived market features.
3. `HindsightMemory` recalls asset-specific research records when memory is
   enabled.
4. `ConfidenceEngine` evaluates available observations; unavailable fields
   remain unavailable and affect coverage.
5. `InstitutionalAnalytics` calculates deterministic movement signals.
6. `GroqResearcher` synthesizes only the acquired evidence and deterministic
   report skeleton. If synthesis is unavailable, the deterministic report is
   returned with an explicit warning.
7. The validated report is retained in Hindsight with a stable research
   document ID.
8. Every fifth retained report triggers a reflection and stores a separate
   meta-insight.
9. FastAPI returns the typed report to the React terminal or legacy `/research`
   page.

## Data boundaries

- Provider responses are external evidence and retain source timestamps.
- Deterministic calculations belong in Python modules, not in prompts.
- Hindsight stores compact research/event memories, not every raw price row.
- A future relational store is the authoritative home for normalized market,
  filing, fundamental, event, forecast, and outcome records. The current local
  implementation is `quantmind.storage.SQLiteStore`; production PostgreSQL
  migration remains a later phase.
- `quantmind.temporal` is the shared point-in-time eligibility boundary for
  retrospective research and evaluation.

## Current limitations

The repository currently uses yfinance and CoinGecko for live acquisition and
does not yet provide the full relational canonical database, Fortune 500
historical universe, filing/fundamental ingestion ledger, forecast outcome
ledger, or walk-forward evaluation required by the master specifications.
These are later implementation phases, not completed functionality.
