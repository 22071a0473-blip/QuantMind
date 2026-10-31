# QUANTMIND — PRINCIPAL ENGINEERING MASTER SPECIFICATION
## Hindsight-Native Quantitative Equity Intelligence, Historical Market Memory & Institutional Research Platform

**Project type:** Production-oriented financial research software  
**Architecture:** Modular, data-centric, agent-orchestrated research system  
**Primary differentiator:** Persistent historical memory with point-in-time evidence, quantitative outcome resolution, and measurable research improvement  
**Initial universe:** All Fortune 500 companies, with support for additional publicly traded securities  
**Development approach:** Evolve the existing repository; implement, test, benchmark and document every major subsystem.

---

# PART I — MISSION AND ENGINEERING MANDATE

## 1. Your role

Operate as a principal software architect and quantitative research engineering lead with expertise in:

- Institutional equity research systems.
- Quantitative finance and financial econometrics.
- Historical event studies and point-in-time data.
- AI agent orchestration and persistent memory.
- Financial data engineering and temporal databases.
- Python, FastAPI, React, TypeScript and production infrastructure.
- Model evaluation, backtesting, observability and security.

You are not being asked to create a conventional stock dashboard, a generic RAG chatbot, or a predictive model that outputs an arbitrary target price.

You are responsible for engineering QuantMind into a coherent financial intelligence system that can accumulate historical evidence, conduct reproducible research, evaluate its own prior conclusions and improve its research methodology based on measured results.

You have access to an existing QuantMind codebase. Treat that repository as the starting point and source of truth.

**Your responsibility is implementation, not merely specification.** Inspect the repository, determine what already works, design the changes, implement them, run the available checks and report the actual state of the system.

Do not assume that a feature is implemented because a filename exists. Trace its execution path and verify its behavior.

## 2. Product thesis

The core hypothesis behind QuantMind is:

> Financial research becomes more useful when current market evidence is analyzed alongside a persistent, structured history of what happened in comparable situations, what was believed at the time, which conclusions proved wrong, and what the realized outcomes reveal.

The system must distinguish four concepts:

1. **Historical facts:** What was reported, when it became public, and what subsequently happened.
2. **Analytical interpretations:** What those facts may imply under stated assumptions.
3. **Forecasts:** What the system expected to happen at a specified future horizon.
4. **Resolved outcomes:** What actually happened after the forecast was recorded.

These concepts must never be conflated.

Hindsight is the persistent memory and reflection layer. The financial database is the authoritative source for structured market observations and numerical outcomes. Deterministic Python analytics are responsible for calculations. Language models synthesize evidence, formulate hypotheses and challenge conclusions.

No single LLM should be responsible for inventing data, calculating all financial metrics, evaluating its own predictions and declaring itself successful.

## 3. Definition of success

QuantMind must eventually be able to answer a question such as:

"Analyze this company's current position. Find comparable historical situations across the company and its peers, reconstruct what investors knew at those times, calculate what happened over the following trading periods, identify successful and failed historical analogues, compare the present situation against them, and explain which conclusions are supported by evidence and which remain uncertain."

The system must then preserve its analysis, monitor the specified outcome horizons, resolve the results and make them available to future research.

The product is successful only when these capabilities operate through a tested, persistent and reproducible workflow.

Do not claim institutional-grade accuracy, superior returns or predictive advantage without empirical evidence.

---

# PART II — REPOSITORY DISCOVERY AND ARCHITECTURAL GOVERNANCE

## 4. Establish the actual system before changing it

Start by examining the complete existing repository.

Identify:

- Python backend framework and entry points.
- Existing API routers and response schemas.
- Frontend routes, components, state management and charting library.
- Database, ORM, migration system and persistence boundaries.
- Hindsight SDK version, configuration and existing memory operations.
- Existing market-data and news integrations.
- Existing event-processing and analytics modules.
- Agent graph or orchestration framework.
- Existing forecasting models and evaluation logic.
- Scripts, scheduled jobs, tests and deployment configuration.
- Environment variables and external service dependencies.

Build an architecture map that identifies the actual call graph for one complete stock search, from user input to rendered result.

Trace how current data enters the system, how it is transformed, where it is stored, how Hindsight is invoked, and how the frontend receives the output.

Run baseline tests and builds before modifying anything.

Create an implementation plan based on verified findings. Preserve useful functionality and explicitly identify code that must be replaced because it is incorrect, redundant, untestable or architecturally unsuitable.

Do not perform a wholesale rewrite simply because a different framework seems attractive.

## 5. Architecture decision records

For every significant architectural decision, create a short architecture decision record containing:

- Problem and context.
- Considered alternatives.
- Chosen approach.
- Trade-offs.
- Operational consequences.
- Reversal criteria.

Prioritize decisions concerning temporal data, Hindsight memory boundaries, financial data providers, persistence, agent orchestration, backtesting and forecast evaluation.

Use the existing stack where it remains appropriate. Introduce new dependencies only when a clear capability or reliability gap justifies them.

Do not invent APIs for installed libraries. Inspect the installed versions and verify the actual interfaces.

---

# PART III — TARGET SYSTEM ARCHITECTURE

## 6. Build a modular research platform

Organize the application around the following logical boundaries. Adapt the existing repository's physical structure rather than mechanically duplicating these directory names.

### A. Application and presentation layer

Responsible for:

- Stock and company search.
- Interactive charts and financial tables.
- Research workspaces.
- Historical event timelines.
- Research memo presentation.
- Prediction history and evaluation results.
- Job progress, source status and data freshness.

The frontend must never independently calculate authoritative financial metrics or fabricate missing data.

### B. API and application services

Responsible for:

- Authentication and authorization if the application supports multiple users.
- Request validation.
- Research-job creation and status.
- Company and security resolution.
- Report retrieval.
- Data freshness and provider health.
- Consistent error handling.
- Pagination and caching.

### C. Research orchestration

Responsible for coordinating the research workflow, managing task dependencies, enforcing evidence requirements, tracking partial failures and assembling a validated final report.

The orchestration layer must not contain duplicated financial calculations or become an unstructured collection of LLM calls.

### D. Quantitative analytics

Responsible for deterministic calculations, financial ratios, returns, risk metrics, event studies, comparable-company analysis, forecast evaluation and backtesting.

Each calculation must have a defined contract, units, period, input requirements and tests.

### E. Data acquisition and normalization

Responsible for provider adapters, ingestion, timestamp normalization, deduplication, security mapping, corporate actions, data-quality checks, caching and incremental updates.

### F. Persistent research memory

Responsible for Hindsight integration, historical event retention, semantic recall, reflection, evidence-linked research memories and validated analytical lessons.

### G. Evaluation and feedback

Responsible for prediction resolution, model evaluation, memory ablation, calibration, backtest reproducibility and performance reporting.

### H. Infrastructure and observability

Responsible for database migrations, scheduled jobs, retries, logs, metrics, health checks, secrets and deployment configuration.

Maintain clear interfaces between these boundaries. A provider change must not require rewriting the research UI. A new analysis agent must not require duplicating the data pipeline.

---

# PART IV — FORTUNE 500 AND SECURITY COVERAGE

## 7. Company and security identity

Create a versioned universe based on an authoritative Fortune 500 list, with the ranking year and source preserved.

Do not treat the Fortune 500 list as a ticker list. It represents companies, some of which may have multiple securities, private ownership, subsidiaries, predecessor entities or no directly tradable shares.

Build an explicit company-to-security mapping.

The canonical model must distinguish:

- Company.
- Tradable security.
- Exchange and listing.
- Historical ticker symbol.
- Legal entity and relevant predecessor.
- Sector and industry.
- Listing and delisting dates.
- SEC CIK or equivalent identifiers where applicable.
- Provider-specific identifiers.
- Mapping provenance and verification status.

Handle ticker changes, multiple share classes, mergers, delistings and corporate restructurings.

Never infer a security's historical identity from its current ticker alone.

Build company search using exact identifiers, aliases and fuzzy matching, with an ambiguity-resolution workflow when several companies match.

Create a coverage report that measures how much of the target universe is actually researchable.

The report must distinguish mapped companies, tradable securities, partial histories, inaccessible data and unresolved mappings. Do not claim full Fortune 500 coverage until it has been measured.

---

# PART V — TEMPORAL FINANCIAL DATA FOUNDATION

## 8. Make time correctness a first-class requirement

Financial data is not simply a table of values indexed by date. Different facts become knowable at different times.

Implement explicit temporal semantics throughout the system.

Where applicable, preserve:

- Event occurrence time.
- Public disclosure time.
- Provider publication time.
- Original observation period.
- Filing acceptance or publication time.
- Data ingestion time.
- Data correction or restatement time.
- Prediction cutoff time.
- Outcome observation time.

Do not substitute one timestamp for another.

For historical research at time \(t\), the eligible information set must be restricted to facts demonstrably available by \(t\).

Define a shared point-in-time eligibility policy and enforce it in data retrieval, memory retrieval, research generation and backtesting.

If a source cannot establish when information became available, mark the temporal uncertainty and exclude it from strict historical simulations where necessary.

## 9. Structured data storage

Inspect the existing database before choosing a new persistence layer.

Use a relational database for canonical entities, financial statements, source metadata, research records, predictions and outcomes. Use PostgreSQL for a multi-user production deployment when appropriate, while retaining a practical local-development configuration.

Store large time series and normalized financial facts in structured, queryable storage.

At minimum, model:

- Companies and securities.
- Security identity history.
- OHLCV market bars.
- Corporate actions.
- Financial statements and facts.
- News, filings and corporate events.
- Data-source records.
- Research jobs and reports.
- Retrieved-memory references.
- Predictions and outcomes.
- Backtest runs and evaluation metrics.
- Ingestion jobs and data-quality issues.

Use stable primary keys, unique constraints, foreign keys, appropriate indexes and explicit units.

Use migrations rather than undocumented manual schema changes.

Keep raw provider responses or durable source snapshots where licensing and storage policies permit. Preserve normalized data separately so transformations can be audited and reproduced.

## 10. Provider abstraction and provenance

Implement provider adapters for market prices, fundamentals, filings, news and corporate events.

Reuse reliable existing integrations.

Potential sources include SEC EDGAR and XBRL for US filings, a suitable market-data provider, and a licensed news provider. Existing yfinance support may be retained for prototyping, subject to its terms and data limitations.

For every material data record, preserve source identity and provenance.

For every ingestion run, record:

- Provider and adapter version.
- Requested range and security.
- Retrieval timestamp.
- Number of records received, inserted, updated and rejected.
- Coverage gaps.
- Retry count and terminal errors.
- Validation results.

Implement idempotent ingestion, bounded retries, rate limiting, caching, resumable backfills and explicit provider-failure states.

A failed data provider must not silently produce a valid-looking but incomplete report.

---

# PART VI — THE HINDSIGHT INTELLIGENCE SYSTEM

## 11. Hindsight is not a document dump

This is the most important architectural requirement.

Do not simply store generated research reports in Hindsight and retrieve the nearest matching paragraph later.

Design memory around durable historical evidence, context, analytical claims and resolved outcomes.

First inspect the actual Hindsight integration and the installed SDK documentation. Verify supported retention, recall, reflection, metadata and isolation capabilities. Use the actual supported interfaces.

Keep Hindsight behind a dedicated adapter so that memory behavior can be tested independently of the rest of the application.

### Memory domain 1: Historical events

Store source-backed events such as earnings surprises, guidance changes, regulatory decisions, acquisitions, management changes, major product announcements, capital raises and sector shocks.

Each memory should reference a canonical event record containing the company, event type, disclosure time, source, relevant historical context and outcome availability.

### Memory domain 2: Historical situations and analogues

Store descriptions of comparable historical situations, including why they were considered similar and which dimensions differed.

Examples of comparison dimensions include:

- Growth acceleration or deceleration.
- Margin expansion or compression.
- Valuation regime.
- Leverage and cash-flow position.
- Earnings surprise.
- Guidance revision.
- Market volatility.
- Sector conditions.
- Relevant macroeconomic environment.

The memory must preserve both similarities and differences.

### Memory domain 3: Research theses

Retain historical research conclusions, the evidence used, assumptions made, competing explanations, catalysts and invalidation conditions.

Separate the date a thesis was created from the period it describes.

### Memory domain 4: Forecasts and realized outcomes

Retain the exact forecast, information cutoff, methodology, expected horizon and evidence available when the forecast was produced.

When the horizon matures, link the record to an independently calculated realized outcome.

Never modify the original forecast to make it agree with the result.

### Memory domain 5: Validated analytical lessons

Retain lessons only when their supporting evidence and evaluation status can be identified.

Distinguish an exploratory hypothesis from a replicated finding and a finding that failed on subsequent evaluation.

Do not let an LLM promote its own speculation into a validated lesson.

## 12. Memory retrieval architecture

Implement a hybrid recall pipeline combining supported Hindsight retrieval with structured filtering and deterministic analysis.

The workflow must:

1. Resolve the target company and security.
2. Extract the current analytical question and event context.
3. Apply temporal eligibility filters.
4. Retrieve candidate memories using the available Hindsight capabilities.
5. Filter candidates by company, event category, sector and relevant time period.
6. Assess semantic relevance and evidence quality.
7. Calculate quantitative similarity features where suitable.
8. Remove duplicates and identify contradictory evidence.
9. Fetch authoritative structured records for the selected candidates.
10. Calculate historical outcome distributions.
11. Return an evidence-linked set of analogues to the research workflow.

Use a two-stage retrieval design where appropriate: efficient candidate generation followed by more selective ranking.

Do not rely on vector similarity alone to establish financial comparability.

A historical event can be semantically similar but economically different. Conversely, two events with different wording can have similar financial structures.

Where enough data exists, test alternative ranking approaches rather than hardcoding arbitrary weights and declaring the result optimal.

Every analogue result should expose its supporting source records, matching criteria, material differences, sample size and outcome coverage.

## 13. Hindsight reflection and analytical feedback

Use reflection to identify:

- Repeated historical patterns.
- Exceptions and contradictions.
- Failed historical theses.
- Conditions under which a previous analogy was misleading.
- Important differences between the current situation and its precedents.
- Potential improvements to future research questions.

Reflection must generate hypotheses, not unverified numerical facts.

Any claim such as "similar events led to an average 8% gain" must be calculated from eligible, structured, resolved observations.

Reflection results must be linked to the memories used, their timestamps, the method version and the status of any subsequent validation.

Prevent duplicate generated reports from overwhelming original evidence.

Keep research-session memory, factual-event memory and resolved-outcome memory logically distinct.

## 14. Measure the value of memory

Implement a formal memory-ablation experiment.

Compare otherwise equivalent research or forecasting pipelines with and without retrieved historical memory.

Control for:

- Available market data.
- Prediction timestamps.
- Evaluation periods.
- Model versions.
- Forecast horizons.
- Data quality.
- Scoring methodology.
- Relevant model and prompt configuration.

Measure whether memory improves forecast accuracy, research completeness, source coverage, risk identification or another clearly defined objective.

Do not apply an artificial confidence penalty to the no-memory baseline.

If memory improves the narrative but not forecast accuracy, report that distinction. If it provides no measurable improvement, investigate and report the result rather than concealing it.

---

# PART VII — MULTI-STAGE RESEARCH ORCHESTRATION

## 15. Implement a controlled research workflow

Inspect the existing graph or agent orchestration implementation before adding new agents.

Use the existing framework if it provides suitable state management, retries and tracing.

Do not introduce a large collection of agents simply for appearance. Create specialist stages only where they have distinct responsibilities and verifiable outputs.

The recommended logical research stages are:

### Stage A: Security resolution

Resolve the company, security, exchange, currency and requested historical period.

Stop or request clarification if the security cannot be identified reliably.

### Stage B: Evidence acquisition

Retrieve available prices, fundamentals, filings, news and relevant benchmark data.

Return source metadata, timestamps, coverage and quality flags.

### Stage C: Quantitative analysis

Calculate the requested performance, risk, valuation and financial metrics.

Return structured numerical results and methodology metadata.

### Stage D: Historical memory research

Retrieve eligible historical events, previous company-specific research and relevant cross-company analogues.

Return evidence-linked memories, matching criteria and identified limitations.

### Stage E: Independent challenge

Review the emerging thesis for:

- Contradictory evidence.
- Missing or stale data.
- Look-ahead bias.
- Misleading comparisons.
- Unsupported causality.
- Alternative explanations.
- Risks that could invalidate the thesis.

This stage should challenge the analysis, not merely generate an opposing paragraph.

### Stage F: Scenario analysis

Construct bullish, base and bearish cases from explicit drivers and assumptions.

Use deterministic calculations for numerical scenario outputs.

### Stage G: Research synthesis

Assemble the results into a coherent report with source citations, uncertainty and explicit evidence boundaries.

### Stage H: Validation and persistence

Validate the report schema, verify that source references exist, check the consistency of numerical claims and save the research record.

Create a forecast record only when the workflow explicitly defines a testable forecast and its evaluation horizon.

### Stage I: Outcome resolution

Run separately when the relevant forecast horizon matures. Retrieve subsequent eligible market observations and resolve the forecast.

Do not resolve a prediction using data that has not yet arrived.

## 16. Typed state and fault isolation

Every research stage must have a typed input and output contract.

The research state should include:

- Research ID.
- Security identifier.
- Analysis timestamp and cutoff.
- Requested period.
- Retrieved data references.
- Data-quality findings.
- Quantitative results.
- Retrieved-memory references.
- Evidence and citations.
- Scenario assumptions.
- Research conclusion.
- Validation status.
- Errors and partial failures.

Use bounded retries, idempotency and explicit stage status.

If news retrieval fails, a price-based report may still be possible, but its news section must be marked unavailable.

If price history is insufficient for the requested analysis, the system must not generate fabricated quantitative results.

If an LLM returns invalid structured output, validate and retry under controlled conditions or report a failure.

Make the workflow observable so that a developer can identify which stage failed and why.

---

# PART VIII — QUANTITATIVE RESEARCH AND HISTORICAL EVENT STUDIES

## 17. Deterministic analytics

Implement reusable, tested calculations for:

- Historical and cumulative returns.
- Rolling returns.
- Volatility.
- Maximum drawdown and drawdown duration.
- Beta and correlation.
- Benchmark-relative performance.
- Downside volatility.
- Value-at-Risk and expected shortfall with documented assumptions.
- Moving averages and technical indicators.
- Abnormal volume and price shocks.
- Financial statement growth and profitability.
- Cash flow, leverage and liquidity metrics.
- Valuation multiples.
- Event-window returns.
- Forecast errors and calibration metrics.

Preserve the units, time windows, assumptions, input coverage and methodology version for every result.

Use adjusted prices appropriately and distinguish price return from total return.

Do not compare accounting periods or currencies without appropriate normalization.

## 18. Historical event-study engine

Build a reusable event-study framework that calculates market behavior around historical catalysts.

For each event:

- Establish the correct event date and public availability time.
- Select an appropriate benchmark.
- Define pre-event and post-event windows.
- Calculate raw and benchmark-relative returns.
- Measure volatility and drawdown changes.
- Handle overlapping events.
- Identify missing or ambiguous event timing.
- Record the sample inclusion criteria.

For suitable event studies, implement standard abnormal-return and cumulative-abnormal-return calculations where the required estimation data exists.

Document assumptions, estimation windows and limitations.

Distinguish descriptive association from causal inference.

Do not claim that a news event caused a price movement merely because the two occurred close together.

## 19. Historical analogue engine

Create a separate service for comparing the current company situation with historical cases.

For every candidate analogue, evaluate:

- Economic similarity.
- Event similarity.
- Financial condition.
- Valuation context.
- Sector and macro regime.
- Market volatility.
- Data availability.
- Material differences.

Calculate outcomes at specified trading-day horizons using point-in-time eligible records.

Return distributions and dispersion, not just averages.

Include unsuccessful cases, contradictory evidence and sample-size warnings.

Where the sample is small, say so. Do not manufacture statistical significance.

---

# PART IX — FORECASTING, SCENARIOS AND EVALUATION

## 20. Separate forecasts from narratives

The system must support distinct modes:

1. Historical descriptive research.
2. Fundamental and valuation analysis.
3. Scenario analysis.
4. Quantitative forecasting.
5. Retrospective forecast evaluation.

Do not treat all five as the same task.

A scenario is a conditional calculation based on assumptions. A forecast is a testable statement about a future outcome. A historical analogue is an observed precedent. An investment thesis is an interpretation of evidence.

These must be represented separately in the data model and user interface.

## 21. Forecast construction

Start with defensible baselines before adding complex models.

Evaluate simple historical baselines and suitable quantitative methods before selecting more sophisticated models.

Reuse existing LSTM, ARIMA or SARIMAX code only where its implementation, assumptions and performance justify doing so.

Do not select a model because it is complex or because it fits historical data closely.

Where forecasting is supported, store:

- Forecast timestamp.
- Information cutoff.
- Security identifier.
- Target variable.
- Forecast horizon.
- Methodology and model version.
- Prediction value or distribution.
- Uncertainty estimate.
- Input data references.
- Memory references.
- Evaluation eligibility.
- Eventual realized outcome.

Use calibrated probabilities only when a defensible probabilistic method and sufficient evaluation data support them.

Otherwise, show ranges, scenarios or directional hypotheses without implying that they are calibrated probabilities.

## 22. Point-in-time walk-forward evaluation

Implement chronological evaluation.

For each historical cutoff:

1. Construct the information set available at that time.
2. Retrieve only eligible memories.
3. Generate the forecast or research conclusion.
4. Persist the result before using future observations.
5. Wait until the specified outcome horizon matures.
6. Calculate the realized result.
7. Evaluate the prediction against its baseline.
8. Aggregate results across appropriate samples.

Prevent future-data leakage through financial restatements, news timestamps, later memory updates, revised corporate mappings or incorrectly adjusted prices.

Address survivorship bias by including delisted securities where data permits.

Use chronological development, validation and final evaluation periods.

Do not repeatedly tune the system against the final evaluation set.

Report:

- Sample size.
- Forecast error.
- Directional accuracy.
- Calibration where applicable.
- Performance by horizon.
- Performance by sector and event category.
- Downside behavior.
- Benchmark-relative outcomes where appropriate.
- Uncertainty estimates.
- Data exclusions and limitations.

For portfolio simulations, include realistic execution assumptions, turnover and transaction costs.

Do not equate forecast accuracy with investment profitability.

---

# PART X — INSTITUTIONAL RESEARCH WORKSPACE

## 23. Product design principles

Build a serious financial research interface.

The product should prioritize information density, analytical clarity, source traceability and fast navigation.

Avoid a generic chatbot-first layout, decorative AI widgets, fake live data and oversized marketing cards.

The main workflow should be:

**Search security → inspect market evidence → examine historical context → challenge the thesis → review scenarios → inspect sources → track the outcome.**

Use the existing frontend architecture and charting dependencies where practical.

## 24. Global research terminal

Include:

- Company and ticker search.
- Search suggestions with security identity.
- Market benchmark overview.
- Sector performance where data exists.
- Recently researched securities.
- Research-job status.
- Data freshness and provider health.
- Persistent navigation between company research and historical memory.

## 25. Security research page

Create a professional workspace with:

**Overview:** company identity, latest available price, market capitalization where available, key metrics, and concise research summary.

**Price history:** full available trading history, two-year detailed view, range selection, volume, benchmarks and event overlays.

**Fundamentals:** financial statements, growth, margins, cash flow, debt, dilution and valuation.

**News and filings:** dated source-backed items, earnings and material catalysts.

**Risk:** volatility, drawdown, concentration, leverage, downside scenarios and relevant business risks.

**Historical analogues:** comparable events, similarity dimensions, sample outcomes, exceptions and source evidence.

**Research memo:** structured analysis with bull, base and bear cases, explicit assumptions, counterarguments and thesis invalidation conditions.

**Forecast ledger:** timestamped forecasts, expected horizons, matured outcomes and evaluation results.

Every chart, filter, source link and interactive control must work.

The frontend must use real API responses, not hardcoded production fixtures.

## 26. Historical memory explorer

Provide a dedicated interface to search historical memories by company, sector, event category, date and relevant analytical context.

Users must be able to inspect:

- Original event.
- Disclosure date.
- Source link.
- Relevant historical context.
- Why the memory was retrieved.
- Material similarities and differences.
- Observed outcomes.
- Whether the associated thesis or forecast was correct under its stated criteria.
- Whether the memory has been validated or remains exploratory.

Show missing data and uncertainty explicitly.

The memory explorer should make the system's reasoning auditable rather than presenting a mysterious similarity score.

---

# PART XI — RESEARCH REPORT CONTRACT

## 27. Standardized research output

Define a versioned research-report schema and validate it before persistence or frontend rendering.

Every report should contain:

1. Security identity and analysis timestamp.
2. Executive summary.
3. Data availability and coverage.
4. Historical performance.
5. Fundamental analysis.
6. Current catalysts.
7. Historical event analysis.
8. Hindsight-derived analogues.
9. Risk assessment.
10. Bull, base and bear scenarios.
11. Counterarguments and invalidation conditions.
12. Conclusion and unresolved questions.
13. Sources and methodology.
14. Forecast metadata, if a testable forecast was created.

Each material claim must be classified as one of:

- Source-backed fact.
- Deterministically calculated result.
- Historical observation.
- Analytical interpretation.
- Conditional scenario.
- Forecast.
- Unverified hypothesis.

The report must provide source references and calculation metadata wherever applicable.

A generated report should be reproducible from its stored data references, methodology version, memory references and configuration, to the extent supported by the retained inputs.

Do not promise bit-for-bit reproducibility for nondeterministic model outputs. Instead, preserve the original output and its execution metadata.

---

# PART XII — IMPLEMENTATION AND ENGINEERING QUALITY

## 28. Production engineering requirements

Implement appropriate:

- Database migrations.
- Typed API schemas.
- Configuration validation.
- Secret management.
- Structured logging.
- Job tracing.
- Error handling.
- Timeouts and bounded retries.
- Rate limiting.
- Cache invalidation.
- Health checks.
- Data-quality reports.
- Background jobs.
- Backup and recovery documentation.
- Dependency and security checks.

Keep provider-specific logic outside core analytics.

Use dependency injection or equivalent explicit interfaces where it improves testability.

Avoid unnecessary abstractions and premature microservices. A modular monolith with clear service boundaries is preferable until measured scale or deployment constraints justify distributed components.

Do not build an elaborate distributed agent framework merely to make the architecture look sophisticated.

## 29. Testing strategy

Write unit tests for deterministic financial calculations and temporal eligibility.

Write integration tests for provider adapters, persistence, Hindsight operations and research orchestration.

Write regression tests for known existing defects discovered during the audit.

Write frontend tests for search, chart ranges, partial data, research reports and historical-memory inspection.

Include explicit tests for:

- Future information being excluded from historical research.
- Duplicate memories not dominating retrieval.
- Unresolved outcomes remaining unresolved.
- Missing values not being treated as zero.
- Memory-disabled analysis receiving no artificial penalty.
- Forecast records remaining immutable after creation.
- Provider outages producing explicit partial failures.
- Historical chart coverage matching actual source availability.
- Financial metrics being calculated with the correct period and units.

Use deterministic fixtures for tests and identify them as fixtures.

Do not present test fixtures as real financial data.

Run the existing test suite before and after changes, and explain regressions.

---

# PART XIII — EXECUTION PROTOCOL

## 30. Implement in controlled phases

### Phase 0 — Repository audit

Deliver the architecture map, verified baseline, identified defects and implementation plan.

### Phase 1 — Correctness foundation

Fix existing analytical errors, timestamp handling, security mapping issues, memory duplication and misleading confidence calculations.

### Phase 2 — Canonical data model

Implement the required entity models, migrations, provider contracts and data-quality framework.

### Phase 3 — Working single-security workflow

Make a real stock search, historical price chart, key quantitative metrics and source-backed company details work end-to-end.

### Phase 4 — Hindsight integration

Implement memory categories, ingestion, recall, temporal filtering, analogue retrieval and evidence-linked reflection.

### Phase 5 — Research orchestration

Implement typed research stages, independent analytical challenge, scenario construction and validated report persistence.

### Phase 6 — Prediction and outcome ledger

Implement immutable forecasts, horizon-based resolution and reproducible evaluation.

### Phase 7 — Institutional research workspace

Complete the frontend research terminal and historical-memory explorer.

### Phase 8 — Evaluation and universe scaling

Run walk-forward experiments, evaluate memory contribution, expand historical ingestion and measure Fortune 500 coverage.

### Phase 9 — Reliability and deployment

Complete regression tests, observability, documentation, configuration validation and deployment checks.

After each phase, verify the implementation before proceeding.

Continue through the phases without asking for approval for routine engineering decisions. Ask only when a genuine product decision, irreversible action or missing external credential blocks progress.

Do not wait until the end to run tests.

Do not spend substantial resources on full-universe backfills before the single-security pipeline has passed its acceptance tests.

---

# PART XIV — FINAL ACCEPTANCE GATES

## 31. Functional gate

A user can search a real company, inspect its available historical price series, examine financial metrics and dated news, retrieve relevant Hindsight memories, and generate a traceable research report.

## 32. Temporal correctness gate

A historical analysis cannot access information published after its stated cutoff.

The system can demonstrate how it enforced this restriction.

## 33. Memory integrity gate

Historical events, research interpretations, forecasts and resolved outcomes are distinguishable and linked through stable references.

Recall returns relevant evidence and preserves contradictions rather than manufacturing certainty.

## 34. Quantitative correctness gate

Critical calculations are covered by deterministic tests and use documented units, periods and assumptions.

Historical event returns and forecast outcomes are derived from eligible structured data.

## 35. Evaluation gate

The system can compare memory-enabled and memory-disabled workflows over equivalent evaluation samples.

It reports actual results, uncertainty and limitations, even when the results do not show improvement.

## 36. Operational gate

The application has documented configuration, migrations, run commands, data-ingestion commands, tests and recovery procedures.

It can restart without losing its persistent research records.

## 37. Coverage gate

The system reports measured Fortune 500 and security-level coverage, including unresolved identities, missing histories and provider limitations.

It does not claim universal coverage without evidence.

---

# PART XV — REQUIRED ENGINEERING HANDOFF

At completion, produce:

- Verified architecture and data-flow documentation.
- Architecture decision records.
- Implemented database schema and migrations.
- API and research-report contracts.
- Provider and Hindsight integration documentation.
- Installation and environment configuration instructions.
- Historical ingestion and backfill procedures.
- Prediction resolution and evaluation commands.
- Automated test results.
- Frontend build and backend verification results.
- Actual Fortune 500 coverage statistics, if ingestion was completed.
- Memory retrieval and evaluation findings, if experiments were run.
- A list of incomplete work, external blockers and known limitations.

Clearly separate implemented features, tested features, untested integrations and future work.

Never claim that an integration, test, ingestion run or backtest succeeded unless the execution result supports that claim.

## FINAL DIRECTIVE

Begin with the existing QuantMind repository.

Inspect the actual code and dependencies. Establish the baseline. Make architectural decisions based on verified evidence. Implement the system in controlled phases, preserve existing functionality, and test each critical path.

The objective is not to create the largest number of agents, the longest report, the most elaborate dashboard or the largest memory store.

The objective is to build a reliable system in which historical financial evidence, persistent memory, deterministic quantitative analysis and AI research synthesis reinforce one another—and in which the value of that combination can be independently measured.

**Build the system. Verify the claims. Preserve the evidence. Measure whether Hindsight makes QuantMind better.**