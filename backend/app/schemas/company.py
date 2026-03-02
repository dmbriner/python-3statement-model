from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderKeys(BaseModel):
    alpha_vantage_api_key: str | None = None
    fmp_api_key: str | None = None


class AnalysisRequest(BaseModel):
    ticker: str = Field(min_length=1)
    projection_years: int = Field(default=5, ge=1, le=10)
    provider_keys: ProviderKeys | None = None


class SearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str = ""
    quote_type: str = ""
    logo_url: str | None = None


class CompanySearchResponse(BaseModel):
    results: list[SearchResult]


class ScenarioSummary(BaseModel):
    revenue_final_year: float
    ebitda_final_year: float
    net_income_final_year: float


class PeerSummary(BaseModel):
    symbol: str
    name: str
    ev_revenue: float | None = None
    ev_ebitda: float | None = None
    pe_ratio: float | None = None


class ResearchSummary(BaseModel):
    provider: str | None = None
    peer_count: int = 0
    peers: list[PeerSummary] = []
    precedent_titles: list[str] = []
    analyst_snapshot: dict | None = None


class ValuationSummary(BaseModel):
    dcf_per_share: float | None = None
    comps_per_share: float | None = None
    precedents_per_share: float | None = None
    lbo_per_share: float | None = None


class AnalysisResponse(BaseModel):
    ticker: str
    company_name: str | None = None
    profile: dict | None = None
    historical_annual: list[dict]
    historical_quarterly: list[dict]
    scenarios: dict[str, ScenarioSummary]
    research: ResearchSummary | None = None
    valuation: ValuationSummary | None = None


class ExportResponse(BaseModel):
    file_name: str
    content_base64: str
