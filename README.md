# QuantMind Terminal

> **Why did this asset move, and what does history say about the next move?**

QuantMind is a memory-backed market research terminal for stocks, ETFs, and
crypto assets. It combines live market data, deterministic signal analysis,
Groq narrative synthesis, and Vectorize Hindsight memory into a structured
five-factor research memo.

It is deliberately not a chatbot. The output is an auditable research artifact:
the live snapshot and citations show what is known now, the deterministic
confidence layer shows how the score was calculated, and Hindsight shows which
past observations were recalled.

## The problem

Understanding a large move usually requires stitching together price action,
volume, news, sector context, macro conditions, company history, and previous
market reactions. A stateless LLM may summarize today's headlines, but it does
not automatically remember how a similar catalyst behaved in the same asset.

QuantMind compresses that workflow into a repeatable report while keeping
evidence and uncertainty visible. It does not promise a price prediction and it
does not replace investment advice.

## What the report contains

Every research run produces five consistent factors:

1. **Why it moved** — a catalyst classification grounded in live news and
   price/volume evidence.
2. **Deep research** — company, sector, macro, and news context, with
   insufficient evidence called out instead of invented.
3. **Confidence meter** — a deterministic score, coverage percentage, regime,
   vector groups, and signal audit.
4. **Historical precedent** — similar prior reports recalled from the asset's
   Hindsight memory bank.
5. **Facts vs. reality** — reported evidence, current narrative, and the gap
   between them.

The report also includes an experimental leadership and success-roadmap section.
Those fields are explicitly labeled as hypotheses when the available sources do
not support a factual conclusion.

## Why Hindsight matters

Hindsight is the differentiator, not a storage add-on. QuantMind uses the
official Python client directly:

```text
Live market/news context
        │
        ├── recall(current headlines and catalyst context)
        │
        ▼
Deterministic confidence + Groq evidence-grounded synthesis
        │
        ├── retain(completed research report)
        └── reflect(periodic pattern summary)
        │
        ▼
The next report has historical context
```

The memory lifecycle is:

1. **Recall** — the first three live headlines become the semantic query. If
   there is no news, QuantMind uses an asset/price/volume/catalyst query.
2. **Analyze** — recalled reports are parsed into historical precedent records
   and contribute to the memory signal.
3. **Retain** — the completed report is stored in the asset-specific Hindsight
   bank.
4. **Reflect** — every fifth retained market event triggers a Hindsight
   reflection that is stored as a meta-insight.

The web UI's **With Memory** and **Without Memory** links make this effect
visible. Memory-off runs skip recall and apply a clearly labeled deterministic
confidence penalty; this is a comparison baseline, not a claim that confidence
can be mathematically guaranteed by memory alone.

Learn more from the [Hindsight documentation](https://hindsight.vectorize.io/)
and the [Hindsight source repository](https://github.com/vectorize-io/hindsight).

## Architecture

```text
Jinja2 terminal UI / API client
              │
              ▼
        FastAPI application
              │
              ▼
       QuantMindEngine
       ┌──────┼─────────┐
       │      │         │
   yfinance  Hindsight  Groq
 CoinGecko  recall/    synthesis
            retain/
            reflect
              │
              ▼
  12-signal compatibility analytics
  + separate 50-parameter confidence audit
```

The explicit `/analyze` endpoint also exposes a typed asynchronous state graph
with acquisition, recall, analysis, completion, and failure phases. The graph
is dependency-free and does not pretend to be a separate orchestration
framework.

## Deterministic confidence audit

The report's compatibility analytics remains in `quantmind/analytics.py`.
Alongside it, `quantmind/confidence_engine.py` evaluates 50 auditable
parameters across five vectors:

- Market
- Technical
- Fundamental
- Macro
- Sentiment

Missing provider data is recorded as unavailable and lowers coverage; it is not
silently converted into fabricated facts. The current live provider set
populates the parameters it can support and leaves the rest explicit for
future connectors.

## Current integrations

| Layer | Implementation |
|---|---|
| Web/API | FastAPI, Uvicorn, Jinja2 |
| Memory | Vectorize Hindsight Python SDK |
| Synthesis | Async Groq client |
| Equities/ETFs | yfinance |
| Crypto | CoinGecko via `CRYPTO:<coin-id>` |
| Deterministic analysis | Python signal and confidence engines |
| Runtime | Docker-compatible FastAPI service |

The repository also contains typed boundaries for future macro, sector,
filings, flows, news, and correlation providers. They report unavailable data
honestly; they are not fixture data.

## Run locally

### Prerequisites

- Python 3.11+
- A Hindsight Cloud URL and token
- A Groq API key for narrative synthesis

### Configure

```powershell
# Run from the repository root; .env.example is beside pyproject.toml.
Copy-Item .env.example .env
notepad .env
```

Set these values in `.env`:

```env
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_TOKEN=your_rotated_hindsight_token
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Never commit `.env`, API keys, or tokens. If a token has ever been pasted into
chat or a public issue, revoke it and create a new one.

### Install and start

```powershell
uv sync
uv run uvicorn quantmind.app:app --reload --port 8000
```

Open <http://127.0.0.1:8000>.

### Web terminal

The Phase 1 React terminal lives in `web/` and calls the typed FastAPI search
endpoints:

```powershell
npm --prefix web install
npm --prefix web run dev
```

Press **Ctrl+K** to open the command palette. It searches with a 150 ms
debounce, groups results by asset kind, and links to the stock and memory
routes.

## Research workflow

1. Run `PLTR`, `CRWD`, or `CRYPTO:bitcoin` with **With Memory**.
2. Show the five-factor memo, confidence audit, source links, and Hindsight
   memory count.
3. Open the **Without Memory** link for the same asset.
4. Compare the empty historical-precedent factor and the labeled confidence
   penalty.
5. Run the asset again with memory enabled after several retained reports.
6. Show how the recalled precedent and periodic reflection change the report.

Useful API calls:

```text
GET  /api/report/PLTR?memory=true
GET  /api/report/PLTR?memory=false
GET  /api/signals/PLTR
GET  /api/memory/PLTR
GET  /api/reflect/PLTR?query=What%20patterns%20emerge%3F
POST /analyze
GET  /docs
```

## Safety and scope

QuantMind is a research and analysis tool, not financial advice. It does not
guarantee returns, identify illegal insider information, or make autonomous
trades. Every report includes a disclaimer, and unsupported conclusions should
remain labeled as insufficient evidence or hypotheses.

## License

See the repository license and the licenses of the upstream providers and SDKs.
