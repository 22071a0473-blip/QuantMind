# Architecture decisions

## ADR-001: Preserve the existing FastAPI and React stack

- **Context:** QuantMind already has a working FastAPI service, typed Pydantic
  contracts, a Vite frontend, provider adapters, and Hindsight integration.
- **Decision:** Extend those boundaries rather than replacing the application
  with a new orchestration framework or dashboard stack.
- **Trade-offs:** Existing provider limitations remain visible while the
  canonical data layer is introduced incrementally.
- **Operational consequence:** New ingestion and research stages expose typed
  interfaces that can be called from the current API and scripts.
- **Reversal criteria:** Replace a boundary only if measured reliability,
  throughput, or temporal correctness cannot be achieved with the current
  implementation.

## ADR-002: Treat Hindsight as research memory, not the financial database

- **Context:** Hindsight is useful for semantic recall and reflection, but raw
  price bars and financial facts require structured queries and reproducible
  calculations.
- **Decision:** Keep normalized numerical data in a relational store and put
  compact source-linked events, research reports, theses, forecasts, and
  lessons in Hindsight.
- **Trade-offs:** The project must maintain two linked persistence boundaries.
- **Operational consequence:** Every memory needs a stable identifier and
  references back to structured records.
- **Reversal criteria:** Reconsider only if Hindsight provides a supported,
  queryable temporal store that satisfies the structured-data requirements.

## ADR-003: Enforce point-in-time eligibility explicitly

- **Context:** Publication, availability, occurrence, ingestion, and outcome
  timestamps are not interchangeable. Using one generic date creates
  look-ahead bias.
- **Decision:** Provider-facing models retain publication/availability
  metadata, and retrospective consumers use `quantmind.temporal`.
- **Trade-offs:** Records with unknown publication timing are excluded from
  strict historical evaluation instead of being silently included.
- **Operational consequence:** Incomplete provider timestamps appear as
  uncertainty and reduce eligible evidence.
- **Reversal criteria:** None; temporal provenance is a correctness invariant.

## ADR-004: Use a transparent baseline before complex analogue models

- **Context:** Historical similarity can look predictive when feature timing
  and overlapping outcomes are hidden.
- **Decision:** Start with versioned trading-session features and Euclidean
  distance over the shared finite features. Exclude target self-matches and
  information unavailable at the decision cutoff.
- **Trade-offs:** The baseline is interpretable and reproducible but does not
  capture nonlinear relationships or establish calibrated probabilities.
- **Operational consequence:** Every query stores its cutoff, feature version,
  matching features, differences, and forward outcomes; later models can be
  compared against this baseline.
- **Reversal criteria:** Replace only after a walk-forward comparison shows a
  reliable out-of-sample improvement without leakage.
