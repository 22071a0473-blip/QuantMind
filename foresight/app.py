from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse

from .engine import build_report
from .llm import GroqSynthesizer
from .memory import MemoryService
from .sources import MarketSources

app = FastAPI(title="Foresight", version="0.1.0")
memory = MemoryService()
sources = MarketSources()
synthesizer = GroqSynthesizer()
STATIC_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(STATIC_INDEX)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "foresight"}


@app.get("/api/report/{asset}")
async def report(
    asset: str,
    target_price: float = Query(default=40.0, gt=0),
):
    source_bundle = await sources.gather(asset)
    report = await build_report(asset, target_price, memory, source_bundle)
    return await synthesizer.enrich(report, source_bundle.evidence)


@app.post("/api/reflect/{asset}")
async def reflect(asset: str, query: str = Query(min_length=1)):
    return {"asset": asset.upper(), "answer": await memory.reflect(asset.upper(), query)}
