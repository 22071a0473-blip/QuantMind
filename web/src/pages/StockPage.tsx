import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { commitForecast, fetchHealth, fetchLedger, fetchMarket, fetchPrecedent, fetchReport, type HealthResponse, type Hypothesis, type LedgerItem, type MarketPoint, type MarketResponse, type PrecedentResponse, type Report } from "../lib/api";

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

function LedgerPanel({ ticker }: { ticker: string }) {
  const [items, setItems] = useState<LedgerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = (signal: AbortSignal) => {
    setLoading(true);
    fetchLedger(ticker, signal)
      .then(setItems)
      .catch((reason: unknown) => { if (!signal.aborted) setError(reason instanceof Error ? reason.message : "Ledger unavailable"); })
      .finally(() => { if (!signal.aborted) setLoading(false); });
  };

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [ticker]);

  const commit = () => {
    const controller = new AbortController();
    setCommitting(true);
    setError(null);
    commitForecast(ticker, 20, controller.signal)
      .then((hypothesis: Hypothesis) => setItems((current) => [
        { hypothesis, resolution: null, verified: true }, ...current.filter((item) => item.hypothesis.id !== hypothesis.id),
      ]))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Forecast commit failed"))
      .finally(() => setCommitting(false));
  };

  if (loading) return <article className="panel"><div className="panel-head"><span>HYPOTHESIS LEDGER</span></div><p>Loading dated forecasts…</p></article>;
  return <article className="panel ledger-panel">
    <div className="panel-head"><span>HYPOTHESIS LEDGER</span><button className="button-primary" onClick={commit} disabled={committing}>{committing ? "COMMITTING…" : "COMMIT FORECAST"}</button></div>
    {error && <p className="warning-bar">{error}</p>}
    {!items.length && !error && <div className="empty-state">The ledger stores falsifiable, dated forecasts. Commit the first forecast when enough history is available.</div>}
    {items.length > 0 && <div className="ledger-table"><div className="ledger-row ledger-head"><span>CREATED</span><span>CLAIM</span><span>HORIZON</span><span>PROBABILITY</span><span>STATUS</span><span>PROVENANCE</span></div>{items.map((item) => <div className="ledger-row" key={item.hypothesis.id}><span>{item.hypothesis.created_at.slice(0, 10)}</span><span>{item.hypothesis.claim_text}</span><span>{item.hypothesis.horizon_days}D</span><span>{Math.round(item.hypothesis.predicted_probability * 100)}%</span><span>{item.hypothesis.status}{item.resolution ? ` · ${item.resolution.realized_abnormal_return >= 0 ? "+" : ""}${(item.resolution.realized_abnormal_return * 100).toFixed(2)}%` : ""}</span><span>{item.hypothesis.provenance} {item.verified ? "✓" : "!"}</span></div>)}</div>}
  </article>;
}

function PrecedentPanel({ ticker }: { ticker: string }) {
  const [data, setData] = useState<PrecedentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchPrecedent(ticker, controller.signal).then(setData).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Precedent unavailable");
    });
    return () => controller.abort();
  }, [ticker]);
  if (error) return <article className="panel"><div className="panel-head"><span>PRECEDENT</span></div><p className="warning-bar">{error}</p></article>;
  if (!data) return <article className="panel"><div className="panel-head"><span>PRECEDENT</span></div><p>Loading analogue evidence…</p></article>;
  if (data.status === "no_event" || !data.detected_event) return <article className="panel"><div className="panel-head"><span>PRECEDENT</span></div><div className="empty-state">No qualifying event detected before the cutoff.</div></article>;
  return <article className="panel precedent-panel">
    <div className="panel-head"><span>PRECEDENT</span><small>{data.relaxation_level} · {data.semantic_status}</small></div>
    <div className="precedent-event"><strong>{data.detected_event.event_type}</strong><span>{data.detected_event.event_date}</span><a href={data.detected_event.source_url ?? undefined} target="_blank" rel="noreferrer">{data.detected_event.headline} ↗</a></div>
    {data.status === "insufficient_analogues" ? <div className="empty-state">Insufficient elapsed analogues. No numeric forecast is shown.</div> : <><div className="analogue-table"><div className="analogue-row analogue-head"><span>DATE / TICKER</span><span>TYPE</span><span>SIMILARITY</span><span>5D</span><span>20D</span><span>60D</span></div>{(data.matches ?? []).map((match) => <div className="analogue-row" key={match.event_id}><span>{match.event_date} · {match.ticker}</span><span>{match.event_type}<small>{match.retrieval_source}</small></span><span>{match.similarity == null ? "n/a" : `${(match.similarity * 100).toFixed(0)}%`}</span><span>{formatPercent(match.forward_returns.fwd_5d)}</span><span>{formatPercent(match.forward_returns.fwd_20d)}</span><span>{formatPercent(match.forward_returns.fwd_60d)}</span></div>)}</div><div className="distribution-grid">{Object.entries(data.distributions ?? {}).map(([horizon, distribution]) => <div className="distribution" key={horizon}><strong>{horizon.replace("fwd_", "").toUpperCase()}</strong><span>n={distribution.n}</span><span>median {formatPercent(distribution.median)}</span><span>IQR {formatPercent(distribution.iqr)}</span><span>hit {formatPercent(distribution.hit_rate == null ? null : distribution.hit_rate * 100)}</span></div>)}</div></>}
  </article>;
}

export function StockPage() {
  const { symbol = "PLTR" } = useParams();
  const ticker = symbol.toUpperCase();
  const [report, setReport] = useState<Report | null>(null);
  const [market, setMarket] = useState<MarketResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"overview" | "evidence" | "precedent" | "ledger">("overview");

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    Promise.all([fetchReport(ticker, controller.signal), fetchMarket(ticker, controller.signal), fetchHealth(controller.signal)])
      .then(([nextReport, nextMarket, nextHealth]) => { setReport(nextReport); setMarket(nextMarket); setHealth(nextHealth); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Research unavailable"); });
    return () => controller.abort();
  }, [ticker]);

  const latest = useMemo(() => market?.points[market.points.length - 1], [market]);
  const profile = market?.profile;
  if (error) return <section className="terminal-empty"><p className="eyebrow">DATA ERROR</p><h2>{ticker}</h2><p>{error}</p><Link className="button-primary" to="/">Return to workspace</Link></section>;
  if (!report || !market) return <section className="terminal-empty"><p className="eyebrow">LOADING RESEARCH</p><h2>{ticker}</h2><p>Resolving canonical security, market series and evidence…</p></section>;

  return (
    <section className="workspace">
      <div className="crumb"><Link to="/">WORKSPACE</Link><span>/</span><strong>{ticker}</strong><span className="live-dot">● {health?.database === "ok" ? "LIVE DATA" : "DATA DEGRADED"}</span></div>
      <div className="security-head">
        <div><p className="eyebrow">SECURITY MONITOR</p><h1>{ticker}</h1><p className="company-name">{profile?.legal_name ?? report.factor_2_deep_research.company} · {profile?.exchange ?? "MARKET DATA"}</p></div>
        <div className="quote"><strong>{latest ? formatNumber(latest.adjusted_close ?? latest.close) : formatNumber(report.snapshot.price)}</strong><span className={report.snapshot.change_pct >= 0 ? "positive" : "negative"}>{formatPercent(report.snapshot.change_pct)}</span><small>{report.snapshot.history_days} sessions in live provider</small></div>
      </div>
      <div className="tab-bar">{(["overview", "evidence", "precedent", "ledger"] as const).map((item) => <button className={tab === item ? "tab active" : "tab"} key={item} onClick={() => setTab(item)}>{item.toUpperCase()}</button>)}</div>
      {tab === "overview" && <div className="research-grid">
        <article className="panel chart-panel"><div className="panel-head"><span>PRICE / ADJUSTED CLOSE</span><small>{market.available ? `${market.coverage?.bars ?? 0} bars · ${latest?.provider ?? "provider"}` : "UNAVAILABLE"}</small></div><PriceChart points={market.points} /><div className="metrics"><Metric label="LAST" value={latest ? formatNumber(latest.adjusted_close ?? latest.close) : formatNumber(report.snapshot.price)} /><Metric label="DAY MOVE" value={formatPercent(report.snapshot.change_pct)} tone={report.snapshot.change_pct >= 0 ? "positive" : "negative"} /><Metric label="VOLUME RATIO" value={formatNumber(report.snapshot.volume_ratio)} /><Metric label="QUALITY ISSUES" value={formatNumber(market.coverage?.quality_issues, 0)} /></div></article>
        <article className="panel confidence-panel"><div className="panel-head"><span>CONFIDENCE AUDIT</span><small>{report.confidence_meter.regime}</small></div><div className="score-ring"><strong>{report.confidence_meter.score}</strong><span>/ 100</span></div><p>{report.confidence_meter.explanation}</p><div className="coverage-bar"><i style={{ width: `${report.confidence_meter.coverage * 100}%` }} /></div><small>{report.confidence_meter.signals_available}/{report.confidence_meter.signals_total} signals available</small></article>
        <article className="panel"><div className="panel-head"><span>WHY IT MOVED</span><small>RANKED DRIVERS</small></div>{report.factor_1_why_it_moved.map((driver) => <div className="driver" key={driver.category}><div><strong>{driver.category}</strong><small>{Math.round(driver.probability * 100)}% probability</small></div><p>{driver.explanation}</p></div>)}</article>
        <article className="panel"><div className="panel-head"><span>FACTS / REALITY GAP</span><small>SOURCE-BOUND</small></div><div className="fact-block"><span>REPORTED</span><p>{report.factor_5_facts_vs_reality.reported_facts}</p></div><div className="fact-block"><span>MARKET NARRATIVE</span><p>{report.factor_5_facts_vs_reality.market_narrative}</p></div><div className="fact-block"><span>GAP</span><p>{report.factor_5_facts_vs_reality.gap}</p></div></article>
      </div>}
      {tab === "evidence" && <article className="panel evidence-panel"><div className="panel-head"><span>LIVE EVIDENCE</span><small>{report.live_news.length} items</small></div>{report.live_news.length ? report.live_news.map((item) => <a className="evidence-row" href={item.url} target="_blank" rel="noreferrer" key={`${item.url}-${item.published}`}><div><strong>{item.title}</strong><small>{item.publisher} · {item.published}</small></div><p>{item.summary}</p><span>↗</span></a>) : <div className="empty-state">No verified live news was returned for this request.</div>}</article>}
      {tab === "precedent" && <PrecedentPanel ticker={ticker} />}
      {tab === "ledger" && <LedgerPanel ticker={ticker} />}
      {report.warning && <p className="warning-bar">{report.warning}</p>}
      <p className="disclaimer">Research tool, not financial advice. Data availability and timestamps are shown rather than inferred.</p>
    </section>
  );
}
