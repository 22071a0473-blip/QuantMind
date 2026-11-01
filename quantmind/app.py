from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html import escape
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles

from .agent_graph import AgentGraph, AgentState
from .analogue_retrieval import AnalogueService
from .analogues import AnalogueMatch, EventQuery
from .confidence_engine import ConfidenceAudit, ConfidenceEngine
from .current_event import detect_current_event
from .engine import QuantMindEngine
from .event_memory import QuantMindEventMemory
from .event_store import EventStore, MarketEvent
from .llm import GroqResearcher
from .memory import HindsightMemory
from .search import ParsedQuery, SearchExecution, SearchResult, fts_query, parse_query
from .storage import SQLiteStore
from .universe import AssetKind, SearchResponse, UniverseAsset, list_universe, search_universe

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="QuantMind", version="1.1.0")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
_WEB_DIST = Path(__file__).resolve().parent.parent / "web-dist"
if not _WEB_DIST.is_dir():
    _WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
if _WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_WEB_DIST / "assets"), name="web-assets")


@dataclass(slots=True)
class CachedReport:
    expires_at: float
    payload: dict[str, object]


_REPORT_CACHE: dict[str, CachedReport] = {}
_REQUEST_TIMES: dict[str, list[float]] = {}
_CACHE_TTL_SECONDS = 300.0
_RATE_WINDOW_SECONDS = 60.0
_RATE_LIMIT_PER_IP = 30
_STATE_LOCK = threading.Lock()


@app.on_event("startup")
async def import_event_snapshot_on_startup() -> None:
    database = Path(os.environ.get("QUANTMIND_DATABASE", "data/quantmind.db"))
    snapshot = Path(__file__).resolve().parent.parent / "data" / "market_events.jsonl"
    store = EventStore(database)
    try:
        if store.list_events(limit=1) or not snapshot.exists():
            return
        imported = store.import_jsonl(snapshot)
        logger.info("Imported %d market events from %s.", imported, snapshot)
    finally:
        store.close()


def build_store() -> SQLiteStore:
    return SQLiteStore(Path(os.environ.get("QUANTMIND_DATABASE", "data/quantmind.db")))


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
    return QuantMindEngine(HindsightMemory(), GroqResearcher())


def enforce_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _STATE_LOCK:
        recent = [
            timestamp for timestamp in _REQUEST_TIMES.get(client_ip, []) if now - timestamp < _RATE_WINDOW_SECONDS
        ]
        if len(recent) >= _RATE_LIMIT_PER_IP:
            raise HTTPException(status_code=429, detail="Rate limit exceeded; retry shortly.")
        recent.append(now)
        _REQUEST_TIMES[client_ip] = recent


def validate_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not re.fullmatch(r"(?:CRYPTO:[A-Z0-9_-]+|[A-Z0-9.-]{1,12})", normalized):
        raise HTTPException(status_code=404, detail=f"No price data for {ticker} on requested date")
    return normalized


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    if (_WEB_DIST / "index.html").is_file():
        return FileResponse(_WEB_DIST / "index.html", media_type="text/html")
    return templates.TemplateResponse(request=request, name="index.html", context={"report": None, "error": None})


@app.get("/stock/{symbol:path}", response_class=HTMLResponse)
async def stock_page(symbol: str) -> HTMLResponse:
    del symbol
    if (_WEB_DIST / "index.html").is_file():
        return FileResponse(_WEB_DIST / "index.html", media_type="text/html")
    raise HTTPException(status_code=404, detail="Web application is not built")


@app.get("/memory", response_class=HTMLResponse)
async def memory_page() -> HTMLResponse:
    if (_WEB_DIST / "index.html").is_file():
        return FileResponse(_WEB_DIST / "index.html", media_type="text/html")
    raise HTTPException(status_code=404, detail="Web application is not built")


@app.post("/research", response_class=HTMLResponse)
async def research(
    request: Request,
    asset: str = Form(min_length=1, max_length=40),
    target_price: float | None = Form(default=None, gt=0),
) -> HTMLResponse:
    enforce_rate_limit(request)
    try:
        result = await build_engine().research(validate_ticker(asset), persist_memory=True)
        if target_price is not None:
            result.report.extended_analysis.roadmap.success_definition += (
                f" Scenario input {target_price:.4f}; this is not a prediction."
            )
        return templates.TemplateResponse(
            request=request, name="index.html", context={"report": result.report, "error": None}
        )
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
    enforce_rate_limit(request)
    try:
        result = await build_engine().research(
            validate_ticker(asset),
            memory_enabled=memory,
            persist_memory=False,
        )
        return templates.TemplateResponse(
            request=request, name="index.html", context={"report": result.report, "error": None}
        )
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
async def health() -> dict[str, object]:
    engine = build_engine()
    database = "ok"
    try:
        store = build_store()
        store.close()
    except Exception:
        database = "unavailable"
    hindsight = "not_configured"
    if engine.memory.configured:
        try:
            await asyncio.wait_for(engine.memory.health_check(), timeout=3.0)
            hindsight = "ok"
        except Exception:
            hindsight = "unavailable"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "service": "quantmind",
        "database": database,
        "memory": hindsight,
        "llm": "configured" if GroqResearcher().configured else "not_configured",
        "universe_size": len(list_universe()),
    }


@app.get("/api/memory/status")
async def memory_status() -> dict[str, str]:
    engine = build_engine()
    if not engine.memory.configured:
        return {"backend": "hindsight-cloud", "status": "not_configured"}
    try:
        await asyncio.wait_for(engine.memory.health_check(), timeout=3.0)
    except Exception:
        return {"backend": "hindsight-cloud", "status": "unavailable"}
    return {"backend": "hindsight-cloud", "status": "configured"}


@app.get("/api/universe", response_model=list[UniverseAsset])
async def universe(kind: AssetKind | None = Query(default=None)) -> list[UniverseAsset]:
    return list_universe(kind)


@app.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1, max_length=80),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    return search_universe(q, limit)


@app.get("/api/query", response_model=ParsedQuery)
async def query_understanding(q: str = Query(min_length=1, max_length=500)) -> ParsedQuery:
    return parse_query(q)


@app.get("/api/search/research", response_model=SearchExecution)
async def research_search(
    q: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchExecution:
    parsed = parse_query(q)
    store = build_store()
    warnings: list[str] = []
    lexical_results: list[SearchResult] = []
    try:
        safe_query = fts_query(q)
        if safe_query:
            lexical_results = [
                SearchResult(
                    result_id=hit.result_id,
                    title=hit.title,
                    snippet=hit.snippet,
                    source_type=hit.source_type,
                    source_url=hit.source_url,
                    ticker=hit.ticker,
                    score=hit.score,
                    available_at=hit.information_cutoff.date() if hit.information_cutoff else None,
                )
                for hit in store.search_research_reports(safe_query, limit)
            ]
    finally:
        store.close()

    memory_results: list[SearchResult] = []
    memory_status: Literal["verified", "unavailable", "not_configured"] = "not_configured"
    try:
        memory_results = [
            SearchResult(
                result_id=hit.result_id,
                title=hit.title,
                snippet=hit.snippet,
                source_type="hindsight_event",
                source_url=hit.source_url,
                ticker=hit.ticker,
                score=hit.score,
            )
            for hit in await QuantMindEventMemory().search(q, limit)
        ]
        memory_status = "verified"
    except KeyError:
        warnings.append("Hindsight is not configured; local research results are shown.")
        memory_status = "not_configured"
    except Exception:
        warnings.append("Hindsight is unavailable; local research results are shown.")
        memory_status = "unavailable"

    structured_results = [
        SearchResult(
            result_id=f"asset:{asset.symbol}",
            title=asset.name,
            snippet=f"{asset.symbol} · {asset.sector or 'Unknown sector'}",
            source_type="structured_asset",
            ticker=asset.symbol,
            score=1.0,
        )
        for asset in search_universe(q, limit).results
    ]
    combined = structured_results + lexical_results + memory_results
    combined.sort(key=lambda result: result.score, reverse=True)
    return SearchExecution(
        query=q,
        parsed=parsed,
        results=combined[:limit],
        lexical_count=len(lexical_results),
        memory_count=len(memory_results),
        memory_status=memory_status,
        warnings=warnings,
    )


@app.get("/api/market/{ticker}")
async def market_series(
    ticker: str,
    start: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> dict[str, object]:
    normalized = validate_ticker(ticker)
    store = build_store()
    try:
        security = store.find_security(normalized)
        if security is None:
            return {"ticker": normalized, "available": False, "reason": "No canonical market series is stored."}
        profile = store.company_profile(security.security_id)
        points = store.market_series(
            security.security_id,
            start=date.fromisoformat(start) if start else None,
            end=date.fromisoformat(end) if end else None,
            limit=limit,
        )
        coverage = store.security_coverage(security.security_id, normalized)
        return {
            "ticker": normalized,
            "available": bool(points),
            "profile": profile.model_dump() if profile else None,
            "coverage": coverage.model_dump(),
            "points": [point.model_dump(mode="json") for point in points],
        }
    finally:
        store.close()


@app.get("/api/precedent/{ticker}")
async def precedent(
    ticker: str,
    cutoff: datetime | None = Query(default=None),
) -> dict[str, object]:
    """Return a point-in-time structured analogue study."""
    normalized = validate_ticker(ticker)
    effective_cutoff = cutoff.astimezone(UTC) if cutoff else datetime.now(UTC)
    if effective_cutoff > datetime.now(UTC):
        raise HTTPException(status_code=422, detail="cutoff cannot be in the future")
    detected = detect_current_event(normalized, effective_cutoff)
    if detected is None:
        return {"ticker": normalized, "detected_event": None, "status": "no_event", "cutoff": effective_cutoff.isoformat()}
    service = AnalogueService(Path(os.environ.get("QUANTMIND_DATABASE", "data/quantmind.db")))
    study = await service.astudy(detected, cutoff=effective_cutoff)
    return {
        "ticker": normalized,
        "cutoff": effective_cutoff.isoformat(),
        "status": "insufficient_analogues" if study.insufficient_analogues else "ok",
        "detected_event": _analogue_row_payload(detected, None),
        "matches": [_analogue_row_payload(match.event, match) for match in study.matches],
        "distributions": {
            horizon: distribution.model_dump(mode="json")
            for horizon, distribution in study.statistics.items()
        },
        "relaxation_level": study.relaxation_level,
        "semantic_status": study.semantic_status,
    }


def _analogue_row_payload(
    event: MarketEvent | EventQuery,
    match: AnalogueMatch | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": event.event_id or "",
        "ticker": event.ticker,
        "event_date": event.event_date.isoformat(),
        "event_type": event.event_type,
        "headline": getattr(event, "headline", f"{event.ticker} {event.event_type}"),
        "source_url": getattr(event, "source_url", None),
        "forward_returns": {
            "fwd_1d": getattr(event, "fwd_1d", None),
            "fwd_5d": getattr(event, "fwd_5d", None),
            "fwd_20d": getattr(event, "fwd_20d", None),
            "fwd_60d": getattr(event, "fwd_60d", None),
        },
    }
    if match is not None:
        payload.update(
            {
                "similarity": match.similarity,
                "feature_scores": match.feature_scores.model_dump(exclude_none=True),
                "retrieval_source": match.retrieval_source,
                "relaxation_level": match.relaxation_level,
            }
        )
    return payload


@app.get("/api/report/{ticker}")
async def report(
    request: Request,
    ticker: str,
    memory: bool = True,
) -> dict:
    enforce_rate_limit(request)
    normalized = validate_ticker(ticker)
    cache_key = f"{normalized}:{memory}"
    with _STATE_LOCK:
        cached = _REPORT_CACHE.get(cache_key)
        if cached and cached.expires_at > time.monotonic():
            return cached.payload
    try:
        result = await build_engine().research(normalized, memory_enabled=memory, persist_memory=False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"No price data for {normalized}: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Memory backend unavailable") from exc
    payload = result.report.model_dump()
    with _STATE_LOCK:
        _REPORT_CACHE[cache_key] = CachedReport(
            expires_at=time.monotonic() + _CACHE_TTL_SECONDS,
            payload=payload,
        )
    return payload


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run the explicit acquisition/recall/analyze graph for terminal clients."""
    normalized = validate_ticker(request.asset)
    engine = build_engine()
    graph = AgentGraph(engine.sources, engine.memory)
    state = await graph.run(AgentState(asset=normalized, query=request.query, memory_enabled=request.memory))
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
async def reflect_get(
    ticker: str, query: str = "What patterns emerge from this ticker's historical moves?"
) -> dict[str, str]:
    return await reflect_for_ticker(ticker, query)


@app.post("/api/reflect/{ticker}")
async def reflect_post(
    ticker: str, query: str = "What patterns emerge from this ticker's historical moves?"
) -> dict[str, str]:
    return await reflect_for_ticker(ticker, query)


from .ledger_routes import router as ledger_router

app.include_router(ledger_router)
