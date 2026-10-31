import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { understandQuery, type ParsedQuery } from "../lib/api";
import { useSearch } from "../components/SearchPalette";

const watchlist = ["AAPL", "MSFT", "NVDA", "PLTR", "CRM", "META"];

export function HomePage() {
  const { openSearch } = useSearch();
  const [question, setQuestion] = useState("");
  const [parsed, setParsed] = useState<ParsedQuery | null>(null);
  const [routing, setRouting] = useState(false);

  useEffect(() => {
    if (!question.trim()) { setParsed(null); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setRouting(true);
      understandQuery(question, controller.signal).then(setParsed).catch(() => undefined).finally(() => setRouting(false));
    }, 250);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [question]);

  return <section className="home-workspace">
    <div className="terminal-banner"><span className="live-dot">●</span> QUANTMIND INTELLIGENCE TERMINAL <span className="banner-right">UTC {new Date().toISOString().slice(11, 19)} · POINT-IN-TIME MODE</span></div>
    <div className="home-grid">
      <div className="home-primary">
        <p className="eyebrow">RESEARCH WORKSPACE / PHASE 4</p>
        <h1>Find the signal<br /><em>behind the move.</em></h1>
        <p className="lede">Structured market data, source evidence and persistent precedent in one disciplined research surface.</p>
        <div className="query-box"><span className="query-mark">⌕</span><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a market question, metric or event…" /><button onClick={openSearch}>⌘K</button></div>
        {(routing || parsed) && <div className="route-card">{routing ? <span>Routing query…</span> : <><strong>{parsed?.intent.split("_").join(" ").toUpperCase()}</strong><span>{parsed?.retrieval_strategy.join(" · ")}</span>{parsed?.clarification && <small>{parsed.clarification}</small>}</>}</div>}
      </div>
      <aside className="watch-panel panel"><div className="panel-head"><span>WATCHLIST</span><small>CANONICAL UNIVERSE</small></div>{watchlist.map((symbol) => <Link className="watch-row" to={`/stock/${symbol}`} key={symbol}><strong>{symbol}</strong><span>Open monitor</span><b>›</b></Link>)}</aside>
    </div>
    <div className="terminal-strip"><span>WORKSPACES</span><span>OVERVIEW</span><span>SECURITY MONITOR</span><span>EVIDENCE LEDGER</span><span>HINDSIGHT MEMORY</span></div>
    <div className="home-note"><strong>Research discipline</strong><span>Verified facts, calculated metrics and interpretation remain visually separated. Missing coverage is never replaced with a guess.</span></div>
  </section>;
}
