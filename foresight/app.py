from fastapi import FastAPI, Query

from .engine import build_report
from .memory import MemoryService

app = FastAPI(title="Foresight", version="0.1.0")
memory = MemoryService()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "foresight"}


@app.get("/api/report/{asset}")
async def report(
    asset: str,
    target_price: float = Query(default=40.0, gt=0),
):
    return await build_report(asset, target_price, memory)


@app.post("/api/reflect/{asset}")
async def reflect(asset: str, query: str = Query(min_length=1)):
    return {"asset": asset.upper(), "answer": await memory.reflect(asset.upper(), query)}
