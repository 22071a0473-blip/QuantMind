from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .engine import QuantMindEngine
from .llm import GroqResearcher
from .memory import HindsightMemory

load_dotenv()

app = FastAPI(title="QuantMind", version="1.0.0")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def build_engine() -> QuantMindEngine:
    try:
        return QuantMindEngine(HindsightMemory(), GroqResearcher())
    except KeyError as exc:
        raise RuntimeError(f"Missing required environment variable: {exc.args[0]}") from exc


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
        report = await build_engine().research(asset, target_price)
        return templates.TemplateResponse(request=request, name="index.html", context={"report": report, "error": None})
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
