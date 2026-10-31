# QuantMind Build Plan

QuantMind is an evidence-grounded market research terminal. It must use live
provider evidence, deterministic analytics, and Hindsight memory without
presenting synthetic data as fact.

## Phase 0 — honest foundation

- Remove demo-only providers, confidence priors, and fake memory records.
- Rename the Python package to `quantmind`.
- Keep missing evidence explicit and make it reduce confidence coverage.
- Keep reproducible tests and linting.

## Phase 1 — universe and search

- Build a real asset universe with `scripts/build_universe.py`.
- Include the S&P 100 with GICS sector, industry, and SEC CIK metadata.
- Include cached Nasdaq Trader `nasdaqlisted.txt` and `otherlisted.txt` data,
  refreshed daily.
- Include the top 250 CoinGecko coins.
- Rank search matches by exact ticker, ticker prefix, name prefix, name token,
  and fuzzy similarity using `rapidfuzz`.
- Add a React/Vite/TypeScript/Tailwind frontend in `web/`.
- Provide Ctrl+K search, 150 ms debounce, keyboard navigation,
  `autocomplete="off"`, grouped results, and routes for `/`, `/stock/:symbol`,
  and `/memory`.
- Use a multi-stage Dockerfile to build the frontend and serve it with FastAPI.
- Acceptance: Python lint and tests pass, the web build passes, and the manual
  demo checklist is documented.

## Later phases

### Phase 3 — historical event memory

- 3.1 Use one global `quantmind-events` bank with deterministic document IDs.
- 3.2 Classify source-backed price events into a stable event taxonomy.
- 3.3 Backfill events with a resumable, dry-run-capable script.
- Verify the bank with `scripts/verify_memory.py`.
- Do not run the full backfill until the dry-run and offline tests pass.

Future phases add source-backed filings, macro, sector, flows, correlations,
historical backtests, and deeper Hindsight pattern evaluation. Do not implement
those phases while completing Phase 1.
