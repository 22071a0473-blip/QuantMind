from __future__ import annotations

import re
from html import escape
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .agent_graph import AgentGraph, AgentState
from .confidence_engine import ConfidenceAudit, ConfidenceEngine
from .engine import QuantMindEngine
from .llm import GroqResearcher
from .memory import HindsightMemory

load_dotenv()

app = FastAPI(title="QuantMind", version="1.1.0")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


class AnalyzeRequest(BaseModel):
    asset: str = Field(min_length=1, max_length=40)
    query: str = Field(default="", max_length=500)
    memory: bool = True


class AnalyzeResponse(BaseModel):
    asset: str
    phase: str
    confidence: ConfidenceAudit
    recalled_count: int
    errors: list[str]


@app.exception_handler(StarletteHTTPException)
async def api_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse | HTMLResponse:
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})
    detail = escape(str(exc.detail))
    return HTMLResponse(
        status_code=exc.status_code,
        content=(
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<title>QuantMind error</title><style>"
            "body{font:16px system-ui,sans-serif;background:#08111f;color:#eef4ff;"
            "padding:4rem;max-width:720px;margin:auto}a{color:#58e0bd}"
            "</style></head><body><h1>QuantMind could not complete that request</h1>"
            f"<p>{detail}</p><p><a href='/'>Return to QuantMind</a></p></body></html>"
        ),
    )


def build_engine() -> QuantMindEngine:
    try:
        return QuantMindEngine(HindsightMemory(), GroqResearcher())
    except KeyError as exc:
        raise HTTPException(status_code=503, detail=f"Missing required environment variable: {exc.args[0]}") from exc


def validate_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not re.fullmatch(r"(?:CRYPTO:[A-Z0-9_-]+|[A-Z0-9.-]{1,12})", normalized):
        raise HTTPException(status_code=404, detail=f"No price data for {ticker} on requested date")
    return normalized


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html", context={"report": None, "error": None})


@app.post("/research", response_class=HTMLResponse)
async def research(
    request: Request,
    asset: str = Form(min_length=1, max_length=40),
    target_price: float | None = Form(default=None, gt=0),
) -> HTMLResponse:
    try:
        result = await build_engine().research(validate_ticker(asset))
        if target_price is not None:
            result.report.extended_analysis.roadmap.success_definition += (
                f" Scenario input {target_price:.4f}; this is not a prediction."
            )
        return templates.TemplateResponse(request=request, name="index.html", context={"report": result.report, "error": None})
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"report": None, "error": str(exc.detail)},
            status_code=exc.status_code,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"report": None, "error": f"Research failed: {exc}"},
            status_code=502,
        )


@app.get("/research", response_class=HTMLResponse)
async def research_get(
    request: Request,
    asset: str = Query(min_length=1, max_length=40),
    memory: bool = True,
) -> HTMLResponse:
    try:
        result = await build_engine().research(validate_ticker(asset), memory_enabled=memory)
        return templates.TemplateResponse(request=request, name="index.html", context={"report": result.report, "error": None})
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"report": None, "error": str(exc.detail)},
            status_code=exc.status_code,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"report": None, "error": f"Research failed: {exc}"},
            status_code=502,
        )


@app.get("/api/health")
async def health() -> dict[str, str]:
    build_engine()
    return {"status": "ok", "service": "quantmind", "memory": "hindsight-cloud", "llm": "groq"}


@app.get("/api/memory/status")
async def memory_status() -> dict[str, str]:
    build_engine()
    return {"backend": "hindsight-cloud", "status": "configured"}


@app.get("/api/report/{ticker}")
async def report(
    ticker: str,
    date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    memory: bool = True,
) -> dict:
    del date  # The live providers expose the current session; the query is retained for API compatibility.
    normalized = validate_ticker(ticker)
    try:
        result = await build_engine().research(normalized, memory_enabled=memory)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"No price data for {normalized}: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Memory backend unavailable") from exc
    return result.report.model_dump()


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run the explicit acquisition/recall/analyze graph for terminal clients."""
    normalized = validate_ticker(request.asset)
    engine = build_engine()
    graph = AgentGraph(engine.sources, engine.memory)
    state = await graph.run(
        AgentState(asset=normalized, query=request.query, memory_enabled=request.memory)
    )
    if state.phase.value == "failed":
        raise HTTPException(status_code=503, detail="Research graph failed")
    observations: dict[str, float | None] = {}
    if state.live is not None:
        features = state.live.features
        observations = {
            "price_change_1d": features.return_1d,
            "price_change_5d": features.return_5d,
            "price_change_20d": features.return_20d,
            "volume_ratio": features.volume_ratio,
            "volatility": features.volatility_20d,
            "drawdown": features.drawdown_1y,
            "momentum": features.momentum_20d,
            "trend_slope": features.trend_slope,
            "sma20_distance": features.price_vs_sma20,
            "sma50_distance": features.price_vs_sma50,
            "high_low_position": features.high_low_position,
            "news_count": features.news_count,
            "news_recency": 100.0 if features.news_count else None,
            "event_clarity": 100.0 if features.news_count else 0.0,
            "memory_precedent": min(100.0, len(state.recalled.records) * 20) if state.recalled else 0.0,
        }
    audit = ConfidenceEngine().evaluate(observations)
    return AnalyzeResponse(
        asset=normalized,
        phase=state.phase.value,
        confidence=audit,
        recalled_count=len(state.recalled.records) if state.recalled else 0,
        errors=state.errors,
    )


@app.get("/api/memory/{ticker}")
async def memory_list(ticker: str) -> dict:
    try:
        return await build_engine().list_memory_bank(validate_ticker(ticker))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Memory backend unavailable") from exc


@app.get("/api/signals/{ticker}")
async def signals(ticker: str) -> dict:
    normalized = validate_ticker(ticker)
    try:
        engine = build_engine()
        analytics = await engine.signal_snapshot(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"No price data for {normalized}: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Memory backend unavailable") from exc
    response = {
        "ticker": normalized,
        "signals": [signal.model_dump() for signal in analytics.signals],
        "total_signals": len(analytics.signals),
        "confidence_score": analytics.overall_score,
        "coverage": 1.0,
    }
    return response


async def reflect_for_ticker(ticker: str, query: str) -> dict[str, str]:
    normalized = validate_ticker(ticker)
    try:
        insight = await build_engine().reflect(normalized, query)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Memory backend unavailable") from exc
    return {"ticker": normalized, "insight": insight}


@app.get("/api/reflect/{ticker}")
async def reflect_get(ticker: str, query: str = "What patterns emerge from this ticker's historical moves?") -> dict[str, str]:
    return await reflect_for_ticker(ticker, query)


@app.post("/api/reflect/{ticker}")
async def reflect_post(ticker: str, query: str = "What patterns emerge from this ticker's historical moves?") -> dict[str, str]:
    return await reflect_for_ticker(ticker, query)
