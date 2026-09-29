# Foresight

Foresight is a memory-backed market research system built for the hackathon brief:
why an asset moved, what leadership did, what must happen next, how confident the
analysis is, and how similar patterns behaved historically.

This is not a chatbot. It is a structured report engine that stores and recalls
patterns over time, using Hindsight as the memory substrate.

## Product story

The agent is built around five verticals:

1. Why the stock or token moved
2. Deep company, sector, and macro research
3. Leadership scorecard and promise ledger
4. Success roadmap and required milestones
5. Facts vs reality and historical precedent analysis

The memory layer is the differentiator: it does not store a chat log; it stores a
long-lived dossier of company context, leadership promises, milestone statuses,
market drivers, and each thesis outcome.

## Hindsight integration

Use the official Hindsight plugin for OpenClaw to persist the market memory layer
without building custom hooks by hand:

```bash
openclaw plugins install @vectorize-io/hindsight-openclaw
npx --package @vectorize-io/hindsight-openclaw hindsight-openclaw-setup \
  --mode cloud --token-env HINDSIGHT_CLOUD_TOKEN
```

Or point the project to a local or external Hindsight deployment:

```bash
npx --package @vectorize-io/hindsight-openclaw hindsight-openclaw-setup \
  --mode api --api-url http://localhost:8888 --no-token
```

Once configured, OpenClaw auto-recalls relevant memories before each turn and
retains conversations after each turn. This is exactly the right pattern for a
research agent that improves over time.

## Local run

```bash
cd foresight
uv sync --extra test
uv run uvicorn foresight.app:app --reload
```

Then open:

- http://localhost:8000/docs
- GET /api/report/PLTR?target_price=40
- POST /api/reflect/PLTR?query=What are the main catalysts?

Set environment variables for Hindsight if you want live memory instead of the
built-in local fallback:

```powershell
Copy-Item .env.example .env
# Edit .env and replace HINDSIGHT_API_TOKEN with the token from Hindsight Cloud.
```

The browser session proves your identity in the dashboard, but the local app
needs an API token of its own. Do not send the token in chat or commit `.env`.
After starting the server, verify `GET http://localhost:8000/api/memory/status`
returns `{"backend":"hindsight-cloud"}`. If it returns `local-demo`, the token or
URL is missing/invalid in the process environment.

The app keeps a local in-memory fallback for demos when no Hindsight server is
available.

## Why this structure is hackathon-strong

- It is a report engine, not a chatbot.
- It keeps a memory trail visible on every output.
- It separates deterministic analysis from LLM synthesis.
- It keeps the confidence score explainable, not mystical.
- It uses a 36-signal feature lattice with coverage penalties, regime labels,
  event-pattern analogues, and an audit trail rather than pretending unavailable
  data exists.
- It is built around the same product story as your brief: market patterns,
  leadership quality, required milestones, and the deep world conditions behind a
  move.

## Architecture

```text
Frontend (report page)
   -> Research orchestrator
      -> Hindsight recall
      -> evidence + memory fetch
      -> deterministic confidence engine
      -> roadmap engine
      -> leadership scorecard
      -> LLM synthesis (optional)
      -> Hindsight retain + reflect
```

## Immediate next steps

1. Replace the fixture evidence with live SEC, macro, and news connectors.
2. Add a Groq-backed JSON synthesis layer with validation and retry.
3. Add a watcher job for "since last time" updates.
4. Add a thesis tracker and watchlist UI.
5. Scale to 5–8 assets and a longer historical pattern library.

## Project positioning

Your strongest pitch is:

"Foresight is a memory-backed research engine for market-moving companies and
crypto assets. It remembers why the move happened, what leadership promised, what
must happen next, and how similar patterns behaved before."
