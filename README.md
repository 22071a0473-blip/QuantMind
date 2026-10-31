# QuantMind

> **Evidence-first market research for understanding why an asset moved.**

QuantMind is a research workspace for equities, ETFs, and crypto. It combines
live provider data, normalized financial records, deterministic market
analytics, source-backed event history, and persistent [Hindsight](https://hindsight.vectorize.io/)
memory in one Bloomberg-inspired terminal interface.

QuantMind is not a brokerage terminal and does not place trades. Its purpose is
to help a researcher answer a more useful question than “what is the price?”

> What changed, what evidence supports the explanation, and what happened the
> last time a similar situation occurred?

**Research tool only. Not financial advice.**

## Product overview

Every research report is organized around five evidence panels:

1. **Why it moved** — observed price and volume behavior, available catalyst
   evidence, and ranked movement drivers.
2. **Deep research** — company, sector, macro, and news context, with gaps
   shown instead of silently completed.
3. **Confidence audit** — deterministic signal coverage, regime, score, and
   parameter-level availability.
4. **Historical precedent** — prior event records and research reports recalled
   from Hindsight.
5. **Facts versus reality** — reported facts, market narrative, and the
   difference between them.

The interface separates verified evidence, calculated metrics, historical
analogy, and interpretation. Unsupported conclusions are labeled as hypotheses
or unavailable; the system does not manufacture prices, citations, targets, or
missing observations.

## Why persistent memory matters

A conventional market brief can summarize today’s headlines while losing the
most valuable context: what happened when a comparable catalyst appeared
before. QuantMind retains compact research reports and source-backed event
records so later queries can retrieve prior precedent.

```text
Provider data and source records
                │
                ├── point-in-time eligibility
                ├── deterministic signals and feature calculations
                ├── Hindsight recall of related precedent
                ▼
        evidence-grounded research report
                │
                ├── retain compact report memory
                └── reflect periodic pattern summaries
```

Hindsight is the long-term research-memory layer. SQLite remains the
authoritative local store for normalized companies, securities, market bars,
financial facts, forecasts, outcomes, provenance, and ingestion jobs. Raw
numerical time series are not pushed into Hindsight.

## Bloomberg-style workspace

The React workspace is intentionally information-dense rather than
dashboard-like:

- dark navy terminal surfaces with restrained amber accents;
- global Ctrl+K/Cmd+K search from every main view;
- exact, prefix, token, and fuzzy canonical-universe search;
- grouped results, keyboard navigation, recent searches, and 150 ms debounce;
- security monitors with quote context, adjusted-close charts, coverage, and
  quality indicators;
- tabs for overview, source evidence, and Hindsight precedent;
- responsive layouts for desktop, tablet, and mobile;
- explicit loading, error, unavailable-data, and incomplete-coverage states.

Open `/` for the workspace and `/stock/{ticker}` for a security monitor.

## Architecture

```text
React / Vite / TypeScript terminal
                  │
                  ▼
             FastAPI API
       ┌──────────┼──────────┐
       │          │          │
  Structured   Provider   Hindsight
   SQLite      adapters   memory
       │          │          │
       └──────────┼──────────┘
                  ▼
        typed evidence and reports
                  │
                  ▼
      deterministic analytics + synthesis
```

| Area | Responsibility |
|---|---|
| `quantmind/app.py` | FastAPI routes, validation, report and market responses |
| `quantmind/search.py` | Deterministic query intent, ticker, metric, and retrieval routing |
| `quantmind/storage.py` | Typed SQLite canonical store and idempotent persistence |
| `quantmind/sources.py` | Live market, news, and provider acquisition |
| `quantmind/analytics.py` | Deterministic movement signals and regime analysis |
| `quantmind/historical.py` | Point-in-time features, analogue search, and evaluation |
| `quantmind/outcomes.py` | Resolved, censored, and invalidated forecast outcomes |
| `quantmind/memory.py` | Hindsight retain, recall, reflection, and precedent formatting |
| `web/` | React/Vite/TypeScript/Tailwind research terminal |
| `scripts/` | Universe, ingestion, backfill, coverage, and research commands |
| `data/` | Generated universe and validated source-linked event data |
| `docs/` | Architecture, decisions, build plan, and specifications |

## Data sources and provenance

QuantMind uses a provider when available and exposes provider limitations.

| Provider | Role |
|---|---|
| Yahoo Finance through `yfinance` | Historical OHLCV, snapshots, earnings dates, and company metadata |
| SEC EDGAR | 8-K filings, item codes, filing timestamps, headlines, and URLs |
| Nasdaq Trader | Cached stock and ETF listings |
| CoinGecko | Top crypto assets and identifiers |
| Vectorize Hindsight | Persistent research memory and reflection |
| Groq | Optional evidence-grounded narrative synthesis |

SEC requests require a descriptive contact identifier in the User-Agent.
Provider terms, rate limits, coverage, and freshness apply. A source-backed
event label does not override the underlying price-data validation.

## Quick start

### Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+
- Docker Desktop, if using the container workflow
- Hindsight Cloud URL and token for memory features
- Groq API key for optional narrative synthesis

### Configure

From the repository root:

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

Never commit `.env`, API keys, or tokens. Rotate credentials that have been
exposed in a chat, issue, screenshot, log, or repository.

### Install

```powershell
uv sync --extra test
Push-Location web
npm install
Pop-Location
```

### Run locally

Start the API:

```powershell
uv run uvicorn quantmind.app:app --reload --port 8000
```

Open <http://127.0.0.1:8000>. The API serves `web-dist/` when present and
falls back to `web/dist/` for local development.

For Vite hot reload, use a second terminal:

```powershell
Push-Location web
npm run dev
Pop-Location
```

## Search and query routing

The search palette is optimized for canonical asset discovery. Results are
ranked by exact ticker, ticker prefix, name prefix, name token, and fuzzy
similarity. Crypto results route to `CRYPTO:<coin-id>`.

Natural-language questions are routed deterministically before retrieval:

```powershell
curl "http://127.0.0.1:8000/api/query?q=AAPL%2020-day%20return%20and%20volatility"
```

Recognizable entities and numerical metrics use structured paths. Broader
questions expose the retrieval strategies they require rather than sending
every query to an LLM.

## API surface

| Route | Purpose |
|---|---|
| `GET /api/health` | Service status and generated-universe size |
| `GET /api/search?q=...` | Ranked canonical asset search |
| `GET /api/query?q=...` | Deterministic query intent and retrieval routing |
| `GET /api/universe` | Typed asset catalog |
| `GET /api/market/{ticker}` | Stored OHLCV series, company profile, and coverage |
| `GET /api/report/{ticker}?memory=true` | Evidence-grounded research report |
| `GET /api/signals/{ticker}` | Deterministic signal analysis |
| `GET /api/memory/{ticker}` | Asset-specific memory status |
| `GET /api/reflect/{ticker}` | Hindsight reflection |
| `POST /api/ledger/commit` | Explicitly commit a deterministic forecast |
| `GET /api/ledger` | Paginated hypothesis list |
| `GET /api/ledger/{id}` | Hypothesis, resolution, and hash verification |
| `GET /api/ledger/stats` | Provenance-scoped calibration metrics |
| `POST /analyze` | Typed asynchronous analysis graph |
| `GET /docs` | FastAPI OpenAPI documentation |

The legacy `/research` page remains available while the React workspace is the
primary user experience.

## Hypothesis Ledger

The Ledger is QuantMind's accountability layer. It records an immutable,
timestamped claim with its information cutoff, provenance, algorithm version,
evidence identifiers, and deterministic probability. A forecast is committed
only through `POST /api/ledger/commit`; ordinary report and read routes do not
write ledger rows.

The current `baseline-v0` compares historical ticker returns with SPY and
refuses to create a forecast below 30 complete observations. Once the horizon
elapses, the resolver records adjusted-close returns and classifies the result
as resolved, censored, or invalidated without filling missing prices. Metrics
remain hidden until 20 resolved observations exist, and live-forward results
are never mixed with historical replay results.

## Build the asset universe

The generated catalog combines S&P 100 metadata, Nasdaq Trader listings, and
the top 250 CoinGecko assets. Provider responses are cached by the build
script and the generated file should not be hand-edited.

```powershell
$env:QUANTMIND_SEC_USER_AGENT = "Your Name contact@example.com"
uv run python scripts/build_universe.py
```

Output: `data/universe.json`.

## Historical event memory

The event pipeline supports:

- contract wins and major partnership deals;
- earnings and earnings-surprise classifications;
- layoffs and restructuring;
- leadership changes;
- mergers and acquisitions;
- cyber incidents;
- price-only events when no filing explains the move.

Each event carries day-0 return, abnormal return versus SPY, volume ratio, and
nullable forward 1-, 5-, 20-, and 60-day returns. Missing future observations
remain `null`; they are never inferred.

Always inspect a dry run before writing to Hindsight:

```powershell
$env:QUANTMIND_SEC_USER_AGENT = "Your Name contact@example.com"
uv run python scripts/backfill_memory.py `
  --tickers CRM META NVDA `
  --years 5 `
  --max-events-per-ticker 10 `
  --dry-run
```

Useful options:

| Option | Function |
|---|---|
| `--tickers` | Tickers to process |
| `--years` | Historical window |
| `--max-events-per-ticker` | Cap for price-only events |
| `--checkpoint` | Resumable checkpoint path |
| `--dry-run` | Report without calling Hindsight |
| `--list-events TICKER` | Print event dates, types, returns, and headlines |
| `--type TYPE` | Filter event-list output |

The backfill uses the global `quantmind-events` bank with deterministic
document IDs, making reruns idempotent. Cost output is explicitly labeled
unverified; do not assume a fixed credit cost per memory.

Inspect retained events:

```powershell
uv run python scripts/verify_memory.py
```

## Canonical SQLite store

SQLite stores normalized structured data locally:

- companies and securities;
- daily market bars;
- financial facts and point-in-time availability;
- data sources and ingestion jobs;
- quality issues and coverage;
- research reports, forecasts, and outcomes;
- historical feature and evaluation snapshots.

Initialize a database:

```powershell
uv run python scripts/init_database.py
```

The default path is `data/quantmind.db`. Override it with `--database` or set
`QUANTMIND_DATABASE` for API market-series requests.

### Market and fundamentals ingestion

Ingest a verified Fortune 500 CSV:

```powershell
uv run python scripts/ingest_universe.py `
  --year 2025 `
  --source data/fortune500-2025.csv `
  --report data/fortune500_coverage.json
```

Ingest historical market data for a resolved security:

```powershell
uv run python scripts/ingest_market.py `
  --ticker AAPL `
  --security-id <resolved-security-uuid> `
  --years 2 `
  --checkpoint .cache/market/aapl.json
```

Run an incremental update with the same command and `--incremental`. The
adapter preserves adjusted-close semantics, provider timestamps, retries,
duplicates, and rejected-record details.

Export coverage:

```powershell
uv run python scripts/report_coverage.py `
  --database data/quantmind.db `
  --output data/coverage.json
```

## Historical research and evaluation

Phase 3 computes versioned trading-session features, point-in-time analogue
matches, and a transparent walk-forward baseline. It excludes information that
was not available by the research cutoff and reports missing features rather
than imputing them.

```powershell
uv run python scripts/historical_research.py features `
  --ticker AAPL `
  --database data/quantmind.db

uv run python scripts/historical_research.py analogues `
  --ticker AAPL `
  --date 2025-01-15 `
  --limit 10 `
  --database data/quantmind.db

uv run python scripts/historical_research.py dossier `
  --ticker AAPL `
  --date 2025-01-15 `
  --database data/quantmind.db

uv run python scripts/historical_research.py evaluate `
  --ticker AAPL `
  --horizon 20 `
  --database data/quantmind.db
```

Forecast outcomes are resolved separately:

```powershell
uv run python scripts/resolve_outcome.py `
  --ticker AAPL `
  --forecast data/forecast.json `
  --database data/quantmind.db
```

`resolved`, `censored`, `invalidated`, and `unresolved` are distinct states.
The evaluator is an interpretable historical baseline, not a calibrated
probability model or profitability claim.

## Validation

Run the backend checks:

```powershell
uv run ruff check quantmind tests scripts
uv run pytest
```

Run the frontend checks:

```powershell
Push-Location web
npm run typecheck
npm run build
Pop-Location
```

The test suite covers event serialization, SEC parsing, classifier behavior,
forward returns, universe parsing, query routing, temporal eligibility,
historical features, idempotent storage, configuration, and the analysis
graph.

## Phase 4 search and memory verification

Research search executes across the canonical asset universe, locally persisted
research reports and the shared Hindsight event bank:

```text
GET /api/search/research?q=why%20did%20AAPL%20move
```

The response includes parsed intent, typed results, source labels, scores,
Hindsight availability and warnings when an external source is unavailable.
Local lexical results remain usable when Hindsight is not configured.

Before claiming that memory retrieval is operational, run:

```powershell
python scripts/verify_memory.py --json
```

The probe checks configuration, bank access, a marked write, recall, repeated
document-ID behavior and temporal-query support without printing credentials.
The installed Hindsight SDK currently does not expose public deletion or
operation-status methods, so use a disposable verification bank when cleanup
is required.

## Deployment

The repository includes Docker and Render configuration:

```powershell
docker compose up --build
```

The service listens on port `8000`. Configure deployment secrets and the SEC
User-Agent in the deployment environment, never in the repository.

## Scope and limitations

QuantMind does not:

- provide financial advice or guarantee returns;
- place trades or manage brokerage accounts;
- infer private or illegal insider information;
- treat a headline as proof of causality;
- replace primary-source diligence;
- convert unavailable fields into fabricated facts;
- claim complete Fortune 500 coverage without measured source coverage;
- claim semantic or hybrid search superiority without evaluation results.

Market movements are multi-causal. The confidence score measures evidence
coverage and signal availability; it is not the probability of a successful
trade. Historical precedent describes prior observations, not guaranteed
future behavior.

## License and third-party terms

See the repository license. Each upstream provider and SDK has its own terms,
rate limits, attribution requirements, and data-usage restrictions.
