# Phase 1 manual checklist

- Run `uv sync --extra test` and `npm --prefix web install`.
- Run `python scripts/build_universe.py` with a real SEC contact in
  `--user-agent`; confirm `data/universe.json` contains the S&P 100, Nasdaq
  listings, and 250 crypto assets.
- Start the API and confirm `/api/universe` returns typed assets.
- Open the web app and press **Ctrl+K** (or **Cmd+K**).
- Type `apple`, `meta plat`, `berkshire`, `nvidia`, `tesla`, and `BRK-B`.
- Confirm results are grouped by asset kind, exact/prefix matches appear first,
  and arrow keys plus Enter navigate without submitting the page.
- Confirm the search waits 150 ms before making a request and the input has
  `autocomplete="off"`.
- Visit `/`, `/stock/PLTR`, and `/memory` directly and through client-side links.
- Run `python -m ruff check quantmind tests scripts`, `python -m pytest`, and
  `npm --prefix web run build`.
