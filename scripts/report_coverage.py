"""Export canonical-store coverage as machine-readable JSON."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantmind.storage import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    store = SQLiteStore(args.database)
    try:
        payload = store.coverage_export().model_dump_json(indent=2)
    finally:
        store.close()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
