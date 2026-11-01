export type Asset = {
  symbol: string;
  name: string;
  kind: "stock" | "etf" | "crypto";
  sector?: string;
  industry?: string;
  in_sp100: boolean;
  memory_event_count: number;
};

export type SearchResponse = { results: Asset[]; total: number };

export type ParsedQuery = {
  query: string;
  intent: string;
  symbols: string[];
  metrics: string[];
  retrieval_strategy: string[];
  clarification: string | null;
};

export type Report = {
  asset: string;
  generated_at: string;
  snapshot: {
    asset: string;
    kind: "stock" | "crypto";
    price: number;
    change_pct: number;
    volume_ratio?: number | null;
    history_days: number;
  };
  confidence_meter: {
    score: number;
    coverage: number;
    signals_available: number;
    signals_total: number;
    regime: string;
    explanation: string;
  };
  factor_1_why_it_moved: Array<{ category: string; probability: number; explanation: string }>;
  factor_2_deep_research: { company: string; sector: string; macro: string; news: string };
  factor_5_facts_vs_reality: { reported_facts: string; market_narrative: string; gap: string };
  historical_precedent: { count: number; narrative: string; average_follow_through: number | null };
  memory_used: { recalled_count: number; total_count: number; backend: string };
  live_news: Array<{ title: string; publisher: string; published: string; url: string; summary: string }>;
  warning?: string | null;
};

export type MarketPoint = {
  observed_at: string;
  open: number;
  high: number;
  low: number;
  close: number;
  adjusted_close?: number | null;
  volume?: number | null;
  provider: string;
};

export type MarketResponse = {
  ticker: string;
  available: boolean;
  reason?: string;
  profile?: { legal_name: string; exchange?: string; sector?: string; industry?: string; currency: string } | null;
  coverage?: { bars: number; first_observation?: string; latest_observation?: string; quality_issues: number };
  points: MarketPoint[];
};

export type PrecedentRow = {
  event_id: string;
  ticker: string;
  event_date: string;
  event_type: string;
  headline: string;
  source_url: string | null;
  similarity?: number;
  feature_scores?: Record<string, number>;
  retrieval_source?: "structured" | "semantic" | "both";
  relaxation_level?: string;
  forward_returns: Record<string, number | null>;
};

export type PrecedentResponse = {
  ticker: string;
  cutoff: string;
  status: "ok" | "no_event" | "insufficient_analogues";
  detected_event: PrecedentRow | null;
  matches?: PrecedentRow[];
  distributions?: Record<string, {
    n: number;
    insufficient_analogues: boolean;
    median?: number | null;
    mean?: number | null;
    iqr?: number | null;
    hit_rate?: number | null;
    interval_90?: { lower: number; upper: number } | null;
    forecast_probability?: number | null;
    base_rate_scope?: string | null;
  }>;
  relaxation_level?: string;
  semantic_status?: string;
};

export type HealthResponse = {
  status: string;
  database: string;
  memory: string;
  llm: string;
  universe_size: number;
};

export type Hypothesis = {
  id: string;
  ticker: string;
  created_at: string;
  information_cutoff: string;
  provenance: "live_forward" | "historical_replay";
  claim_text: string;
  direction: "outperform" | "underperform";
  horizon_days: 5 | 20 | 60;
  predicted_probability: number;
  status: "open" | "resolved" | "censored" | "invalidated";
  status_reason?: string | null;
  resolve_after: string;
};

export type LedgerItem = {
  hypothesis: Hypothesis;
  resolution: {
    realized_abnormal_return: number;
    outcome: number;
    brier: number;
    log_loss: number;
  } | null;
  verified: boolean;
};

export type TimeMachineCandidate = {
  ticker: string;
  as_of: string;
  information_cutoff: string;
  event_id: string;
  event_type: string;
  headline: string;
  available_at: string;
  history_days: number;
};

export type TimeMachineMatch = {
  event_id: string;
  ticker: string;
  event_date: string;
  event_type: string;
  headline: string;
  source_url: string;
  similarity: number;
  feature_scores: Record<string, number | null>;
  retrieval_source: string;
  relaxation_level: string;
  forward_returns: Record<string, number | null>;
};

export type TimeMachineForecast = {
  ticker: string;
  as_of: string;
  information_cutoff: string;
  event: { event_type: string; headline?: string | null; source_url?: string | null };
  matches: TimeMachineMatch[];
  distributions: Record<string, {
    n: number;
    insufficient_analogues: boolean;
    median?: number | null;
    mean?: number | null;
    iqr?: number | null;
    hit_rate?: number | null;
    interval_90?: { lower: number; upper: number } | null;
    forecast_probability?: number | null;
    base_rate_scope?: string | null;
  }>;
  relaxation_level: string;
  insufficient_analogues: boolean;
  hypothesis_id?: string | null;
  provenance: "historical_replay";
};

export type TimeMachineReveal = {
  hypothesis_id: string;
  revealed: boolean;
  resolve_after: string;
  status: string;
  status_reason?: string | null;
  resolution?: { realized_abnormal_return: number; outcome: number; end_price_date: string } | null;
};

export async function searchAssets(query: string, signal: AbortSignal): Promise<SearchResponse> {
  const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal });
  if (!response.ok) throw new Error(`Search failed (${response.status})`);
  return response.json() as Promise<SearchResponse>;
}

export async function understandQuery(query: string, signal?: AbortSignal): Promise<ParsedQuery> {
  const response = await fetch(`/api/query?q=${encodeURIComponent(query)}`, { signal });
  if (!response.ok) throw new Error(`Query routing failed (${response.status})`);
  return response.json() as Promise<ParsedQuery>;
}

export async function fetchReport(ticker: string, signal: AbortSignal): Promise<Report> {
  const response = await fetch(`/api/report/${encodeURIComponent(ticker)}`, { signal });
  if (!response.ok) throw new Error(`Research report unavailable (${response.status})`);
  return response.json() as Promise<Report>;
}

export async function fetchMarket(ticker: string, signal: AbortSignal): Promise<MarketResponse> {
  const response = await fetch(`/api/market/${encodeURIComponent(ticker)}?limit=500`, { signal });
  if (!response.ok) throw new Error(`Market series unavailable (${response.status})`);
  return response.json() as Promise<MarketResponse>;
}

export async function fetchPrecedent(ticker: string, signal: AbortSignal): Promise<PrecedentResponse> {
  const response = await fetch(`/api/precedent/${encodeURIComponent(ticker)}`, { signal });
  if (!response.ok) throw new Error(`Precedent unavailable (${response.status})`);
  return response.json() as Promise<PrecedentResponse>;
}

export async function fetchHealth(signal: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/health", { signal });
  if (!response.ok) throw new Error(`Dependency health unavailable (${response.status})`);
  return response.json() as Promise<HealthResponse>;
}

export async function fetchLedger(ticker: string, signal: AbortSignal): Promise<LedgerItem[]> {
  const response = await fetch(`/api/ledger?ticker=${encodeURIComponent(ticker)}&limit=50`, { signal });
  if (!response.ok) throw new Error(`Ledger unavailable (${response.status})`);
  const payload = await response.json() as { items: Hypothesis[]; total: number; limit: number; next_cursor?: string | null };
  const items = await Promise.all(payload.items.map(async (hypothesis) => {
    const detail = await fetch(`/api/ledger/${hypothesis.id}`, { signal });
    if (!detail.ok) throw new Error(`Ledger detail unavailable (${detail.status})`);
    return detail.json() as Promise<LedgerItem>;
  }));
  return items;
}

export async function commitForecast(
  ticker: string,
  horizonDays: 5 | 20 | 60,
  signal: AbortSignal,
): Promise<Hypothesis> {
  const response = await fetch("/api/ledger/commit", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ ticker, horizon_days: horizonDays }),
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Forecast commit failed (${response.status})`);
  }
  return response.json() as Promise<Hypothesis>;
}

export async function fetchTimeMachineCandidates(
  ticker: string,
  signal: AbortSignal,
): Promise<{ items: TimeMachineCandidate[]; total: number; limit: number; offset: number }> {
  const response = await fetch(`/api/timemachine/candidates?ticker=${encodeURIComponent(ticker)}&limit=100`, { signal });
  if (!response.ok) throw new Error(`Time Machine candidates unavailable (${response.status})`);
  return response.json() as Promise<{ items: TimeMachineCandidate[]; total: number; limit: number; offset: number }>;
}

export async function createTimeMachineForecast(
  ticker: string,
  asOf: string,
  horizonDays: 5 | 20 | 60,
  signal: AbortSignal,
): Promise<TimeMachineForecast> {
  const response = await fetch("/api/timemachine/forecast", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ ticker, as_of: asOf, horizon_days: horizonDays }),
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Historical forecast unavailable (${response.status})`);
  }
  return response.json() as Promise<TimeMachineForecast>;
}

export async function revealTimeMachineForecast(
  hypothesisId: string,
  signal: AbortSignal,
): Promise<TimeMachineReveal> {
  const response = await fetch("/api/timemachine/reveal", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ hypothesis_id: hypothesisId }),
    signal,
  });
  if (!response.ok) throw new Error(`Historical outcome unavailable (${response.status})`);
  return response.json() as Promise<TimeMachineReveal>;
}
