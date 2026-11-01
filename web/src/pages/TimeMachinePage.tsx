import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  createTimeMachineForecast,
  fetchTimeMachineCandidates,
  revealTimeMachineForecast,
  type TimeMachineCandidate,
  type TimeMachineForecast,
  type TimeMachineReveal,
} from "../lib/api";

function formatPercent(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function TimeMachinePage() {
  const [searchParams] = useSearchParams();
  const [ticker, setTicker] = useState(searchParams.get("symbol")?.toUpperCase() ?? "CRM");
  const [candidates, setCandidates] = useState<TimeMachineCandidate[]>([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [horizon, setHorizon] = useState<5 | 20 | 60>(20);
  const [forecast, setForecast] = useState<TimeMachineForecast | null>(null);
  const [reveal, setReveal] = useState<TimeMachineReveal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    fetchTimeMachineCandidates(ticker, controller.signal)
      .then((response) => {
        setCandidates(response.items);
        setSelectedDate(response.items[0]?.as_of ?? "");
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Candidates unavailable");
      });
    return () => controller.abort();
  }, [ticker]);

  const selectedCandidate = useMemo(
    () => candidates.find((candidate) => candidate.as_of === selectedDate),
    [candidates, selectedDate],
  );

  const runForecast = () => {
    if (!selectedDate) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setReveal(null);
    createTimeMachineForecast(ticker, selectedDate, horizon, controller.signal)
      .then(setForecast)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Historical forecast unavailable"))
      .finally(() => setLoading(false));
  };

  const revealForecast = () => {
    if (!forecast?.hypothesis_id) return;
    const controller = new AbortController();
    revealTimeMachineForecast(forecast.hypothesis_id, controller.signal)
      .then(setReveal)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Historical outcome unavailable"));
  };

  return (
    <section className="workspace">
      <div className="crumb"><Link to="/">WORKSPACE</Link><span>/</span><strong>TIME MACHINE</strong></div>
      <div className="security-head">
        <div><p className="eyebrow">POINT-IN-TIME REPLAY</p><h1>TIME MACHINE</h1><p className="company-name">Forecast from the past. Outcomes stay sealed until reveal.</p></div>
        <div className="quote"><strong>OFFLINE</strong><span className="positive">NO LIVE NEWS</span><small>Structured corpus only</small></div>
      </div>
      <article className="panel">
        <div className="panel-head"><span>REPLAY CONTROLS</span><small>INFORMATION CUTOFF = AFTER CLOSE</small></div>
        <div className="metrics">
          <label className="metric"><span>TICKER</span><input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} maxLength={12} /></label>
          <label className="metric"><span>AS-OF DATE</span><select value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)}><option value="">Select a dated event</option>{candidates.map((candidate) => <option key={candidate.event_id} value={candidate.as_of}>{candidate.as_of} · {candidate.event_type}</option>)}</select></label>
          <label className="metric"><span>HORIZON</span><select value={horizon} onChange={(event) => setHorizon(Number(event.target.value) as 5 | 20 | 60)}><option value={5}>5 trading days</option><option value={20}>20 trading days</option><option value={60}>60 trading days</option></select></label>
          <button className="button-primary" onClick={runForecast} disabled={loading || !selectedDate}>{loading ? "REPLAYING…" : "RUN REPLAY"}</button>
        </div>
        {selectedCandidate && <p className="disclaimer">Visible history: {selectedCandidate.history_days} prior sessions · source available {selectedCandidate.available_at.slice(0, 16).replace("T", " ")} UTC · no post-cutoff outcomes are sent.</p>}
        {error && <p className="warning-bar">{error}</p>}
      </article>
      {forecast && <article className="panel">
        <div className="panel-head"><span>HISTORICAL FORECAST</span><small>{forecast.as_of} · {forecast.relaxation_level} · {forecast.provenance}</small></div>
        <div className="fact-block"><span>EVENT</span><p>{forecast.event.event_type} — {forecast.event.headline}</p></div>
        <div className="distribution-grid">{Object.entries(forecast.distributions).map(([name, distribution]) => <div className="distribution" key={name}><strong>{name.replace("fwd_", "").toUpperCase()}</strong><span>n={distribution.n}</span><span>median {formatPercent(distribution.median)}</span><span>hit {formatPercent(distribution.hit_rate == null ? null : distribution.hit_rate * 100)}</span><span>probability {distribution.forecast_probability == null ? "—" : `${Math.round(distribution.forecast_probability * 100)}%`}</span></div>)}</div>
        {forecast.insufficient_analogues && <div className="empty-state">Insufficient elapsed analogues. QuantMind refuses to manufacture a numeric forecast.</div>}
        {!forecast.insufficient_analogues && <><div className="panel-head"><span>ANALOGUE EVIDENCE</span><small>{forecast.matches.length} matches</small></div><div className="analogue-table"><div className="analogue-row analogue-head"><span>DATE / TICKER</span><span>TYPE</span><span>SIMILARITY</span><span>5D</span><span>20D</span><span>60D</span></div>{forecast.matches.map((match) => <div className="analogue-row" key={match.event_id}><span>{match.event_date} · {match.ticker}</span><span>{match.event_type}</span><span>{Math.round(match.similarity * 100)}%</span><span>{formatPercent(match.forward_returns.fwd_5d)}</span><span>{formatPercent(match.forward_returns.fwd_20d)}</span><span>{formatPercent(match.forward_returns.fwd_60d)}</span></div>)}</div></>}
        {forecast.hypothesis_id && <button className="button-primary" onClick={revealForecast}>REVEAL REALIZED OUTCOME</button>}
        {reveal && <div className="fact-block"><span>{reveal.revealed ? "REALIZED OUTCOME" : "OUTCOME SEALED"}</span><p>{reveal.revealed && reveal.resolution ? `${formatPercent(reveal.resolution.realized_abnormal_return * 100)} abnormal return · ${reveal.resolution.end_price_date}` : reveal.status_reason ?? `Available after ${reveal.resolve_after}`}</p></div>}
      </article>}
    </section>
  );
}
