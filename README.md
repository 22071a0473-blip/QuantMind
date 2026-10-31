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
| `scripts/ingest_universe.py` | Versioned Fortune 500 CSV ingestion and identity-resolution report |
| `scripts/ingest_market.py` | Resumable single-security historical or incremental market ingestion |
| `scripts/report_coverage.py` | Machine-readable canonical-store coverage report |
| `scripts/historical_research.py` | Point-in-time features, analogue search, dossier, and walk-forward evaluation |
| `scripts/resolve_outcome.py` | Deterministic forecast outcome resolution |
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

## Canonical local database

The repository now includes a portable SQLite canonical store for normalized
companies, securities, market bars, provenance, ingestion jobs, quality issues,
research reports, forecasts, and resolved outcomes. Hindsight remains the
semantic research-memory layer; it is not used as the numerical financial
database.

Initialize or inspect the local database with:

```powershell
uv run python scripts/init_database.py
```

By default this creates `data/quantmind.db`. The database is local runtime
state and should not be committed. Use `--database` to select another path:

```powershell
uv run python scripts/init_database.py --database data/dev-quantmind.db
```

The current store is the persistence foundation for the planned incremental
market, filing, fundamentals, forecast-resolution, and coverage jobs. Those
jobs populate it through typed records and idempotent upserts. Raw numerical
bars stay in SQLite; only compact source-backed events and research reports
belong in Hindsight.

### Phase 2 ingestion commands

The Fortune 500 command intentionally accepts a verified CSV export instead of
silently scraping an unstable page. Required columns are `rank` and
`company`; `ticker`, `exchange`, `headquarters`, and `website` are optional.
Unresolved or private companies are persisted as companies and reported rather
than guessed:

```powershell
uv run python scripts/ingest_universe.py `
  --year 2025 `
  --source data/fortune500-2025.csv `
  --report data/fortune500_coverage.json
```

After a security has been resolved into the database, ingest at least two years
of daily OHLCV data. The yfinance adapter preserves adjusted-close semantics,
provider provenance, availability timestamps, duplicate handling, retry counts,
and data-quality issues:

```powershell
uv run python scripts/ingest_market.py `
  --ticker AAPL `
  --security-id <resolved-security-uuid> `
  --years 2 `
  --checkpoint .cache/market/aapl.json
```

Use the same command for an incremental update. It starts the request after the
latest stored observation and remains idempotent:

```powershell
uv run python scripts/ingest_market.py `
  --ticker AAPL `
  --incremental `
  --checkpoint .cache/market/aapl.json
```

SEC Company Facts ingestion is available as a typed provider boundary and
preserves filing dates, period dates, units, forms, accession numbers, and
point-in-time availability. A real SEC User-Agent is required. Coverage can be
exported at any time:

```powershell
uv run python scripts/report_coverage.py `
  --database data/quantmind.db `
  --output data/coverage.json
```

The initial adapter uses Yahoo Finance for market history and SEC Company Facts
for fundamentals. These sources are suitable for a reproducible hackathon
prototype, not a claim of licensed institutional-grade market-data coverage.

## Phase 3 historical research

Phase 3 keeps numerical bars and feature snapshots in SQLite and uses Hindsight
only for compact research memory. Features are computed by trading-session
position, not calendar offsets, and use adjusted close when the provider
supplies it. Every feature snapshot carries the `phase3-v1` definition version,
price-basis label, source-bar count, and missing-feature list.

Compute and persist features:

```powershell
uv run python scripts/historical_research.py features `
  --ticker AAPL `
  --database data/quantmind.db
```

Search historical analogues as of a strict decision date. The baseline uses
standardized numerical distances, excludes the target observation, excludes
information unavailable by the cutoff, and reports subsequent 1/5/20/60/120/252
session outcomes when available:

```powershell
uv run python scripts/historical_research.py analogues `
  --ticker AAPL `
  --date 2025-01-15 `
  --limit 10 `
  --database data/quantmind.db
```

Generate a reproducible dossier or run the chronological baseline evaluation:

```powershell
uv run python scripts/historical_research.py dossier `
  --ticker AAPL `
  --date 2025-01-15 `
  --database data/quantmind.db

uv run python scripts/historical_research.py evaluate `
  --ticker AAPL `
  --horizon 20 `
  --database data/quantmind.db
```

The evaluator reports sample counts, excluded observations, MAE, RMSE,
directional accuracy, realized-return distribution, and explicit limitations.
It is a transparent historical baseline, not a calibrated probability or
profitability claim. Forecasts are resolved separately so censored or
invalidated outcomes are not silently treated as failures or successes.

## API routes

| Route | Description |
|---|---|
| `GET /api/health` | Service status and generated universe size |
| `GET /api/search?q=...` | Ranked, grouped asset search |
| `GET /api/query?q=...` | Deterministic intent, entity, metric and retrieval-strategy routing |
| `GET /api/universe` | Typed asset catalog |
| `GET /api/market/{ticker}` | Canonical OHLCV series, company profile and coverage metadata |
| `GET /api/report/{ticker}?memory=true` | Research report |
| `GET /api/signals/{ticker}` | Deterministic signal analysis |
| `GET /api/memory/{ticker}` | Asset memory status and recalled precedents |
| `GET /api/reflect/{ticker}` | Hindsight reflection |
| `POST /analyze` | Typed asynchronous analysis graph |
| `GET /docs` | FastAPI OpenAPI documentation |

The legacy `/research` page remains available while the React terminal is the
primary flow.

## Phase 4 research workspace

The React workspace uses a restrained Bloomberg-style terminal layout: dense
navigation, keyboard-first search, compact quote panels, tabular evidence and
explicit data-quality states. It is intentionally not a trading terminal and
does not invent prices, analyst targets or source metadata.

The global search palette supports Ctrl+K/Cmd+K, recent searches, grouped
canonical-universe results, keyboard navigation and a 150 ms debounce. Natural
language questions are routed by `GET /api/query` before retrieval: recognizable
tickers and metrics use deterministic structured paths, while broad questions
advertise the lexical, structured and Hindsight strategies they require.

The security workspace at `/stock/{ticker}` combines the live report with any
stored canonical OHLCV history, confidence coverage, ranked movement drivers,
source-linked news and Hindsight precedent. If the SQLite store has no series or
the provider has no evidence, the UI labels that gap instead of displaying a
placeholder value. Set `QUANTMIND_DATABASE` when the canonical store is not
`data/quantmind.db`.

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
