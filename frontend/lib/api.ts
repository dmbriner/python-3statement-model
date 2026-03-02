export type SearchResult = {
  symbol: string;
  name: string;
  exchange: string;
  quote_type: string;
  logo_url?: string | null;
};

export type AnalysisResponse = {
  ticker: string;
  company_name?: string | null;
  profile?: Record<string, unknown> | null;
  historical_annual: Record<string, unknown>[];
  historical_quarterly: Record<string, unknown>[];
  scenarios: Record<
    string,
    { revenue_final_year: number; ebitda_final_year: number; net_income_final_year: number }
  >;
  research?: {
    provider?: string | null;
    peer_count: number;
    peers: Array<{
      symbol: string;
      name: string;
      ev_revenue?: number | null;
      ev_ebitda?: number | null;
      pe_ratio?: number | null;
    }>;
    precedent_titles: string[];
    analyst_snapshot?: Record<string, unknown> | null;
  } | null;
  valuation?: {
    dcf_per_share?: number | null;
    comps_per_share?: number | null;
    precedents_per_share?: number | null;
    lbo_per_share?: number | null;
  } | null;
};

export type ApiProfileRecord = {
  id: string;
  name: string;
  provider_keys: Record<string, unknown>;
};

export type SavedAnalysisRecord = {
  id: string;
  ticker: string;
  title: string;
  assumptions: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  notes?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function apiFetch<T>(path: string, init?: RequestInit, token?: string | null): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function searchCompanies(query: string): Promise<SearchResult[]> {
  const payload = await apiFetch<{ results: SearchResult[] }>(`/companies/search?query=${encodeURIComponent(query)}`);
  return payload.results;
}

export async function analyzeTicker(ticker: string): Promise<AnalysisResponse> {
  return apiFetch<AnalysisResponse>("/companies/analyze", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export async function getCurrentUser(token: string): Promise<{ id: string; email?: string | null }> {
  return apiFetch<{ id: string; email?: string | null }>("/auth/me", undefined, token);
}

export async function listApiProfiles(token: string): Promise<ApiProfileRecord[]> {
  return apiFetch<ApiProfileRecord[]>("/me/api-profiles", undefined, token);
}

export async function createApiProfile(token: string, payload: ApiProfileRecord): Promise<ApiProfileRecord> {
  return apiFetch<ApiProfileRecord>("/me/api-profiles", { method: "POST", body: JSON.stringify(payload) }, token);
}

export async function updateApiProfile(token: string, profileId: string, payload: ApiProfileRecord): Promise<ApiProfileRecord> {
  return apiFetch<ApiProfileRecord>(`/me/api-profiles/${profileId}`, { method: "PUT", body: JSON.stringify(payload) }, token);
}

export async function deleteApiProfile(token: string, profileId: string): Promise<{ id: string; deleted: boolean }> {
  return apiFetch<{ id: string; deleted: boolean }>(`/me/api-profiles/${profileId}`, { method: "DELETE" }, token);
}

export async function listSavedAnalyses(token: string): Promise<SavedAnalysisRecord[]> {
  return apiFetch<SavedAnalysisRecord[]>("/me/analyses", undefined, token);
}

export async function createSavedAnalysis(token: string, payload: SavedAnalysisRecord): Promise<SavedAnalysisRecord> {
  return apiFetch<SavedAnalysisRecord>("/me/analyses", { method: "POST", body: JSON.stringify(payload) }, token);
}

export async function updateSavedAnalysis(token: string, analysisId: string, payload: SavedAnalysisRecord): Promise<SavedAnalysisRecord> {
  return apiFetch<SavedAnalysisRecord>(`/me/analyses/${analysisId}`, { method: "PUT", body: JSON.stringify(payload) }, token);
}

export async function deleteSavedAnalysis(token: string, analysisId: string): Promise<{ id: string; deleted: boolean }> {
  return apiFetch<{ id: string; deleted: boolean }>(`/me/analyses/${analysisId}`, { method: "DELETE" }, token);
}

export async function exportWorkbook(ticker: string): Promise<{ fileName: string; contentBase64: string }> {
  const payload = await apiFetch<{ file_name: string; content_base64: string }>("/exports/workbook", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
  return { fileName: payload.file_name, contentBase64: payload.content_base64 };
}
