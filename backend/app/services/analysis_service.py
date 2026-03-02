from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from model_engine import (  # noqa: E402
    HistoricalData,
    ModelAssumptions,
    build_excel_bytes,
    build_research_pack,
    build_sensitivity_table,
    load_historical_data,
    run_dcf,
    run_lbo,
    run_multiple_valuation,
    run_precedent_transactions,
    run_three_statement_model,
    search_companies,
)
from model_engine.runtime_config import clear_api_credentials, set_api_credentials  # noqa: E402

from app.schemas.company import (
    AnalysisRequest,
    AnalysisResponse,
    PeerSummary,
    ResearchSummary,
    ScenarioSummary,
    SearchResult,
    ValuationSummary,
)


def _apply_provider_keys(payload: AnalysisRequest) -> None:
    if payload.provider_keys:
        set_api_credentials(
            ALPHA_VANTAGE_API_KEY=payload.provider_keys.alpha_vantage_api_key,
            FMP_API_KEY=payload.provider_keys.fmp_api_key,
        )
    else:
        clear_api_credentials()


def _base_assumptions(years: int) -> ModelAssumptions:
    return ModelAssumptions(projection_years=years)


def _shift_asm(base: ModelAssumptions, g_shift: float, m_shift: float) -> ModelAssumptions:
    asm = copy.deepcopy(base)
    asm.revenue_growth = [min(max(g + g_shift, -0.05), 0.30) for g in base.revenue_growth]
    asm.gross_margin = [min(max(m + m_shift, 0.03), 0.85) for m in base.gross_margin]
    return asm


def search_for_companies(query: str) -> list[SearchResult]:
    results = search_companies(query)
    return [
        SearchResult(
            symbol=result.symbol,
            name=result.name,
            exchange=result.exchange,
            quote_type=result.quote_type,
            logo_url=result.logo_url,
        )
        for result in results
    ]


def analyze_company(payload: AnalysisRequest) -> AnalysisResponse:
    _apply_provider_keys(payload)
    hist = load_historical_data(payload.ticker)
    base_asm = _base_assumptions(payload.projection_years)
    scenarios = {
        "Base": base_asm,
        "Bull": _shift_asm(base_asm, 0.025, 0.015),
        "Bear": _shift_asm(base_asm, -0.025, -0.02),
    }
    outputs = {name: run_three_statement_model(hist, asm) for name, asm in scenarios.items()}
    research_pack = build_research_pack(hist.ticker, profile=hist.profile) if hist.profile else None
    base_output = outputs["Base"]
    latest_hist = hist.annual().sort_values("year").iloc[-1]
    fcf_series = base_output.fcf["fcf"].tolist()
    ebitda_series = base_output.fcf["ebitda"].tolist()
    shares = max(float(latest_hist.get("shares_outstanding", 1.0)), 1.0)
    net_debt = float(base_output.balance_sheet.iloc[-1]["debt"]) - float(base_output.balance_sheet.iloc[-1]["cash"])
    revenue = float(base_output.income_statement.iloc[-1]["revenue"])
    ebitda = float(base_output.income_statement.iloc[-1]["ebitda"])
    eps = float(base_output.income_statement.iloc[-1]["eps"])

    dcf_result = run_dcf(fcf_series, ebitda_series, 0.09, 0.025, net_debt, shares)
    comps_rev = run_multiple_valuation("Trading EV / Revenue", revenue, 2.0, net_debt, shares, "Revenue")
    comps_ebitda = run_multiple_valuation("Trading EV / EBITDA", ebitda, 9.0, net_debt, shares, "EBITDA")
    comps_pe = run_multiple_valuation("Trading P / E", max(eps, 0.0) * shares, 18.0, 0.0, shares, "Net Income")
    precedents = run_precedent_transactions(revenue, ebitda, net_debt, shares, 2.4, 10.0, 0.25)
    lbo_result = run_lbo(ebitda_series, fcf_series, net_debt, shares, 8.5, 8.0, 4.5, 0.08)

    return AnalysisResponse(
        ticker=hist.ticker,
        company_name=hist.profile.name if hist.profile else None,
        profile=hist.profile.__dict__ if hist.profile else None,
        historical_annual=hist.annual().to_dict(orient="records"),
        historical_quarterly=hist.quarterly().to_dict(orient="records"),
        scenarios={
            name: ScenarioSummary(
                revenue_final_year=float(out.income_statement.iloc[-1]["revenue"]),
                ebitda_final_year=float(out.income_statement.iloc[-1]["ebitda"]),
                net_income_final_year=float(out.income_statement.iloc[-1]["net_income"]),
            )
            for name, out in outputs.items()
        },
        research=ResearchSummary(
            provider=research_pack.provider if research_pack else None,
            peer_count=len(research_pack.peers) if research_pack else 0,
            peers=[
                PeerSummary(
                    symbol=peer.symbol,
                    name=peer.name,
                    ev_revenue=peer.ev_revenue,
                    ev_ebitda=peer.ev_ebitda,
                    pe_ratio=peer.pe_ratio,
                )
                for peer in (research_pack.peers[:8] if research_pack else [])
            ],
            precedent_titles=[item.title for item in (research_pack.precedents[:5] if research_pack else [])],
            analyst_snapshot=research_pack.analyst_snapshot.__dict__ if research_pack and research_pack.analyst_snapshot else None,
        ),
        valuation=ValuationSummary(
            dcf_per_share=dcf_result.value_per_share,
            comps_per_share=float((comps_rev.value_per_share + comps_ebitda.value_per_share + comps_pe.value_per_share) / 3),
            precedents_per_share=float(sum(item.value_per_share for item in precedents) / len(precedents)),
            lbo_per_share=lbo_result.value_per_share,
        ),
    )


def build_export_package(payload: AnalysisRequest) -> tuple[str, bytes]:
    _apply_provider_keys(payload)
    hist = load_historical_data(payload.ticker)
    base_asm = _base_assumptions(payload.projection_years)
    output = run_three_statement_model(hist, base_asm)
    sensitivity = build_sensitivity_table(HistoricalData(ticker=hist.ticker, df=hist.annual(), annual_df=hist.annual()), base_asm)
    research = build_research_pack(hist.ticker, profile=hist.profile) if hist.profile else None
    additional_sheets = {
        "Profile Summary": pd.DataFrame([hist.profile.__dict__]) if hist.profile else pd.DataFrame([{"ticker": hist.ticker}]),
        "Annual Historical": hist.annual(),
        "Quarterly Historical": hist.quarterly(),
        "Assumptions": pd.DataFrame([dataclasses.asdict(base_asm)]),
    }
    if research:
        additional_sheets["Peers"] = pd.DataFrame([peer.__dict__ for peer in research.peers]) if research.peers else pd.DataFrame()
        additional_sheets["Earnings"] = pd.DataFrame([event.__dict__ for event in research.earnings_events]) if research.earnings_events else pd.DataFrame()
        additional_sheets["Precedents"] = pd.DataFrame([item.__dict__ for item in research.precedents]) if research.precedents else pd.DataFrame()
        if research.analyst_snapshot:
            additional_sheets["Analyst Snapshot"] = pd.DataFrame([research.analyst_snapshot.__dict__])

    content = build_excel_bytes(output, sensitivity, hist.annual(), additional_sheets=additional_sheets)
    return f"{hist.ticker.lower().replace('-', '_')}_platform_export.xlsx", content
