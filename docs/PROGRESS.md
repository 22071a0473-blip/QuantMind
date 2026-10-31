# QuantMind progress

## Gate 0 — correctness and trust boundary

Status: passed locally on 2026-03-10.

- Ruff: passed for `quantmind`, `tests`, and `scripts`.
- Backend tests: 52 passed.
- Frontend typecheck: passed.
- Frontend production build: passed.
- Optional Groq and Hindsight configuration: deterministic operation remains available when keys are absent.
- Missing market features remain unavailable rather than being copied from unrelated values.
- GET report and legacy research routes do not retain or reflect into Hindsight.
- Hindsight records use readable research text plus a structured event line; unsupported outcome claims are not inferred.
- Health reports database, Hindsight, Groq and universe status separately.
- Superseded planning documents are retained under `docs/archive/`.

The Hindsight service itself was not configured in this environment, so cloud reachability is reported as `not_configured` rather than claimed as verified.

## Gate 1 — hypothesis ledger

Status: passed locally on 2026-03-10.

- Append-only hypotheses use SQLite immutability triggers and deterministic
  record hashes.
- Duplicate forecast commits return the existing row; superseding creates a
  new linked row.
- Baseline probabilities are deterministic and require at least 30 complete
  ticker/SPY observations.
- Resolution uses the first bar strictly after the information cutoff and
  records abnormal return, Brier score, and log-loss.
- The frontend exposes the ledger as a security-monitor tab with explicit
  commit, loading, error, and unavailable-data states.
- Gate smoke test committed one `TEST` forecast, returned a verified detail,
  returned paginated list metadata, and exposed the expected insufficient-data
  calibration state.
- Validation: 63 backend tests passed, Ruff passed, frontend typecheck passed,
  and the production frontend build passed.

## Gate 2 — analogue foundation and precedent surface

Status: foundation implemented locally on 2026-10-31.

- Added idempotent `market_events` storage with deterministic event IDs,
  forward-return completion dates, and strict cutoff eligibility.
- Added weighted L0/L1/L2 analogue retrieval, stable bootstrap intervals,
  shrinkage probabilities, and explicit insufficient-sample refusals.
- Added current-event detection and read-only `/api/precedent/{ticker}` with
  future-cutoff rejection.
- Added explicit `--write` protection to event backfill and a coverage report
  script. The current checked-out corpus contains zero structured events, so
  coverage is honestly reported as empty rather than inferred.
- Added a Precedent tab with loading, no-event, insufficient, semantic-status,
  similarity, source-link, and forward-return states.
- Installed Hindsight probe output confirms no public operation-status polling
  method and no `arecall` tag-filter parameter.
- Validation: 67 backend tests passed, Ruff passed, frontend typecheck passed,
  and the production frontend build passed.
