"""Initialize or inspect QuantMind's local canonical database."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantmind.storage import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    args = parser.parse_args()
    store = SQLiteStore(args.database)
    try:
        print(store.export_coverage())
    finally:
        store.close()


if __name__ == "__main__":
    main()
