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
