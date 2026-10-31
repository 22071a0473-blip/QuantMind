import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchMarket, fetchReport, type MarketPoint, type MarketResponse, type Report } from "../lib/api";

function formatNumber(value: number | null | undefined, digits = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function formatPercent(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function PriceChart({ points }: { points: MarketPoint[] }) {
  const values = points.map((point) => point.adjusted_close ?? point.close).filter(Number.isFinite);
  if (values.length < 2) return <div className="empty-chart">No stored OHLCV history for this security.</div>;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const path = values.map((value, index) => {
    const x = (index / (values.length - 1)) * 1000;
    const y = 180 - ((value - min) / range) * 150;
    return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  return (
    <div className="chart-shell">
      <svg viewBox="0 0 1000 200" role="img" aria-label="Historical adjusted close chart">
        <path className="chart-grid" d="M0 30H1000M0 105H1000M0 180H1000" />
        <path className="chart-line" d={path} />
      </svg>
      <div className="chart-axis"><span>{formatNumber(min)}</span><span>{formatNumber(max)}</span></div>
    </div>
  );
}

function Metric({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return <div className="metric"><span>{label}</span><strong className={tone}>{value}</strong></div>;
}

export function StockPage() {
  const { symbol = "PLTR" } = useParams();
  const ticker = symbol.toUpperCase();
  const [report, setReport] = useState<Report | null>(null);
  const [market, setMarket] = useState<MarketResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"overview" | "evidence" | "memory">("overview");

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    Promise.all([fetchReport(ticker, controller.signal), fetchMarket(ticker, controller.signal)])
      .then(([nextReport, nextMarket]) => { setReport(nextReport); setMarket(nextMarket); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Research unavailable"); });
    return () => controller.abort();
  }, [ticker]);

  const latest = useMemo(() => market?.points[market.points.length - 1], [market]);
  const profile = market?.profile;
  if (error) return <section className="terminal-empty"><p className="eyebrow">DATA ERROR</p><h2>{ticker}</h2><p>{error}</p><Link className="button-primary" to="/">Return to workspace</Link></section>;
  if (!report || !market) return <section className="terminal-empty"><p className="eyebrow">LOADING RESEARCH</p><h2>{ticker}</h2><p>Resolving canonical security, market series and evidence…</p></section>;

  return (
    <section className="workspace">
      <div className="crumb"><Link to="/">WORKSPACE</Link><span>/</span><strong>{ticker}</strong><span className="live-dot">● LIVE PROVIDER</span></div>
      <div className="security-head">
        <div><p className="eyebrow">SECURITY MONITOR</p><h1>{ticker}</h1><p className="company-name">{profile?.legal_name ?? report.factor_2_deep_research.company} · {profile?.exchange ?? "MARKET DATA"}</p></div>
        <div className="quote"><strong>{latest ? formatNumber(latest.adjusted_close ?? latest.close) : formatNumber(report.snapshot.price)}</strong><span className={report.snapshot.change_pct >= 0 ? "positive" : "negative"}>{formatPercent(report.snapshot.change_pct)}</span><small>{report.snapshot.history_days} sessions in live provider</small></div>
      </div>
      <div className="tab-bar">{(["overview", "evidence", "memory"] as const).map((item) => <button className={tab === item ? "tab active" : "tab"} key={item} onClick={() => setTab(item)}>{item.toUpperCase()}</button>)}</div>
      {tab === "overview" && <div className="research-grid">
        <article className="panel chart-panel"><div className="panel-head"><span>PRICE / ADJUSTED CLOSE</span><small>{market.available ? `${market.coverage?.bars ?? 0} bars · ${latest?.provider ?? "provider"}` : "UNAVAILABLE"}</small></div><PriceChart points={market.points} /><div className="metrics"><Metric label="LAST" value={latest ? formatNumber(latest.adjusted_close ?? latest.close) : formatNumber(report.snapshot.price)} /><Metric label="DAY MOVE" value={formatPercent(report.snapshot.change_pct)} tone={report.snapshot.change_pct >= 0 ? "positive" : "negative"} /><Metric label="VOLUME RATIO" value={formatNumber(report.snapshot.volume_ratio)} /><Metric label="QUALITY ISSUES" value={formatNumber(market.coverage?.quality_issues, 0)} /></div></article>
        <article className="panel confidence-panel"><div className="panel-head"><span>CONFIDENCE AUDIT</span><small>{report.confidence_meter.regime}</small></div><div className="score-ring"><strong>{report.confidence_meter.score}</strong><span>/ 100</span></div><p>{report.confidence_meter.explanation}</p><div className="coverage-bar"><i style={{ width: `${report.confidence_meter.coverage * 100}%` }} /></div><small>{report.confidence_meter.signals_available}/{report.confidence_meter.signals_total} signals available</small></article>
        <article className="panel"><div className="panel-head"><span>WHY IT MOVED</span><small>RANKED DRIVERS</small></div>{report.factor_1_why_it_moved.map((driver) => <div className="driver" key={driver.category}><div><strong>{driver.category}</strong><small>{Math.round(driver.probability * 100)}% probability</small></div><p>{driver.explanation}</p></div>)}</article>
        <article className="panel"><div className="panel-head"><span>FACTS / REALITY GAP</span><small>SOURCE-BOUND</small></div><div className="fact-block"><span>REPORTED</span><p>{report.factor_5_facts_vs_reality.reported_facts}</p></div><div className="fact-block"><span>MARKET NARRATIVE</span><p>{report.factor_5_facts_vs_reality.market_narrative}</p></div><div className="fact-block"><span>GAP</span><p>{report.factor_5_facts_vs_reality.gap}</p></div></article>
      </div>}
      {tab === "evidence" && <article className="panel evidence-panel"><div className="panel-head"><span>LIVE EVIDENCE</span><small>{report.live_news.length} items</small></div>{report.live_news.length ? report.live_news.map((item) => <a className="evidence-row" href={item.url} target="_blank" rel="noreferrer" key={`${item.url}-${item.published}`}><div><strong>{item.title}</strong><small>{item.publisher} · {item.published}</small></div><p>{item.summary}</p><span>↗</span></a>) : <div className="empty-state">No verified live news was returned for this request.</div>}</article>}
      {tab === "memory" && <article className="panel"><div className="panel-head"><span>HINDSIGHT PRECEDENT</span><small>{report.memory_used.backend}</small></div><div className="memory-stat"><strong>{report.historical_precedent.count}</strong><span>matched prior moves</span></div><p>{report.historical_precedent.narrative}</p><p className="muted">Recalled: {report.memory_used.recalled_count} · Stored: {report.memory_used.total_count}</p></article>}
      {report.warning && <p className="warning-bar">{report.warning}</p>}
      <p className="disclaimer">Research tool, not financial advice. Data availability and timestamps are shown rather than inferred.</p>
    </section>
  );
}
