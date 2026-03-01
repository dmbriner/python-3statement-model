"""Historical financial metrics analyzer and smart assumption suggestion engine."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field

from .config import ModelAssumptions
from .data import HistoricalData


@dataclass
class HistoricalMetrics:
    # Growth
    revenue_growth_cagr: float
    revenue_growth_yoy: list[float]
    revenue_growth_avg: float
    # Margins
    gross_margin_avg: float
    gross_margin_trend: float          # pp/year (positive = expanding)
    opex_pct_avg: float
    ebitda_margin_avg: float
    ebit_margin_avg: float
    net_margin_avg: float
    # Working capital (days)
    dso_avg: float
    dio_avg: float
    dpo_avg: float
    # Capital intensity
    capex_pct_avg: float
    depreciation_pct_ppne_avg: float
    # Financing
    tax_rate_avg: float
    interest_rate_avg: float
    dividend_payout_avg: float
    # Debt
    net_debt_avg: float
    net_leverage_avg: float            # Net Debt / EBITDA
    interest_coverage_avg: float       # EBIT / Interest
    # Human-readable notes
    growth_note: str = ""
    margin_note: str = ""
    capex_note: str = ""
    wc_note: str = ""
    financing_note: str = ""


def analyze_historical_data(hist: HistoricalData) -> HistoricalMetrics:
    """Extract all key financial metrics from historical data."""
    df = hist.df.copy().sort_values("year").reset_index(drop=True)
    n = len(df)

    # --- Revenue growth ---
    revenues = df["revenue"].tolist()
    yoy_growth = []
    for i in range(1, n):
        if revenues[i - 1] > 0:
            yoy_growth.append((revenues[i] - revenues[i - 1]) / revenues[i - 1])
    cagr = (revenues[-1] / revenues[0]) ** (1 / max(n - 1, 1)) - 1 if revenues[0] > 0 else 0.03
    growth_avg = float(np.mean(yoy_growth)) if yoy_growth else cagr
    recent_growth = float(np.mean(yoy_growth[-3:])) if len(yoy_growth) >= 3 else growth_avg

    # --- Margins ---
    df["gross_margin"] = (df["revenue"] - df["cogs"]) / df["revenue"]
    df["ebitda"] = df["revenue"] - df["cogs"] - df["opex"]
    df["ebit"] = df["ebitda"] - df["depreciation"]
    df["ebitda_margin"] = df["ebitda"] / df["revenue"]
    df["ebit_margin"] = df["ebit"] / df["revenue"]
    df["opex_pct"] = df["opex"] / df["revenue"]

    gross_margin_avg = float(df["gross_margin"].mean())
    # Trend: slope of gross margin over time (simple linear)
    if n >= 2:
        x = np.arange(n, dtype=float)
        y = df["gross_margin"].values
        slope = float(np.polyfit(x, y, 1)[0])  # pp per year
    else:
        slope = 0.0

    # Estimate net income from ebit (use tax rate avg for NI proxy)
    tax_rate_avg = float(df["tax_rate"].mean())
    df["net_income_proxy"] = df["ebit"].apply(lambda v: max(v, 0)) * (1 - tax_rate_avg) - df["interest_expense"]
    df["net_margin_proxy"] = df["net_income_proxy"] / df["revenue"]

    ebitda_margin_avg = float(df["ebitda_margin"].mean())
    ebit_margin_avg = float(df["ebit_margin"].mean())
    net_margin_avg = float(df["net_margin_proxy"].mean())
    opex_pct_avg = float(df["opex_pct"].mean())

    # --- Working capital days ---
    df["dso"] = (df["accounts_receivable"] / df["revenue"]) * 365
    df["dio"] = (df["inventory"] / df["cogs"].replace(0, np.nan)) * 365
    df["dpo"] = (df["accounts_payable"] / df["cogs"].replace(0, np.nan)) * 365
    dso_avg = float(df["dso"].mean())
    dio_avg = float(df["dio"].fillna(0).mean())
    dpo_avg = float(df["dpo"].fillna(0).mean())

    # --- CapEx ---
    df["capex_pct"] = df["capex"] / df["revenue"]
    capex_pct_avg = float(df["capex_pct"].mean())

    # --- Depreciation ---
    df["dep_pct_ppne"] = df["depreciation"] / df["ppne"].replace(0, np.nan)
    dep_pct_avg = float(df["dep_pct_ppne"].dropna().mean())
    if np.isnan(dep_pct_avg):
        dep_pct_avg = 0.12

    # --- Financing ---
    df["avg_debt"] = (df["debt"] + df["debt"].shift(1)).fillna(df["debt"] * 2) / 2
    df["interest_rate"] = df["interest_expense"] / df["avg_debt"].replace(0, np.nan)
    interest_rate_avg = float(df["interest_rate"].dropna().mean())
    if np.isnan(interest_rate_avg) or interest_rate_avg <= 0:
        interest_rate_avg = 0.05

    # Dividend payout — if no explicit dividend data, estimate from payout ratio assumption
    # Use a reasonable default; actual payout = dividends / NI. We don't have dividends separately.
    div_payout_avg = 0.30  # conservative default

    # --- Leverage / coverage ---
    df["net_debt"] = df["debt"] - df["cash"]
    df["net_leverage"] = df["net_debt"] / df["ebitda"].replace(0, np.nan)
    df["interest_coverage"] = df["ebit"] / df["interest_expense"].replace(0, np.nan)
    net_debt_avg = float(df["net_debt"].mean())
    net_leverage_avg = float(df["net_leverage"].dropna().mean())
    interest_coverage_avg = float(df["interest_coverage"].dropna().mean())

    # --- Notes ---
    trend_word = "expanding" if slope > 0.001 else ("compressing" if slope < -0.001 else "stable")
    growth_note = (
        f"Trailing revenue CAGR: {cagr * 100:.1f}%. "
        f"Recent 3yr avg growth: {recent_growth * 100:.1f}%. "
        f"{'Accelerating' if len(yoy_growth) >= 2 and yoy_growth[-1] > yoy_growth[-2] else 'Decelerating'} trend."
    )
    margin_note = (
        f"Avg gross margin: {gross_margin_avg * 100:.1f}% ({trend_word}, {slope * 100:+.2f}pp/yr). "
        f"Avg EBITDA margin: {ebitda_margin_avg * 100:.1f}%."
    )
    capex_note = (
        f"Avg capex: {capex_pct_avg * 100:.1f}% of revenue. "
        f"D&A: {dep_pct_avg * 100:.1f}% of PP&E annually."
    )
    wc_note = (
        f"DSO {dso_avg:.0f} days | DIO {dio_avg:.0f} days | DPO {dpo_avg:.0f} days. "
        f"Cash conversion cycle: {dso_avg + dio_avg - dpo_avg:.0f} days."
    )
    financing_note = (
        f"Avg interest rate: {interest_rate_avg * 100:.1f}% on debt. "
        f"Net leverage: {net_leverage_avg:.1f}x EBITDA. "
        f"Interest coverage: {interest_coverage_avg:.1f}x."
    )

    return HistoricalMetrics(
        revenue_growth_cagr=cagr,
        revenue_growth_yoy=yoy_growth,
        revenue_growth_avg=growth_avg,
        gross_margin_avg=gross_margin_avg,
        gross_margin_trend=slope,
        opex_pct_avg=opex_pct_avg,
        ebitda_margin_avg=ebitda_margin_avg,
        ebit_margin_avg=ebit_margin_avg,
        net_margin_avg=net_margin_avg,
        dso_avg=dso_avg,
        dio_avg=dio_avg,
        dpo_avg=dpo_avg,
        capex_pct_avg=capex_pct_avg,
        depreciation_pct_ppne_avg=dep_pct_avg,
        tax_rate_avg=tax_rate_avg,
        interest_rate_avg=interest_rate_avg,
        dividend_payout_avg=div_payout_avg,
        net_debt_avg=net_debt_avg,
        net_leverage_avg=net_leverage_avg if not np.isnan(net_leverage_avg) else 0.0,
        interest_coverage_avg=interest_coverage_avg if not np.isnan(interest_coverage_avg) else 5.0,
        growth_note=growth_note,
        margin_note=margin_note,
        capex_note=capex_note,
        wc_note=wc_note,
        financing_note=financing_note,
    )


def suggest_scenarios(metrics: HistoricalMetrics, years: int = 5) -> dict[str, ModelAssumptions]:
    """
    Generate Base / Bull / Bear ModelAssumptions from historical metrics.

    Base: trailing averages with gentle mean-reversion toward long-run norms.
    Bull: Base + ~2pp revenue growth, +1.5pp margin expansion.
    Bear: Base − ~2pp revenue growth, −1.5pp margin compression.
    """
    # Base revenue growth: blend recent growth toward long-run norm
    base_growth_start = min(max(metrics.revenue_growth_avg, -0.05), 0.15)
    base_growth_end = min(max(base_growth_start * 0.7, 0.01), 0.08)
    base_growth = _interpolate(base_growth_start, base_growth_end, years)

    bull_growth = [min(g + 0.025, 0.20) for g in base_growth]
    bear_growth = [max(g - 0.025, -0.03) for g in base_growth]

    # Gross margin
    gm_start = metrics.gross_margin_avg
    gm_trend_per_year = min(max(metrics.gross_margin_trend, -0.005), 0.005)
    base_gm = [min(max(gm_start + gm_trend_per_year * i, 0.05), 0.70) for i in range(years)]
    bull_gm = [min(g + 0.015, 0.75) for g in base_gm]
    bear_gm = [max(g - 0.020, 0.03) for g in base_gm]

    # OpEx
    opex = [metrics.opex_pct_avg] * years

    # DSO / DIO / DPO — round to nearest day
    dso = [round(metrics.dso_avg)] * years
    dio = [max(round(metrics.dio_avg), 1)] * years
    dpo = [max(round(metrics.dpo_avg), 1)] * years

    # CapEx
    capex = [metrics.capex_pct_avg] * years

    # Debt amortization — estimate ~5% of avg net debt per year as a rough repayment schedule
    annual_amort = max(abs(metrics.net_debt_avg) * 0.05, 0.0)
    debt_amort = [annual_amort] * years

    return {
        "Base": ModelAssumptions(
            projection_years=years,
            revenue_growth=base_growth,
            gross_margin=base_gm,
            opex_pct_revenue=opex,
            capex_pct_revenue=capex,
            tax_rate=metrics.tax_rate_avg,
            dso_days=dso,
            dio_days=dio,
            dpo_days=dpo,
            depreciation_pct_ppne=metrics.depreciation_pct_ppne_avg,
            interest_rate_on_debt=metrics.interest_rate_avg,
            debt_amortization=debt_amort,
            dividend_payout_ratio=metrics.dividend_payout_avg,
            target_min_cash_pct_revenue=0.03,
        ),
        "Bull": ModelAssumptions(
            projection_years=years,
            revenue_growth=bull_growth,
            gross_margin=bull_gm,
            opex_pct_revenue=[max(o - 0.005, 0.01) for o in opex],
            capex_pct_revenue=[max(c - 0.005, 0.01) for c in capex],
            tax_rate=metrics.tax_rate_avg,
            dso_days=[max(d - 1, 1) for d in dso],
            dio_days=[max(d - 1, 1) for d in dio],
            dpo_days=[d + 1 for d in dpo],
            depreciation_pct_ppne=metrics.depreciation_pct_ppne_avg,
            interest_rate_on_debt=metrics.interest_rate_avg,
            debt_amortization=debt_amort,
            dividend_payout_ratio=metrics.dividend_payout_avg,
            target_min_cash_pct_revenue=0.03,
        ),
        "Bear": ModelAssumptions(
            projection_years=years,
            revenue_growth=bear_growth,
            gross_margin=bear_gm,
            opex_pct_revenue=[min(o + 0.005, 0.50) for o in opex],
            capex_pct_revenue=[min(c + 0.005, 0.20) for c in capex],
            tax_rate=min(metrics.tax_rate_avg + 0.01, 0.40),
            dso_days=[d + 2 for d in dso],
            dio_days=[d + 1 for d in dio],
            dpo_days=[max(d - 1, 1) for d in dpo],
            depreciation_pct_ppne=metrics.depreciation_pct_ppne_avg,
            interest_rate_on_debt=min(metrics.interest_rate_avg + 0.01, 0.12),
            debt_amortization=debt_amort,
            dividend_payout_ratio=metrics.dividend_payout_avg,
            target_min_cash_pct_revenue=0.03,
        ),
    }


def _interpolate(start: float, end: float, n: int) -> list[float]:
    """Linearly interpolate n values from start to end."""
    if n == 1:
        return [start]
    step = (end - start) / (n - 1)
    return [start + step * i for i in range(n)]
