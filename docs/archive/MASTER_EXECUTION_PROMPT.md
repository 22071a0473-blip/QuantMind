# QuantMind: MASTER EXECUTION PROMPT (finish everything in one run)

You are a senior full-stack + data engineer working autonomously in **Agent mode** in the QuantMind repo (`22071a0473-blip/QuantMind`, branch `main`). Read `docs/BUILD_PLAN.md` first; it is the detailed spec. **This prompt overrides it where they differ** and defines the execution order, gates, and corrections learned so far.

Work through **all stages below in order, without stopping to ask questions**, unless a **STOP GATE** says otherwise. Commit after every stage with a clear message and push at the end of each stage. If a requirement is impossible (an API doesn't exist, a rate limit blocks it), pick the closest honest alternative, note it in `docs/DECISIONS.md`, and continue.

Host environment: **Windows + PowerShell**, no `make`, no local Docker. Provide `tasks.ps1` mirroring the Makefile (`test`, `lint`, `typecheck`, `build-web`, `dev`, `backfill`, `verify`, `backtest`). Use `npm.cmd` in docs if PowerShell script policy is a concern.

---

## 0. Current state (do NOT redo these)

- **Done:** package renamed to `quantmind`; all demo/synthetic data removed; Ruff in test extras; universe of 13,501 assets (`data/universe.json`, built by `scripts/build_universe.py`) with ranked search (`/api/search`, `/api/universe`, `in_sp100`, `memory_event_count`); React/Vite/TS/Tailwind app in `web/` (Ctrl+K palette, routes `/`, `/stock/:symbol`, `/memory`); FastAPI serves the SPA; multi-stage Dockerfile; `/api/health`.
- **Done (memory, partial):** `quantmind/events.py` (`EventRecord`), `event_memory.py` (global bank `quantmind-events`, `aretain_batch` with tags/metadata/document IDs), `sec_events.py` (EDGAR 8-K incl. `filings.files[]` pagination), `taxonomy.py`, `scripts/backfill_memory.py` (`--tickers --years --max-events-per-ticker --dry-run --checkpoint --list-events`), `verify_memory.py`, `probe_hindsight_sdk.py`. Dry-run for CRM/META/NVDA works (144 memories; CRM layoff event 2023-01-04 found). **No live Hindsight write has happened yet.**
- **Known facts:** the Hindsight SDK has no public operation-status polling; retain is synchronous. Groq free tier hit its daily token cap before (`openai/gpt-oss-120b`, 200k TPD). Real Hindsight credit cost per memory is **unverified**.

---

## 1. Global rules (apply to every stage)

1. **No fake/synthetic data in any production path.** Missing data renders as "Data unavailable". Every memory and every displayed claim carries a real source link + date, or is labeled "model inference".
2. **Never show raw provider errors** (Groq/Hindsight/yfinance/SEC JSON) in the UI. Log server-side; show friendly, per-panel error states.
3. **Secrets only from env.** Never commit `.env`. Update `.env.example` for every new variable.
4. **Type hints, Ruff-clean, async I/O** (`asyncio.to_thread` for blocking yfinance), Pydantic models for every API response. Files under ~400 lines; readable code (no giant one-liners in the frontend).
5. **Tests for every new module**, offline with fixtures. Before each commit run: `python -m ruff check quantmind tests scripts`, `python -m pytest`, `npm --prefix web run typecheck`, `npm --prefix web run build`.
6. **Never invent SDK/API methods.** Check installed packages and docs (Hindsight: https://hindsight.vectorize.io/, https://github.com/vectorize-io/hindsight); write a tiny probe script when unsure.
7. **Not financial advice**: keep a tasteful footer disclaimer.

---

## STAGE A: Memory quality and layoff coverage

### A1. Memory content format (fix before any live write)
Hindsight extracts facts with an LLM and does semantic recall, so JSON blobs recall poorly. Store each event as **natural-language text first, structured block second**:

```
Salesforce (CRM) filed an SEC 8-K on 2023-01-04 announcing a workforce reduction / restructuring plan (Item 2.05). The stock moved +3.57% that day (+2.80% vs the S&P 500) on 2.1x normal volume. Forward returns: 1d +0.8%, 5d +2.1%, 20d +9.6%, 60d +21.0%. Source: <url>

[EVENT] ticker=CRM | sector=Information Technology | date=2023-01-04 | type=layoffs_restructuring | day0=+3.57% | abnormal=+2.80% | fwd_1d=… | fwd_5d=… | fwd_20d=… | fwd_60d=… | url=…
```

Keep `to_memory_text()` / `from_memory_text()` round-trip (parse the `[EVENT]` line), and keep tags/metadata (`ticker`, `sector`, `type`, `year`, `source`). Update tests. Use `null`/"not yet observable" for horizons that haven't elapsed; never fill values.

### A2. Broaden real catalyst coverage (layoffs, contracts, leadership)
8-K Item 2.05 alone misses most well-known layoffs (announced via memo/press release). Add, all from **real, linkable sources**:
1. **8-K Items 7.01 and 8.01 (and exhibit 99.1 press releases):** fetch the primary/exhibit document text and classify by keywords with word-boundary regexes: `layoff|workforce reduction|reduction in force|job cuts|restructuring plan` → `layoffs_restructuring`; `awarded|contract award|selected by|multi-year agreement|task order` → `contract_win`; `acquire|acquisition|merger` → `m_and_a`; `recall|investigation|subpoena|settlement|antitrust` → `regulatory_legal`; `guidance|outlook` raise/cut → `guidance_raise` / `guidance_cut`. Cache fetched documents in SQLite; respect SEC 10 req/s and the User-Agent.
2. **Item 5.02 refinement:** distinguish real management/board changes (departure, appointment, resignation, election of director/officer) from compensation-only amendments. Classify as `leadership_change`, `board_change`, or drop compensation-only filings.
3. **Curated file `data/known_events.csv`** (columns: `ticker,date,type,headline,source_url`) containing widely reported, verifiable events for S&P 100 names (e.g., Salesforce Jan 2023, Meta Nov 2022 and Mar 2023, Amazon Nov 2022/Jan 2023, Microsoft Jan 2023, Alphabet Jan 2023, Intel Aug 2024, Tesla Apr 2024, Nike/Disney/IBM/others where you are confident). **Every row needs a real news or filing URL; skip any event you cannot source.** The script computes all returns from price data, so only the label is human-curated. Mark these records `source=curated` and show a "Curated" chip in the UI. Add a CSV validator test (valid tickers, ISO dates, non-empty URLs, known types).
4. Add **USAspending.gov** contract awards (`https://api.usaspending.gov/api/v2/search/spending_by_award/`, no key) as `contract_win` events for defense/government-exposed tickers (LMT, RTX, GD, BA, PLTR, GE, HON, and others where awards exist): only awards above $100M, with the award ID URL.
5. De-duplicate events within 3 days per `(ticker, type)`, keeping the one with the best source.

Extend `--list-events` to show source and URL. Update dry-run to print counts by type across all 100 tickers, average record length, and total memories.

### A3. Small live run (STOP GATE 1)
1. Run the live backfill for `--tickers CRM META NVDA --checkpoint data/checkpoint_small.json`. (User has confirmed this run is authorized, and only this one.)
2. Run `verify_memory.py` with: "Salesforce layoffs 2023", "executive or board leadership change", "NVIDIA earnings beat", "defense contract award". Print recalled text, date, and score.
3. Write `data/small_run_report.json`: memories retained, recall precision on the 4 queries (did the expected event appear in top 5?), and total retained per Hindsight `alist_memories`.
4. **Gate:** if recall of "Salesforce layoffs 2023" does **not** return the 2023-01-04 event in the top 5, fix the content format/query construction and retry once. If it still fails, write the problem into `docs/DECISIONS.md`, continue with the remaining stages that don't need live memory, and **skip A4**.

### A4. Full S&P 100 backfill (guarded)
- Add flags `--max-memories N` (default 3500) and `--stop-on-error-rate 0.2`. Use `--max-events-per-ticker 10` for price-only events; mandatory catalyst events are always kept but total is hard-capped by `--max-memories` (drop lowest-priority price-only events first).
- Retain in batches of ≤25 with exponential backoff on 429/5xx; resumable via `data/checkpoint.json`; idempotent document IDs.
- Run it for the full verified S&P 100 (`in_sp100`; confirm exactly 100 tickers, GOOG and GOOGL both counted; fix the list if not).
- Write `data/backfill_report.json` (per ticker, per type, totals, skipped, errors). If the Hindsight API returns credit/quota errors, **stop cleanly**, keep the checkpoint, report how many tickers completed, and continue with later stages using what exists.
- After it finishes, re-run `verify_memory.py` and save results to `data/verify_report.json`.

---

## STAGE B: Pattern engine (the hero feature): news → history

Implement per BUILD_PLAN §3.4, hardened:
- `POST /api/patterns {symbol, headline, url?, date?}` and `GET /api/stock/{symbol}/patterns` (auto-runs on the latest news items).
- Steps: (1) classify headline with rules first, cheap Groq model (`llama-3.1-8b-instant`) only for ambiguous ones, cached by headline hash; extract magnitude (regexes such as "10% of (its )?(employees|workforce)", "$2B contract", "beat by 8%"); (2) recall from `quantmind-events` twice: same company and all-S&P-100 (plus same sector), with a natural-language query built from event type + magnitude + context; (3) parse the `[EVENT]` lines and **aggregate in Python**: n, median/mean day-0, median abnormal, hit-rate % positive at 1d/5d/20d/60d, best/worst, dispersion, split by same-company vs cross-company; (4) confidence label from n (`n<5` → "thin evidence"); (5) narrative ≤120 words from the precedent table only via the LLM, with a deterministic template fallback.
- Return `PatternResult` with `event_type, magnitude, n_precedents, same_company_precedents[], cross_company_precedents[]` (date, ticker, headline, source URL, returns, `source=filing|curated|usaspending|earnings`), `stats`, `narrative`, `memory_ids`, `memory_used`.
- Include a **"without memory" baseline** response mode (`memory=false`) that returns only a generic model statement with no precedents, for the before/after toggle.
- Tests: header parser, aggregator math (fixtures), magnitude regex, classifier rules, and an endpoint test with mocked recall.
- **Acceptance:** for at least 5 S&P 100 tickers and 3 event types, results contain ≥5 real, linked precedents (if the backfill ran); otherwise the response honestly says how many exist.

---

## STAGE C: Professional stock app (BUILD_PLAN Phase 2)

Redesign the frontend as a **Moneycontrol/Yahoo-Finance-grade** product. Split into readable files (`components/`, `pages/`, `lib/`, `hooks/`); use TanStack Query for data fetching/caching; keep TypeScript strict; pin dependency versions.

**Backend endpoints (all cached in SQLite with TTLs; Pydantic responses; per-panel graceful failure):**
`/api/market/overview` (indices `^GSPC ^IXIC ^DJI ^VIX`, S&P 100 heatmap data, top gainers/losers), `/api/stock/{symbol}/quote|history?range=|profile|financials?period=|news|filings|contracts|leadership|analysts|peers|report|patterns`.
- **filings/contracts/leadership** come from the EDGAR provider you already built: decode Item codes to plain English (1.01 Deals & contracts, 2.02 Earnings, 2.05 Restructuring/Layoffs, 5.02 Leadership/Board changes, 2.01 M&A, 1.05 Cyber, 8.01 Other), with filing date and SEC link. Contracts also include USAspending awards where available. Leadership = yfinance `companyOfficers` + recent 5.02 timeline + insider transactions.
- Handle crypto and ETFs (no fundamentals → hide those panels cleanly), tickers like `BRK-B`, delisted/invalid symbols (friendly 404 with search suggestions), market closed, and provider timeouts.

**Pages:**
- **Home `/`:** index tiles, S&P 100 **heatmap** (size = market cap, color = day change, click → stock), gainers/losers, and a **Memory growth** widget (total memories, S&P 100 coverage, latest learned insight).
- **Stock `/stock/:symbol`:** sticky header (name, avatar, price, day change, market cap, 52-week range bar, sector, market-status chip) and tabs: **Overview** (TradingView `lightweight-charts` with range buttons 1D/5D/1M/6M/YTD/1Y/5Y/Max + volume, **memory-event markers** that open a precedent drawer on click, key stats grid, profile), **News & Signals** (news cards with event-type + sentiment chips and a **"🧠 What happened before?"** button opening the pattern drawer from Stage B), **Financials** (quarterly/annual statements with YoY and bar charts), **Filings, Deals & Contracts**, **Leadership & Board**, **Analysts & Ownership**, **Peers**, **AI Memo** (the five-factor report, redesigned, With/Without Memory toggle), **Memory** (timeline of remembered events for this ticker, learned patterns, prediction track record).
- **Compare `/compare?a=&b=`:** normalized price chart and key stats side by side.
- **Design system:** dark default + light toggle; near-black slate, one emerald accent, red/green only for P&L; Inter for UI, JetBrains Mono (tabular numbers) for figures; 8-px spacing scale; 1-px borders; skeleton loaders; ▲▼ icons plus color; compact number formatting (1.2T, 340M); responsive to 375 px; accessible (focus rings, aria labels, contrast). Search palette gets `in_sp100` badge and live `memory_event_count` (from the backfill). Remove the old Jinja page from the primary flow (keep `/research` only as a legacy route or redirect it to the new stock page).
- **Acceptance:** `/stock/NVDA` renders header, chart, stats, news, financials, and filings with real data; each panel fails independently; `npm run typecheck` and `npm run build` pass; add a few Vitest tests (number formatters, search result rendering, pattern drawer).

---

## STAGE D: LLM reliability and report engine (BUILD_PLAN Phase 4)

Rewrite `llm.py`:
- **Fallback chain** (env-configurable, default): `openai/gpt-oss-120b` → `qwen/qwen3-32b` → `llama-3.3-70b-versatile` → `llama-3.1-8b-instant`. On 429 read `retry-after`/message, mark that model cooling down in-process, and **immediately move to the next model; never retry the same model after TPD exhaustion**. On JSON/tool-call errors retry once with a stricter prompt, then move on. Show the model used in the memo footer.
- **Token discipline:** `max_tokens` ≈ 2,000; compress prompts (top 5 news, top 5 precedents, ~20 key stats); daily token counter with a log warning at 80%; small model for classification/sentiment only.
- **Cache** reports by `(symbol, date, memory_flag)` in SQLite (TTL a few hours), `?refresh=true` to bypass.
- **Deterministic fallback** report (from stats, precedents, confidence audit) when all models fail; the UI shows "AI narrative temporarily unavailable" with a complete data-driven memo, never a red error box.
- Tests: mocked 429 → next model used; all models fail → deterministic report; cooldown logic.

---

## STAGE E: Self-improvement made visible (BUILD_PLAN Phase 5)

1. **Prediction log + resolver.** Every generated report/pattern result retains a prediction memory (bank `quantmind-predictions`): symbol, date, event type, expected 5d direction/range (from the aggregated precedents), confidence, precedent IDs, `memory_on`. `scripts/resolve_outcomes.py` + `POST /api/admin/resolve` (protected by `ADMIN_TOKEN`) + a startup background task (every 6 h) resolve matured predictions with actual returns, retain an **outcome memory** (hit/miss, error size, one-line lesson), and after every 5 resolved outcomes per event type call Hindsight `reflect` ("What has QuantMind gotten wrong about {event_type} reactions and what should it weigh differently?"), retaining the result as a `META-INSIGHT` in `quantmind-insights`. Recalls for that event type must include the latest insight, and the UI shows it tagged "learned on {date}".
2. **Walk-forward backtest** (rewrite `scripts/backtest_memory.py`): iterate real backfilled events by date; for event *t* predict the 5-day direction using **only records dated before *t*** (same-type cross-company aggregation) vs a memory-off baseline (event-type-agnostic prior: sign of the overall median 5d return). Output `data/backtest_results.json`: rolling hit rate vs number of memories available, MAE, hit rate by event type, n, and confidence intervals. **Report honestly**, even if the gain is small, and label it a directional-accuracy backtest, not a trading claim. Include a unit test for the no-lookahead rule.
3. **`/memory` "QuantMind Brain" page:** counters (total memories, S&P 100 coverage n/100, events by type, predictions made/resolved/hit-rate), a **learning-curve chart** (x = memories accumulated, y = rolling hit rate, two lines: with vs without memory), a **live learning feed** (recent retained events, resolved outcomes, new insights), a **memory explorer** (filter by ticker/type/date; view the raw record + source link), and a **before/after panel** (generic answer vs memory-backed answer for the same headline).
4. **"Simulate a day" button** (demo, clearly labeled): replays the next held-out historical event through the live pipeline (predict → later resolve → counters update → occasional insight). Real historical events only. Support `HOLDOUT_FROM=YYYY-MM-DD` so the backfill can leave the most recent events unretained for this demo (document this clearly in the README; default off).
5. Endpoints: `/api/memory/stats`, `/api/memory/events`, `/api/memory/insights`, `/api/memory/learning-curve`.

---

## STAGE F: Polish, docs, CI, demo readiness (BUILD_PLAN Phase 6)

- **README rewrite:** hero screenshot/GIF placeholders, problem, architecture diagram (Mermaid), **"How Hindsight memory is used"** (banks, retain/recall/reflect, tags, document IDs, learning loop, prediction/outcome cycle; required for the hackathon submission), setup steps that work on Windows and macOS/Linux, env-var table, data sources + licenses/terms (SEC EDGAR, USAspending, yfinance, CoinGecko, Nasdaq Trader), backtest methodology, and an honest limitations section.
- **`docs/DEMO.md`**: a 60–90 s script: (1) search "salesforce" → stock page with real chart and filing feed; (2) open a layoff-type item → "What happened before?" → cross-company precedents with returns; (3) toggle Without Memory → generic; back → specific + sourced; (4) `/memory` → 100/100 coverage, learning curve, fresh insight; (5) "Simulate a day" → counters tick, "it gets smarter every day".
- **Health & ops:** `/api/health` reports Hindsight, Groq, SEC, universe size, memory counts, and cache status; rate-limit expensive endpoints; timeouts on every provider call; structured logging.
- **CI:** GitHub Actions running Ruff, pytest, `tsc --noEmit`, `vite build`.
- **Deploy:** ensure the Docker image contains `data/` (universe, checkpoint-independent reports, `known_events.csv`) and `web-dist`; verify `render.yaml` env vars; add a `docs/DEPLOY.md` with Render steps and the required env variables (never values).
- Add `docs/CONTENT_CHECKLIST.md` listing the hackathon submission items (repo, demo video, live demo, article, social post) with links to the README and DEMO sections that support each.

---

## Final report (print at the very end and save as `docs/FINAL_REPORT.md`)

1. Per stage: done / partially done / skipped, and why.
2. Numbers: universe size, S&P 100 count (must be 100), memories retained (per Hindsight), events by type, small-run recall results, backtest hit rate (memory vs no-memory, n, CI), tests passing, lint/typecheck/build status.
3. Real Hindsight cost observed (if measurable) and any quota errors hit.
4. Known limitations and what a human must verify manually (Render deploy, keys, visual QA on 375 px and desktop).
5. Exact commands to run the app locally on Windows PowerShell and to re-run the backfill/backtest.

**Begin with Stage A now.**