# QUANTMIND — DATA-FIRST MASTER PROMPT FOR AN AUTONOMOUS EQUITY RESEARCH AND HISTORICAL INTELLIGENCE ENGINE

## Your mission

You are the principal engineer, financial data researcher, quantitative analyst and AI systems architect responsible for transforming my existing QuantMind codebase into a dynamically maintained equity research intelligence platform powered by Hindsight.

**The primary objective is to build a large, continuously updated, historically grounded financial knowledge system—not merely a stock dashboard or chatbot.**

The system must dynamically discover its company universe, collect historical and current financial data, research company events, construct a persistent dataset, organize relevant evidence into Hindsight memory, analyze stocks using historical precedents and evaluate the accuracy of its previous conclusions.

Every major capability must be implemented in code. Do not manually hardcode the Fortune 500 companies, stock-specific analysis logic, historical outcomes, news summaries or research conclusions.

Inspect my existing repository first. Preserve useful code, identify missing functionality and implement the required changes in the existing project.

---

# 1. DATASET SCALE: DEFINE THE TARGET BEFORE WRITING FEATURES

Build a dataset pipeline with explicit coverage targets, measurable completeness and automatic expansion.

## 1.1 Company universe

Discover and maintain the complete Fortune 500 company list for each relevant ranking year.

Target:

- 500 company records per annual Fortune 500 universe.
- Historical Fortune 500 membership by year, where reliable data is available.
- Company descriptions, industry, sector, headquarters and business segments.
- Official website and investor-relations page.
- Public/private ownership status.
- Verified stock exchange, ticker, security identifiers and listing status.
- Historical ticker changes, mergers, delistings and predecessor relationships.

Do not assume all 500 companies are publicly traded.

For each company, determine whether it has a directly investable public security. If it is privately held or its parent company is publicly traded under a different name, record that distinction.

Maintain a coverage ledger showing:

- Companies discovered.
- Companies successfully mapped.
- Public securities verified.
- Historical market data available.
- Fundamental data available.
- News and filing coverage available.
- Companies with unresolved identities or inaccessible sources.

The ingestion pipeline must discover and process companies using database records and configuration-driven jobs. Adding a company must not require writing new company-specific Python code.

## 1.2 Historical market data

For every verified public security, collect:

**Required baseline:** At least the most recent two years of available daily trading data.

**Required historical expansion:** All reliably obtainable daily price history from the security's first available listing date through the latest available observation.

Collect, where available:

- Date and timestamp.
- Open, high, low and close.
- Adjusted close or equivalent adjustment data.
- Trading volume.
- Corporate actions.
- Dividends and splits.
- Exchange and currency.
- Provider and ingestion timestamp.

Use an explicit distinction between price returns and total returns.

Do not fabricate observations for missing dates, treat non-trading days as missing data or silently substitute unadjusted prices for adjusted prices.

### Dataset sizing targets

Use the following as planning estimates, not claims about data already collected.

| Dataset | Initial target |
|---|---|
| Company universe | 500 companies per ranking year |
| Two-year daily prices | Approximately 250,000 security-day records for 500 continuously traded securities |
| Extended historical prices | Potentially several million records, depending on listing histories |
| Quarterly fundamentals | Up to 40 quarters per security for a ten-year historical window |
| Annual fundamentals | Up to 10 fiscal years per security |
| Material news and event records | Initial goal of at least 50 relevant records per public company over two years, where sources support that coverage |
| Filings | All available relevant annual, quarterly and material-event filings for the selected historical window |
| Historical research | Persistent event, thesis, analogue and forecast-outcome records linked to their source data |

Two years of US trading typically provide approximately 500 trading sessions. The market-data estimate therefore excludes private companies, non-US exchange calendars, delistings and incomplete histories.

Do not stop collecting news after an arbitrary number of articles. The news target is a minimum coverage benchmark for evaluation, not a hard ingestion cap. Deduplicate syndicated copies and distinguish material events from repetitive commentary.

Report actual record counts, storage size, missingness, source coverage and collection dates after each ingestion run.

## 1.3 Historical financial statements

Where available, collect at least ten years of annual financial data and forty quarters of quarterly data.

Retrieve the underlying facts required to calculate:

- Revenue.
- Cost of revenue.
- Gross profit.
- Operating income.
- Net income.
- Diluted earnings per share.
- Cash and equivalents.
- Total assets and liabilities.
- Total debt.
- Operating cash flow.
- Capital expenditure.
- Free cash flow.
- Share count and dilution.
- Segment revenue and operating performance.
- Guidance and subsequent revisions, where disclosed.

Retain filing identifiers, reporting periods, units, currencies, source URLs and public availability timestamps.

Support restatements and revisions without overwriting the historical version that was available to investors at an earlier date.

For US companies, use SEC EDGAR and XBRL data where suitable. Research and select additional providers for market prices, international filings and financial fundamentals based on coverage, reliability, licensing, cost and API limits.

Never assume every provider supplies every required field.

## 1.4 News, filings and event dataset

Research each company using a structured collection pipeline.

Cover the previous two years in detail, while preserving older events where available and relevant.

Collect and classify:

- Earnings releases.
- Earnings calls and transcripts, where licensed.
- Guidance changes.
- Revenue and earnings surprises.
- Product announcements.
- Acquisitions and divestitures.
- Regulatory decisions and investigations.
- Litigation.
- Management changes.
- Layoffs and restructuring.
- Debt issuance and refinancing.
- Capital allocation and share repurchases.
- Dividends.
- Major customer or supplier developments.
- Material competitive threats.
- Sector-level developments.
- Relevant macroeconomic events.

For each news or event record, store the original headline, source, URL, publication timestamp, company mapping, event category, extracted facts, relevant financial metrics and source text or permitted document reference.

Separate the event itself from the media articles reporting it. Ten articles discussing one earnings release should not automatically become ten independent historical events.

Use source-backed extraction and deduplication. Preserve conflicting reports and flag unresolved discrepancies.

---

# 2. DYNAMIC CODE GENERATION AND DATA PIPELINE

## 2.1 No manually assembled datasets

Implement the complete process programmatically.

The code must be capable of:

1. Discovering the universe.
2. Resolving companies and securities.
3. Creating ingestion jobs.
4. Fetching records through provider APIs.
5. Handling pagination and rate limits.
6. Validating and normalizing records.
7. Storing raw and normalized data.
8. Detecting missing historical intervals.
9. Resuming failed jobs.
10. Updating existing records safely.
11. Creating research events.
12. Synchronizing selected knowledge with Hindsight.
13. Updating coverage statistics.
14. Scheduling future updates.

Implement generic adapters and reusable ingestion workers.

The same pipeline must work for Apple, Microsoft, NVIDIA, JPMorgan Chase or a newly discovered public company without changing the implementation logic.

Company-specific differences belong in verified metadata, provider mappings and configuration—not scattered conditional statements.

## 2.2 Incremental ingestion

Implement two distinct operating modes.

**Initial backfill**

Fetch all available historical records for the configured universe and date range. Process the workload in bounded batches, persist checkpoints and resume from the last successful stage.

**Incremental update**

Fetch only new or changed records after the latest successfully ingested observation, while periodically reconciling overlapping historical windows to identify corrections, late-arriving records and corporate actions.

Support:

- Idempotent upserts.
- Unique record constraints.
- Exponential backoff with bounded retries.
- Provider-specific rate limits.
- Pagination.
- Concurrency limits.
- Per-company checkpoints.
- Failed-job queues or equivalent recovery mechanisms.
- Backfill progress reporting.
- Provider quota monitoring.
- Data freshness monitoring.

A restart must not cause the system to duplicate the dataset or restart every completed job unnecessarily.

## 2.3 Data-quality gates

Before data becomes eligible for analysis, validate:

- Company and security identity.
- Timestamp and reporting-period validity.
- Duplicate records.
- Price and volume anomalies.
- Missing observations.
- Currency and unit consistency.
- Corporate-action adjustments.
- Fundamental statement consistency.
- News publication time.
- Source availability.
- Historical point-in-time eligibility.

Do not automatically delete unusual observations simply because they look like outliers. Determine whether they represent genuine market events, data errors or corporate actions.

Quarantine suspicious records for review, preserve their provenance and report exclusions.

## 2.4 Research orchestration must be data-driven

Create a scheduler that discovers outstanding work from the database.

Examples:

- A company has no two-year price history: schedule a historical backfill.
- A company's price data is stale: schedule an incremental update.
- A quarterly filing is published: ingest the filing and update relevant financial facts.
- A material event is detected: create a source-backed event record.
- A research memory is missing an outcome: schedule resolution when its horizon matures.
- A security mapping changes: reconcile the affected historical records.

Use a job queue or equivalent background-processing architecture suited to the existing project.

Do not execute a full-universe backfill synchronously inside a web request.

---

# 3. RESEARCH DEPTH: INVESTIGATE EACH COMPANY, NOT JUST ITS TICKER

Build a repeatable company research dossier.

For each company, the system should progressively develop a structured understanding of its business, financial performance, market behavior and historical catalysts.

## 3.1 Business research

Research:

- Business model.
- Products and services.
- Revenue segments.
- Geographic exposure.
- Customer and supplier concentration, where disclosed.
- Competitive positioning.
- Industry structure.
- Management strategy.
- Capital allocation.
- Key operational risks.

Use official company filings and investor-relations materials as primary sources. Use reputable independent sources for corroboration and context.

## 3.2 Financial research

Calculate multi-year trends in revenue, margins, earnings, cash flow, leverage, liquidity, capital expenditure, dilution and valuation.

Compare the latest available results against:

- Previous quarters.
- Prior-year periods.
- Longer-term trends.
- Management guidance.
- Relevant competitors.
- Industry benchmarks.

Show the underlying period, formula, source and data freshness.

Do not compare different fiscal periods as if they were equivalent.

## 3.3 Historical catalyst research

Build a chronological record of material corporate events and their observed market consequences.

For each event, investigate:

- What happened.
- When it happened.
- When it became public.
- What investors could reasonably know beforehand.
- What expectations were documented.
- What price and volume behavior followed.
- How the company and sector performed relative to a benchmark.
- Whether similar situations occurred previously.
- Which factors might explain differences in outcomes.

Use historical price windows around events and compare them with the relevant benchmark.

Do not claim causality without an appropriate research design.

## 3.4 Current research

When a user searches a stock, dynamically retrieve the latest available eligible data, relevant current news, recent filings, historical context and material risks.

The system must report the actual data cutoff and source coverage.

If a provider is unavailable or the latest data cannot be verified, display that limitation rather than presenting stale information as live.

---

# 4. HINDSIGHT: TURN THE DATASET INTO PERSISTENT FINANCIAL INTELLIGENCE

## 4.1 Separate the financial database from Hindsight

Use the financial database as the authoritative store for numerical records and structured historical facts.

Use Hindsight as the persistent memory and reflection layer for source-linked events, research theses, historical analogues, analytical lessons and previous conclusions.

Do not dump every raw price row, financial statement cell or duplicate news article into Hindsight.

Store compact, useful memories with references to the authoritative underlying records.

Every memory must have a stable identifier and, where applicable:

- Company and security identifiers.
- Event category.
- Source references.
- Public availability timestamp.
- Historical context.
- Original research timestamp.
- Relevant analytical claims.
- Outcome horizon.
- Validation status.

Inspect the installed Hindsight version and implement against its actual supported API.

## 4.2 Build memories from historical evidence

Create reusable processes that convert the collected dataset into structured research memories.

Examples include:

- An earnings miss followed by margin deterioration.
- A guidance increase followed by a period of accelerating revenue.
- A major acquisition followed by changes in leverage and free cash flow.
- A regulatory decision followed by a measurable change in price volatility.
- A valuation expansion during a period of improving fundamentals.
- A high-growth company whose performance deteriorated despite strong headline revenue growth.

These are examples of categories to investigate, not conclusions to hardcode.

The system must discover candidate cases from the actual dataset, calculate their outcomes and retain their source evidence.

## 4.3 Historical recall when a stock is searched

When a user searches a company, dynamically:

1. Resolve its identity.
2. Retrieve its current research data.
3. Identify the current financial and market conditions.
4. Retrieve relevant company-specific memories.
5. Retrieve relevant sector and cross-company analogues.
6. Exclude memories containing information unavailable at the relevant historical cutoff when performing retrospective analysis.
7. Compare financial and event characteristics.
8. Calculate actual outcomes for comparable historical cases.
9. Identify counterexamples and material differences.
10. Present evidence-backed conclusions with uncertainty.

Hindsight recall is not itself proof of a financial pattern. All material numerical conclusions must be calculated from the structured dataset.

## 4.4 Build memory from outcomes

When a previous research thesis or forecast reaches its evaluation horizon, calculate the actual outcome and associate it with the original record.

Preserve:

- Original hypothesis.
- Original evidence.
- Forecast timestamp.
- Evaluation horizon.
- Outcome.
- Error or deviation.
- Relevant market context.
- Final evaluation status.

Do not rewrite old memories to make them appear correct.

Allow Hindsight reflection to identify recurring analytical errors and possible improvements, but label untested lessons as hypotheses.

---

# 5. HISTORICAL DATASET EXPANSION AND ANALYTICS

## 5.1 Build a reusable analytical feature store

Calculate features from stored data rather than recalculating the entire dataset every time a stock is searched.

Include:

- Daily and rolling returns.
- Volatility.
- Drawdown.
- Volume anomalies.
- Relative performance.
- Beta and correlation.
- Financial growth and profitability.
- Leverage and liquidity.
- Valuation ratios.
- Earnings surprise.
- Guidance revisions.
- Event-window returns.
- Relevant sector and macroeconomic context.

Store the feature definitions, input references, calculation timestamps and methodology versions.

Recompute only affected features when new records arrive or historical inputs are corrected.

## 5.2 Historical analogue dataset

Create a searchable dataset of historical situations across the company universe.

For every resolved case, preserve its event context, company characteristics, market regime, benchmark performance and subsequent returns over defined trading-day horizons.

Where sufficient data exists, calculate outcomes at horizons such as:

- 1 trading day.
- 5 trading days.
- 20 trading days.
- 60 trading days.
- 120 trading days.
- 252 trading days.

Use only horizons for which the outcome is available.

The system must calculate distributions, downside behavior, dispersion and sample sizes—not merely averages.

Exclude overlapping or duplicate events where appropriate and document the selection rules.

## 5.3 Forecast and research evaluation dataset

Persist every testable forecast before its outcome becomes available.

Create an evaluation dataset that supports:

- Forecast accuracy.
- Directional accuracy.
- Calibration when probabilistic forecasts are justified.
- Performance by horizon.
- Performance by event category.
- Performance by sector.
- Baseline comparisons.
- Memory-enabled versus memory-disabled research.

Use walk-forward evaluation with point-in-time data.

Prevent look-ahead bias, survivorship bias and data leakage through future filings, later memory reflections or revised historical information.

Never declare a model successful because it performs well on the same data used to tune it.

---

# 6. DYNAMIC STOCK RESEARCH INTERFACE

Build the interface around the dataset and research engine.

When the user enters a company name or ticker, the application must dynamically query the backend and return the available research.

## 6.1 Price chart

Display the full available historical price series from the first verified listing date through the latest available observation.

Include:

- Interactive zoom and date selection.
- Daily, weekly and monthly views where supported.
- Volume.
- Adjusted-price handling.
- Benchmark comparison.
- Corporate actions.
- Earnings and material-event markers.
- Historical news overlays.

The two-year view must be available immediately, but it must not replace the full historical view.

Never invent prices to fill gaps. Clearly indicate incomplete historical coverage.

## 6.2 Company research

Display financial trends, company fundamentals, relevant news, risk metrics, historical analogues and source-backed research.

Include a detailed research report with:

- Business overview.
- Historical financial performance.
- Recent catalysts.
- Valuation context.
- Historical comparisons.
- Bull, base and bear scenarios.
- Material risks.
- Counterarguments.
- Assumptions and invalidation conditions.

All numerical scenario outputs must be generated by deterministic calculations from explicit inputs.

## 6.3 Historical memory

Show which memories influenced the research, why they were retrieved, which historical cases they refer to and how those cases performed.

Allow users to inspect original evidence and distinguish validated findings from exploratory hypotheses.

## 6.4 Forecast tracking

Display previous forecasts, their original timestamps, evaluation horizons, resolved outcomes and historical performance.

Never replace an old prediction with a newer one.

---

# 7. PROVIDER RESEARCH AND DATA ACQUISITION STRATEGY

Before selecting or adding providers, conduct a focused investigation of current documentation, historical coverage, pricing, API quotas, licensing and redistribution restrictions.

Compare suitable sources for:

- Market prices and corporate actions.
- Company fundamentals.
- Regulatory filings.
- Historical news.
- Earnings transcripts.
- Economic indicators.
- Benchmark and sector data.

Evaluate whether the source supports the full historical range, adjusted prices, pagination, corrections and point-in-time research.

Create a provider capability matrix and select a primary source and suitable fallback for each data category where practical.

Do not assume a free API can support a 500-company historical backfill.

Estimate the number of API requests, expected ingestion time, storage needs and recurring costs before running the complete backfill.

Implement provider adapters so that switching providers does not require rewriting the analytics engine.

Respect API terms, copyright, access controls and licensing requirements. Do not scrape restricted sources or store full copyrighted documents without permission.

If credentials or paid access are unavailable, implement the adapter and a clearly reported blocked status. Do not silently substitute fake data.

---

# 8. EXACT IMPLEMENTATION REQUIREMENTS

Work directly in the existing repository.

First identify the current codebase, dependencies, working integrations, existing database and incomplete functionality.

Then implement:

1. A versioned Fortune 500 universe loader.
2. Company and security identity resolution.
3. Historical price ingestion.
4. Fundamentals and filing ingestion.
5. News and event ingestion.
6. A canonical financial database.
7. Incremental update and backfill jobs.
8. Data-quality and coverage reporting.
9. Hindsight memory creation and retrieval.
10. Historical analogue calculations.
11. Quantitative research services.
12. A research orchestration workflow.
13. Prediction and outcome persistence.
14. A functioning stock research interface.
15. Automated tests and operational documentation.

Use configuration, database-driven discovery, reusable functions and typed schemas. Do not create a separate hardcoded analysis module for each company.

Do not implement the complete platform as one enormous Python file or one unstructured agent prompt.

Do not rewrite working components without evidence that they need replacement.

Do not create placeholder charts, fictional company data, simulated research results or hardcoded claims of coverage in the production workflow.

## Required commands

Provide executable commands or equivalent application entry points for:

- Initial universe discovery.
- Full historical backfill.
- Incremental data updates.
- News and filing ingestion.
- Data-quality checks.
- Hindsight memory synchronization.
- Historical feature generation.
- Analogue and event-study generation.
- Forecast resolution.
- Research evaluation.
- Coverage and ingestion reporting.
- Application startup.
- Test execution.

The commands must use the same underlying services as the application rather than maintaining separate implementations.

---

# 9. ACCEPTANCE TESTS

The project is not complete until the following are demonstrated.

**Test A — Universe:** The system discovers and records the annual Fortune 500 universe, identifies public securities and reports unresolved company mappings.

**Test B — Historical data:** A selected public company has its available price history ingested, validated and plotted from its first available observation through the latest available observation.

**Test C — Fundamentals:** Available financial statements are stored with reporting periods, units, source references and publication timestamps.

**Test D — Research:** A company search dynamically retrieves relevant financial evidence, recent news, historical events and Hindsight memories.

**Test E — Analogue analysis:** The system identifies historical cases, calculates actual subsequent outcomes and shows similarities, differences and sample sizes.

**Test F — Incremental updates:** A subsequent run retrieves new or corrected records without duplicating existing records or rebuilding the entire dataset unnecessarily.

**Test G — Temporal integrity:** A historical research run cannot use information published after its cutoff.

**Test H — Outcome evaluation:** Previously recorded forecasts are resolved only after their evaluation horizons mature, and the results are stored without changing the original predictions.

**Test I — Scale reporting:** The system reports actual company coverage, market-record counts, news and filing counts, missing data, storage requirements and provider limitations.

**Test J — Memory value:** A reproducible experiment compares otherwise equivalent memory-enabled and memory-disabled research workflows.

---

# 10. REQUIRED FINAL DELIVERABLES

At completion, provide:

- Updated source code.
- Database schema and migrations.
- Provider integrations.
- Hindsight integration.
- Frontend implementation.
- Backfill and update scripts.
- Environment configuration template.
- Automated tests.
- Setup and execution documentation.
- Actual ingestion results.
- Actual dataset counts and coverage.
- Identified missing data and external dependencies.
- Measured runtime, storage requirements and provider costs where available.
- Historical evaluation results, if the experiments have actually been run.

Clearly distinguish code that is implemented from code that has been tested against real external services.

Do not claim that 500 companies have been fully researched merely because the ingestion pipeline supports 500 companies.

Do not claim the full dataset has been collected unless the ingestion results demonstrate it.

Do not claim Hindsight improves forecasts unless the evaluation demonstrates it.

## Final instruction

Start by inspecting the existing repository. Determine exactly what is already implemented, what is missing and what can be reused.

Then build the dynamic data-acquisition and research pipeline first. Make it reliable for one company, validate it across a representative sample, and scale it to the full available universe using resumable jobs and explicit coverage targets.

The end goal is a financial research system that accumulates years of structured market history, company fundamentals, material events, historical analogues and evaluated research conclusions.

When a user searches any supported stock, the system should combine its current data with the relevant historical evidence and persistent Hindsight memory to produce a source-backed, quantitatively grounded research analysis.

**Prioritize dataset completeness, research depth, dynamic ingestion, historical correctness and measurable analytical value over superficial UI features or unnecessary agent complexity.**