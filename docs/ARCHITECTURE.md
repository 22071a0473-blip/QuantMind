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
10. The React workspace sends natural-language questions through
    `quantmind.search.parse_query`, then uses the structured report and market
    endpoints. The terminal never substitutes demo values when a provider or
    canonical store is unavailable.

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
- `quantmind.historical` computes versioned trading-session features, searches
  transparent historical analogues, and runs chronological baseline evaluation.
- `quantmind.outcomes` resolves forecast horizons into resolved, censored, or
  invalidated outcomes without rewriting the original forecast.
- `quantmind.search` performs deterministic query understanding for recognizable
  entities and metrics before any future lexical, semantic or Hindsight
  retrieval adapter is selected.

## Current limitations

The repository still does not claim complete Fortune 500 coverage or
institutional-grade provider coverage. Phase 3 provides the deterministic
feature, analogue, outcome-resolution, dossier, and baseline evaluation
surfaces for securities that have canonical market bars. Peer-universe
comparison, full-text/semantic indexing, measured hybrid ranking and calibrated
forecasting remain later work. Phase 4 now provides the terminal search and
workspace surface, but it does not claim those later retrieval systems exist
until they are backed by indexed source records and evaluation results.
