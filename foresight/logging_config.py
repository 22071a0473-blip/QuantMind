from __future__ import annotations

import logging

from .config import Settings


def configure_logging(settings: Settings | None = None) -> None:
    """Configure one predictable root handler for CLI and API entrypoints."""
    selected = settings or Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, selected.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )

