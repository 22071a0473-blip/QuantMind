import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import "./style.css";

type Asset = { symbol: string; name: string; kind: string; sector?: string; industry?: string };
type SearchResponse = { results: Asset[]; total: number };

function Search() {
  const [open, setOpen] = useState(false); const [query, setQuery] = useState(""); const [data, setData] = useState<SearchResponse>({ results: [], total: 0 }); const [selected, setSelected] = useState(0); const input = useRef<HTMLInputElement>(null); const navigate = useNavigate();
  useEffect(() => { const handler = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setOpen(true); setTimeout(() => input.current?.focus(), 0); } }; window.addEventListener("keydown", handler); return () => window.removeEventListener("keydown", handler); }, []);
  useEffect(() => { const timer = window.setTimeout(async () => { if (!query.trim()) return setData({ results: [], total: 0 }); const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`); setData(await response.json()); setSelected(0); }, 150); return () => window.clearTimeout(timer); }, [query]);
  const go = (asset: Asset) => { setOpen(false); navigate(asset.kind === "crypto" ? `/?asset=${asset.symbol}` : `/stock/${asset.symbol}`); };
  const groups = data.results.reduce<Record<string, Asset[]>>((acc, asset) => ({ ...acc, [asset.kind]: [...(acc[asset.kind] ?? []), asset] }), {});
  return <>{open && <div className="overlay" onMouseDown={() => setOpen(false)}><div className="palette" onMouseDown={event => event.stopPropagation()}><input ref={input} autoComplete="off" value={query} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === "ArrowDown") setSelected(Math.min(selected + 1, data.results.length - 1)); if (event.key === "ArrowUp") setSelected(Math.max(selected - 1, 0)); if (event.key === "Enter" && data.results[selected]) go(data.results[selected]); if (event.key === "Escape") setOpen(false); }} placeholder="Search stocks, ETFs, crypto..." />{Object.entries(groups).map(([kind, assets]) => <div key={kind}><div className="group-title">{kind}</div>{assets.map(asset => { const index = data.results.indexOf(asset); return <button className={index === selected ? "result selected" : "result"} key={asset.symbol} onClick={() => go(asset)}><span>{asset.symbol}</span><small>{asset.name}</small></button>; })}</div>)}</div></div>}<button className="search-button" onClick={() => setOpen(true)}>Search <kbd>Ctrl K</kbd></button></>;
}
function Shell({ children }: { children: React.ReactNode }) { return <><header><Link to="/" className="brand">QUANTMIND</Link><nav><Link to="/">Universe</Link><Link to="/memory">Memory</Link></nav><Search /></header><main>{children}</main></>; }
function Home() { return <section className="hero"><p className="eyebrow">Evidence before conviction</p><h1>Search the market<br /><em>with memory.</em></h1><p className="lede">A research terminal for live catalysts, deterministic signals, and Hindsight precedent.</p><Search /><Link className="cta" to="/stock/PLTR">Open PLTR research →</Link></section>; }
function Stock() { const { symbol = "PLTR" } = useParams(); return <section><p className="eyebrow">Research asset</p><h1>{symbol}</h1><p className="lede">Live report routing is ready. The evidence view will be populated by the QuantMind API.</p><a className="cta" href={`/api/report/${symbol}`}>Open API report →</a></section>; }
function Memory() { return <section><p className="eyebrow">Hindsight</p><h1>Memory ledger</h1><p className="lede">Persistent precedents and reflections will appear here as research reports accumulate.</p></section>; }
function App() { return <Shell><Routes><Route path="/" element={<Home />} /><Route path="/stock/:symbol" element={<Stock />} /><Route path="/memory" element={<Memory />} /></Routes></Shell>; }
createRoot(document.getElementById("root")!).render(<React.StrictMode><BrowserRouter><App /></BrowserRouter></React.StrictMode>);
