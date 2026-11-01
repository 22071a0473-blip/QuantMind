# QuantMind progress

## Gate 0 — correctness and trust boundary

Status: passed locally on 2026-03-10.

- Deterministic operation remains available when Groq and Hindsight credentials
  are absent.
- Missing market features remain unavailable rather than being copied from
  unrelated values.
- GET report and legacy research routes do not retain or reflect into Hindsight.
- Hindsight records use readable research text plus a structured event line.
- Health reports database, Hindsight, Groq and universe status separately.

## Gate 1 — hypothesis ledger

Status: passed locally on 2026-03-10.

- Append-only hypotheses use SQLite immutability triggers and deterministic
  record hashes.
- Duplicate forecast commits return the existing row; superseding creates a
  new linked row.
- Baseline probabilities are deterministic and require at least 30 complete
  ticker/SPY observations.
- Resolution records abnormal return, Brier score and log-loss.
- The frontend exposes the ledger with explicit commit, loading, error and
  unavailable-data states.

## Gate 2 — source-backed analogue corpus

Status: passed locally on 2026-11-01.

- The committed corpus contains **1,502 events across 34 tickers including
  SPY**, with deterministic event IDs and source URLs.
- Event counts are 651 earnings releases, 408 leadership changes, 330
  price-only events, 88 material agreements, 13 restructuring events, 10
  merger/acquisition events and 2 cyber incidents.
- The corpus snapshot imports into an empty database with the same event-ID set.
- Cutoff-safe analogue retrieval, L0/L1/L2 relaxation, forward-return
  statistics, precedent API behavior and ledger integration were verified.
- Hindsight returned HTTP 401 during verification. Structured SQLite analogues
  remain the authoritative fallback, and the API reports
  `semantic_status="unauthorized"` without failing.
- Validation: 73 backend tests passed, Ruff passed, frontend typecheck passed,
  and the production frontend build passed.
- The Stage 2 finish changes are committed locally as `a88d525` and pushed to
  the configured GitHub `main` branch.

Known Gate 2 limitations:

- The attempted 150+ ticker expansion was blocked by intermittent SEC DNS
  resolution failures; the 1,502-event corpus remains the measured baseline.
- Restructuring, merger/acquisition and cyber-incident types are still flagged
  `limited`.
- Leadership-change events do not yet separate officer changes from routine
  director changes.

## Gate 3 — Time Machine

Status: not started as of 2026-11-01.

The next stage must begin with offline pre-flight fixes, then add a single
cutoff definition, historical replay API, differential lookahead tests and the
Time Machine UI. It must not depend on network access, historical news or live
LLM synthesis.
