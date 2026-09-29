from .memory import MemoryService
from .models import Report
from .research import ResearchContext, ResearchEngine


async def build_report(asset: str, target_price: float, memory: MemoryService) -> Report:
    """Build a research report that keeps the confidence engine and the memory loop explicit.

    The implementation intentionally preserves the public API while moving the heavy
    logic into a dedicated research layer. That keeps the model/engine split clear,
    and it makes the app far easier to extend with real news, filings, and price feeds.
    """
    asset_name = asset.upper()
    recalled = await memory.recall(
        asset_name,
        "company dossier leadership promises milestones historical events and market catalysts",
    )
    memory_summary = "; ".join(recalled.items) if recalled.items else ""
    await memory.retain(
        asset_name,
        f"Foresight retained a structured research memo for {asset_name}; confidence is recalculated from evidence and memory.",
    )
    context = ResearchContext(
        asset=asset_name,
        target_price=target_price,
        current_price=22.5,
        current_market_cap=52_000_000_000.0,
        memory_summary=memory_summary,
        historical_sample_size=max(1, len(recalled.items)),
    )
    return ResearchEngine(memory_summary).build_report(context)
