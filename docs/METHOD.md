# Hypothesis Ledger method

The Hypothesis Ledger is QuantMind's deterministic record of what the system
believed, when it believed it, and how that belief performed. It is separate
from narrative research: an LLM may summarize evidence, but it never chooses
the forecast probability.

## Forecast target

Each hypothesis predicts whether the ticker will outperform or underperform
SPY over 5, 20, or 60 trading days. The target is abnormal return:

```text
abnormal return = ticker adjusted-close return - SPY adjusted-close return
```

The entry observation is the first trading bar strictly after
`information_cutoff`. The ending observation is the requested number of
trading sessions after that entry. Adjusted close is preferred because it
preserves split and dividend semantics; close is used only when adjusted close
is unavailable.

## Baseline forecast

`baseline-v0` estimates the probability from the historical frequency of
positive abnormal returns for the same ticker and horizon. It refuses to create
a forecast with fewer than 30 complete ticker/benchmark observations. This is
an intentionally conservative baseline, not a claim of calibrated predictive
power.

## Resolution and metrics

Resolved rows record raw ticker return, benchmark return, abnormal return,
outcome, price dates, and source providers. An `outperform` hypothesis is a
success when abnormal return exceeds its threshold; an `underperform`
hypothesis is a success when it does not.

The Brier score is `(probability - outcome)^2`. Log-loss uses the probability
assigned to the realized outcome, clipped away from zero and one. Calibration
statistics are hidden until at least 20 resolved observations exist for the
selected provenance.

Missing future observations are never interpolated. A hypothesis is `censored`
when its horizon has not elapsed or its start is unavailable, and
`invalidated` when an elapsed horizon cannot be resolved because required
market data is missing.

## Immutability and provenance

Hypotheses and resolutions are append-only SQLite records. Database triggers
reject edits and deletes; status transitions are the only permitted hypothesis
updates. Corrections create a new hypothesis linked through `supersedes_id`.

`live_forward` and `historical_replay` are kept separate so retrospective
experiments cannot silently improve live calibration metrics. Every row stores
its cutoff, algorithm version, code version, evidence identifiers, and a
record hash that can be verified through the API.

## Stage 2 analogue engine

Structured events are stored in SQLite `market_events`; Hindsight's shared
`quantmind-events` bank is semantic discovery only. Each event has a
deterministic SHA-1 identity, a source URL, an availability timestamp, and
nullable forward-return completion dates. A return contributes to a statistic
only when its completion date is strictly before the query cutoff.

Similarity weights are event type 30%, abnormal day-0 return 20%, volume 15%,
sector 10%, pre-drift 10%, regime 10%, and market-cap bucket 5%. Missing
features are removed from both the numerator and denominator. Retrieval uses
L0 same type and sector, L1 same type, and L2 same taxonomy group, stopping at
the first level with at least eight candidates scoring at least 0.5. Fewer
than five elapsed outcomes is reported as insufficient rather than converted
into a numeric statistic.

Forecast probabilities use
`(hits + 10 * base_rate) / (n + 10)`. The base rate falls back to all events
when the event-type sample is below 15 observations. Bootstrap intervals use a
stable SHA-256 seed derived from event ID, horizon, and cutoff. Current-event
detection prefers a source-backed event in the previous three trading sessions
and otherwise requires a price shock above two trailing standard deviations
and at least 1.5x volume.

SEC Item 5.02 is retained as `leadership_change`, but the item also covers
routine director appointments and departures. It is therefore a
leadership/board filing signal, not proof of an executive-performance change;
the corpus does not claim that every 5.02 filing is economically material.
