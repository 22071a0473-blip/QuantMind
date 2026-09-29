# QuantMind

QuantMind is a deployable, memory-backed market research engine. It is not a
chatbot and it does not ship fixture data or a local fallback in the demo path.
Each report uses live yfinance/CoinGecko data, recalls the asset's Hindsight bank,
asks Groq to synthesize only the supplied evidence, and retains the validated
report for future pattern comparison.

## Five-factor report

1. **Why it moved** — ranked catalyst categories with probabilities and citations.
2. **Deep research** — company, sector, macro, and live news context.
3. **Leadership** — sourced CEO/board track record, promises, allocation, and governance gaps.
4. **Success roadmap** — deals, orders, policy, adoption, scenarios, and kill conditions.
5. **Facts vs reality** — reported facts, market narrative, and the evidence gap.

The confidence score is deterministic: a 36-signal lattice, regime classifier,
coverage penalty, signal audit, and Hindsight memory depth. Groq never calculates
the score or invents missing data.

## Run

```powershell
Copy-Item .env.example .env
# Put the Hindsight Cloud and Groq credentials in .env locally.
uv sync
uv run uvicorn foresight.app:app --reload
```

Open http://localhost:8000. Use `CRYPTO:bitcoin` for CoinGecko or a stock ticker
such as `PLTR`, `CRWD`, or `NVDA`.

## Deploy

The repository contains `Dockerfile` and `render.yaml`. In Render, import the
GitHub repository as a Blueprint and set `HINDSIGHT_API_URL`, `HINDSIGHT_API_TOKEN`,
`GROQ_API_KEY`, and `FORESIGHT_SEC_USER_AGENT` as secret environment variables.
Render then provides the public HTTPS URL to submit to judges.
