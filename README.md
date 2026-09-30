# QuantMind

> **Evidence-grounded market research for understanding why an asset moved.**

QuantMind is a research terminal for equities, ETFs, and crypto. It combines
live market data, source-backed event history, deterministic analytics, and
Vectorize Hindsight memory to produce a structured research brief.

QuantMind is designed to answer a research question, not to place trades:

> What changed, what evidence supports that explanation, and what happened the
> last time a similar catalyst appeared?

It is a research tool, not financial advice or a prediction guarantee.

## What QuantMind does

A report is organized into five factors:

1. **Why the asset moved** — price, volume, market context, and available
   catalyst evidence.
2. **Deep research** — company, sector, macro, and news context, with missing
   evidence shown explicitly.
3. **Confidence** — a deterministic confidence score, coverage percentage,
   regime, signal groups, and a 50-parameter audit.
4. **Historical precedent** — related observations recalled from Hindsight,
   including source-backed SEC and market-event records.
5. **Facts versus narrative** — reported facts, current market interpretation,
   and the gap between them.

The system also exposes leadership and strategic-opportunity fields when the
available evidence supports them. Unsupported conclusions remain labeled as
hypotheses or unavailable rather than being filled with synthetic data.

## Why memory matters

A normal market brief can summarize today's headlines and still miss the most
useful question: **what happened when this type of event occurred before?**
QuantMind retains completed reports and historical event records so later
research can compare the current situation with prior observations.

The live research loop is:

```text
Market/news data
      │
      ├── recall related reports and event precedents
      ▼
Deterministic signals + confidence coverage
      │
      ├── Groq evidence-grounded synthesis
      ├── retain completed report
      └── periodic reflect pattern summary
      ▼
The next report has historical context
```

Memory-enabled and memory-disabled report modes are available in the UI. The
memory-disabled mode is a comparison baseline: it skips historical recall and
applies a clearly labeled deterministic penalty. It is not a claim that memory
alone guarantees better returns.

Historical event backfill uses one global Hindsight bank,
`quantmind-events`, with deterministic document IDs. Re-running the same event
replaces the same document instead of creating an uncontrolled duplicate.

## Architecture

```text
React/Vite web terminal
          │
          ▼
FastAPI application
   ┌──────┼─────────┐
   │      │         │
yfinance SEC/     Hindsight
CoinGecko filings recall/
         events   retain/reflect
          │
          ▼
Typed event records
          │
          ▼
Deterministic analytics
          │
          ▼
Groq synthesis + research report
```

The repository contains:

| Area | Purpose |
|---|---|
| `quantmind/` | FastAPI application, analytics, confidence engine, providers, and memory adapters |
| `web/` | React, Vite, TypeScript, and Tailwind search/research interface |
| `scripts/build_universe.py` | Builds the searchable equity, ETF, S&P 100, and crypto universe |
| `scripts/backfill_memory.py` | Dry-run and resumable historical event backfill |
| `scripts/verify_memory.py` | Inspects records in the `quantmind-events` Hindsight bank |
| `scripts/probe_hindsight_sdk.py` | Documents the installed Hindsight SDK surface |
| `data/universe.json` | Generated searchable asset catalog |
| `data/known_events.csv` | Validated, source-linked curated catalyst labels |
| `tests/` | Offline parser, analytics, universe, API, and memory-format tests |
| `docs/` | Build plan and manual validation checklists |

## Data sources

QuantMind uses provider data when available and reports provider gaps
explicitly.

| Source | Use |
|---|---|
| Yahoo Finance via `yfinance` | Historical prices, volume, financial snapshots, earnings dates, and company metadata |
| SEC EDGAR | 8-K filings, filing dates, item codes, headlines, and filing URLs |
| Nasdaq Trader | Cached equity and ETF listings |
| CoinGecko | Top crypto assets and coin identifiers |
| Vectorize Hindsight | Long-term memory, recall, retention, and reflection |
| Groq | Optional evidence-grounded narrative synthesis |

Provider terms, rate limits, and availability apply. SEC requests require a
real contact identifier in the User-Agent. Curated events are labels only; the
backfill computes their market returns from price data.

## Quick start

### Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 18 or newer for the web client
- A Hindsight Cloud URL and API token for memory features
- A Groq API key for narrative synthesis

### Configure the environment

Run these commands from the repository root:

```powershell
Copy-Item .env.example .env
notepad .env
```

Minimum configuration:

```env
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_TOKEN=replace_with_a_rotated_token
GROQ_API_KEY=replace_with_your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
QUANTMIND_SEC_USER_AGENT=Your Name contact@example.com
```

Never commit `.env`, API keys, or tokens. Revoke any credential that has been
shared in a chat, issue, screenshot, or public repository.

### Install dependencies

```powershell
uv sync --extra test
Push-Location web
npm install
Pop-Location
```

### Start the API and web terminal

For the production-style FastAPI service:

```powershell
uv run uvicorn quantmind.app:app --reload --port 8000
```

Open <http://127.0.0.1:8000>. The FastAPI app serves the built frontend when
`web-dist/` is present and falls back to `web/dist/` during local development.

For Vite hot reload in a second terminal:

```powershell
Push-Location web
npm run dev
Pop-Location
```

Press **Ctrl+K** or **Cmd+K** to open the shared search palette. Search supports
exact ticker, ticker prefix, name prefix, name-token, and fuzzy matches. Results
are grouped by asset type and crypto results route to
`/stock/CRYPTO:<coin-id>`.

## Build the asset universe

The generated catalog includes S&P 100 metadata, Nasdaq Trader listings, and
the top 250 CoinGecko assets. The Nasdaq, SEC, and CoinGecko responses are
cached and refreshed according to the build script's cache policy.

```powershell
$env:QUANTMIND_SEC_USER_AGENT = "Your Name contact@example.com"
uv run python scripts/build_universe.py
```

The output is written to `data/universe.json`. Do not hand-edit that generated
file; rebuild it when provider data changes.

## Historical event memory

The event pipeline stores source-backed events such as:

- contracts and major partnership deals,
- earnings and earnings surprise classifications,
- layoffs and restructuring,
- leadership changes,
- mergers and acquisitions,
- cyber incidents,
- abnormal price moves when no source event explains the move.

Each record contains day-0 return, abnormal return versus SPY, volume ratio,
and nullable forward 1-, 5-, 20-, and 60-day returns. A missing forward return
means that enough elapsed market data does not exist; it is never fabricated.

Always run the dry run before any live write:

```powershell
$env:QUANTMIND_SEC_USER_AGENT = "Your Name contact@example.com"
uv run python scripts/backfill_memory.py `
  --tickers CRM META NVDA `
  --years 5 `
  --max-events-per-ticker 10 `
  --dry-run
```

Useful options:

| Option | Purpose |
|---|---|
| `--tickers` | Tickers to process |
| `--years` | Historical window |
| `--max-events-per-ticker` | Cap for price-only events |
| `--checkpoint` | Resumable checkpoint path |
| `--dry-run` | Report events without calling Hindsight |
| `--list-events TICKER` | Print event dates, types, returns, headlines, and URLs |
| `--type TYPE` | Filter `--list-events` output |

Example debug command:

```powershell
uv run python scripts/backfill_memory.py `
  --list-events CRM `
  --type layoffs_restructuring `
  --years 5
```

The backfill reports event counts, average record length, and an
**unverified** Hindsight cost label. It does not assume a fixed credit cost per
memory. Measure account usage before and after a live run.

To inspect the event bank:

```powershell
uv run python scripts/verify_memory.py
```

The live backfill requires explicit credentials and should be run only after
reviewing the dry-run output and checkpoint path.

## API routes

| Route | Description |
|---|---|
| `GET /api/health` | Service status and generated universe size |
| `GET /api/search?q=...` | Ranked, grouped asset search |
| `GET /api/universe` | Typed asset catalog |
| `GET /api/report/{ticker}?memory=true` | Research report |
| `GET /api/signals/{ticker}` | Deterministic signal analysis |
| `GET /api/memory/{ticker}` | Asset memory status and recalled precedents |
| `GET /api/reflect/{ticker}` | Hindsight reflection |
| `POST /analyze` | Typed asynchronous analysis graph |
| `GET /docs` | FastAPI OpenAPI documentation |

The legacy `/research` page remains available while the React terminal is the
primary flow.

## Development checks

Run the focused checks from the repository root:

```powershell
uv run ruff check quantmind tests scripts
uv run pytest
Push-Location web
npm run typecheck
npm run build
Pop-Location
```

The current offline suite covers event serialization, SEC parsing, classifier
rules, forward-return calculation, curated event validation, universe parsing,
configuration, API behavior, and the analysis state graph.

## Deployment

The repository includes a multi-stage `Dockerfile` that builds the web client
and copies the generated frontend and `data/` catalog into the runtime image.

```powershell
docker compose up --build
```

The service listens on port `8000`. Render configuration is provided in
`render.yaml`; set secrets and the SEC User-Agent in the deployment dashboard,
not in the repository.

## Scope and limitations

QuantMind does not:

- provide financial advice or guarantee returns,
- place trades or manage a brokerage account,
- infer private or illegal insider information,
- treat a headline as proof of causality,
- replace primary-source diligence,
- silently turn unavailable provider fields into facts.

Market movements are multi-causal. Confidence is an evidence-coverage measure,
not a probability that a trade will succeed. Historical precedents describe
what happened before; they do not guarantee what happens next.

## License

See the repository license and the licenses, terms, and rate limits of the
upstream providers and SDKs.
