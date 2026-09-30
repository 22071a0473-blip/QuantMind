import { createContext, useContext, useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Asset, SearchResponse, searchAssets } from "../lib/api";

type SearchContextValue = { openSearch: () => void; closeSearch: () => void };
const SearchContext = createContext<SearchContextValue | null>(null);

export function useSearch(): SearchContextValue {
  const context = useContext(SearchContext);
  if (!context) throw new Error("useSearch must be used inside SearchProvider");
  return context;
}

export function SearchProvider({ children, open, setOpen }: { children: ReactNode; open: boolean; setOpen: (value: boolean) => void }) {
  const value = useMemo(() => ({ openSearch: () => setOpen(true), closeSearch: () => setOpen(false) }), [setOpen]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setOpen]);
  return <SearchContext.Provider value={value}>{children}{open && <SearchPalette />}</SearchContext.Provider>;
}

export function SearchPalette() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [data, setData] = useState<SearchResponse>({ results: [], total: 0 });
  const [selected, setSelected] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const { closeSearch } = useSearch();

  useEffect(() => {
    if (!input.current) return;
    input.current.focus();
  }, []);

  useEffect(() => {
    const normalized = query.trim();
    if (!normalized) {
      setData({ results: [], total: 0 });
      setError(null);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await searchAssets(normalized, controller.signal);
        if (!controller.signal.aborted) {
          setData(response);
          setSelected(0);
        }
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Search failed");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 150);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [query]);

  const go = (asset: Asset) => {
    const recent = JSON.parse(localStorage.getItem("quantmind:recent-searches") || "[]") as string[];
    localStorage.setItem("quantmind:recent-searches", JSON.stringify([asset.symbol, ...recent.filter((item) => item !== asset.symbol)].slice(0, 5)));
    closeSearch();
    navigate(asset.kind === "crypto" ? `/stock/CRYPTO:${asset.symbol.replace("CRYPTO:", "")}` : `/stock/${asset.symbol}`);
  };

  const onKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") setSelected((value) => Math.min(value + 1, Math.max(data.results.length - 1, 0)));
    if (event.key === "ArrowUp") setSelected((value) => Math.max(value - 1, 0));
    if (event.key === "Enter" && data.results[selected]) go(data.results[selected]);
    if (event.key === "Escape") close();
  };

  const groups = data.results.reduce<Record<string, Asset[]>>((acc, asset) => {
    (acc[asset.kind] ||= []).push(asset);
    return acc;
  }, {});
  return (
    <div className="overlay" onMouseDown={closeSearch}>
      <div className="palette" onMouseDown={(event) => event.stopPropagation()}>
        <input ref={input} autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={onKeyDown} placeholder="Search stocks, ETFs, crypto..." />
        {loading && <p className="palette-status">Searching…</p>}
        {error && <p className="palette-error">{error}</p>}
        {!loading && !error && !query.trim() && <RecentSearches onSelect={(symbol) => setQuery(symbol)} />}
        {!loading && Object.entries(groups).map(([kind, assets]) => <div key={kind}><div className="group-title">{kind}</div>{assets.map((asset) => {
          const index = data.results.indexOf(asset);
          return <button className={index === selected ? "result selected" : "result"} key={asset.symbol} onClick={() => go(asset)}><span>{asset.symbol}</span><small>{asset.name}</small></button>;
        })}</div>)}
        {!loading && !error && query.trim() && !data.results.length && <p className="palette-status">No matching assets.</p>}
      </div>
    </div>
  );
}

function RecentSearches({ onSelect }: { onSelect: (value: string) => void }) {
  const recent = JSON.parse(localStorage.getItem("quantmind:recent-searches") || "[]") as string[];
  if (!recent.length) return <p className="palette-status">Type to search the universe.</p>;
  return <div><div className="group-title">Recent searches</div>{recent.map((symbol) => <button className="result" key={symbol} onClick={() => onSelect(symbol)}><span>{symbol}</span><small>Recent</small></button>)}</div>;
}
