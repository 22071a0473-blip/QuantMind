# QuantMind

QuantMind produces a structured five-factor report for any ticker, backed by live
market data and Hindsight memory. Every number in the report is traceable to a
live provider or an explicitly labeled memory record; see `/api/signals/{ticker}`.

## Five factors

1. **Why it moved** — catalyst classification with source citations.
2. **Deep research** — company, sector, macro, and news evidence.
3. **Confidence meter** — deterministic score, coverage, regime, and signal audit.
4. **Historical precedent** — dated similar moves recalled from the Hindsight bank.
5. **Facts vs reality** — reported facts, market narrative, and evidence gaps.

Leadership and the success roadmap live below the factors in **Extended Analysis
(experimental)**. They are hypotheses, not facts.

## Memory in Action

1. Query `PLTR` and show the confidence meter and the empty first-observation precedent.
2. Run five analyses on different trading dates; each report is retained in the PLTR Hindsight bank.
3. Query PLTR again and show the dated precedent timeline, memory badge, and confidence lift.

Use the `With Memory` / `Without Memory` toggle to demonstrate the control:
without Hindsight, Factor 4 is empty and the precedent contribution is removed
from confidence. Add the before/after screenshots to the hackathon submission.

## Architecture

```text
Frontend (report page + before/after toggle)
  -> FastAPI orchestrator
     -> Hindsight recall (past patterns)
     -> yfinance/CoinGecko fetch (live data)
     -> deterministic confidence engine (12 verified signals)
     -> Groq synthesis (classification + evidence-only narrative)
     -> Hindsight retain (this report)
     -> Hindsight reflect (every 5 market-event retains)
```

The terminal also exposes an explicit async state graph (`/analyze`) for clients that
need phase-level observability. Its separate confidence audit evaluates 50 parameters
across market, technical, fundamental, macro, and sentiment vectors. Missing provider
data is recorded as unavailable rather than converted into invented facts; the legacy
12-signal `analytics.py` engine remains the report's deterministic compatibility layer.

## API

- `GET /` — landing page
- `GET /api/report/{ticker}?date=YYYY-MM-DD&memory=true|false`
- `GET /api/memory/status`
- `GET /api/memory/{ticker}`
- `GET /api/signals/{ticker}`
- `GET /api/reflect/{ticker}?query=...` or `POST`
- `GET /api/health`
- `POST /analyze` — typed graph execution with the 50-parameter confidence audit

Crypto uses `CRYPTO:bitcoin`, `CRYPTO:ethereum`, and other CoinGecko IDs.

## Scoring Alignment

| Criterion | How QuantMind addresses it |
|---|---|
| Innovation | Pattern engine and before/after memory experiment, not a generic chat interface. |
| Hindsight Memory | `retain` + `recall` + `reflect`; Factor 4 is memory-only. |
| Technical Implementation | Deterministic confidence and 12 verified live signals with weights. |
| User Experience | Responsive report page, visible memory badge, citations, and Render deployment. |
| Real-world Impact | Compresses hours of market research into a cited, inspectable report. |

## Run locally

```powershell
Copy-Item .env.example .env
# Set HINDSIGHT_API_URL, HINDSIGHT_API_TOKEN, and GROQ_API_KEY in .env.
# Keep FORESIGHT_DEMO_MODE=false for the live Hindsight demo path.
uv sync
uv run uvicorn foresight.app:app --reload
```

Open http://localhost:8000. Render uses `Dockerfile` and `render.yaml`; configure
the same secrets in Render's secret environment settings.
