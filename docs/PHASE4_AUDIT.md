# Phase 4 implementation audit

## Verified baseline

- The canonical SQLite store is authoritative for companies, securities, OHLCV bars, financial facts, reports, forecasts and outcomes.
- Hindsight is an external memory boundary. QuantMind writes compact reports and source-backed event records; it does not use Hindsight as the numerical market-data store.
- The installed SDK exposes `aretain`, `aretain_batch`, `arecall`, `alist_memories`, `aget_bank_config` and `acreate_bank`.
- The installed SDK does not expose a public delete-memory or operation-status method.
- The local baseline passed 47 tests before Phase 4 work.

## Implemented in this slice

- Research reports are indexed in a local SQLite FTS5 index whenever they are persisted.
- `GET /api/search/research?q=...` executes structured universe search, local lexical report search and Hindsight event-memory search.
- Results use one typed shape with source type, ticker, score and optional source URL.
- Hindsight failures are explicit in `memory_status` and `warnings`; local results remain available.
- `scripts/verify_memory.py` probes configuration, bank access, a uniquely marked write, recall, repeated document-ID write behavior and temporal-query support without printing credentials.

## Acceptance evidence and current limitations

Running `python scripts/verify_memory.py --json` in an environment without Hindsight credentials reports `not configured` rather than claiming memory success. A configured run is required before claiming verified retrieval, idempotency, or temporal cutoff behavior. Because the installed client has no delete operation, verification records cannot be automatically removed by this script; use a dedicated disposable bank if a clean run is required.

Full semantic retrieval, measured hybrid ranking, external-source document indexing, citation correctness benchmarking and the search results UI remain subsequent work. The current endpoint is intentionally a real execution path, not just parsed intent, and exposes those coverage limits to callers.
