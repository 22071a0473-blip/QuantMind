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

export async function searchAssets(query: string, signal: AbortSignal): Promise<SearchResponse> {
  const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal });
  if (!response.ok) throw new Error(`Search failed (${response.status})`);
  return response.json() as Promise<SearchResponse>;
}
