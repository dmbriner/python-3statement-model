"""Sensitivity analysis: 2D tables and tornado charts."""

from __future__ import annotations

import copy

import pandas as pd

from .config import ModelAssumptions
from .data import HistoricalData
from .model import run_three_statement_model


def build_sensitivity_table(
    historical_data: HistoricalData,
    assumptions: ModelAssumptions,
    growth_shocks: list[float] | None = None,
    margin_shocks: list[float] | None = None,
) -> pd.DataFrame:
    """2D sensitivity for average FCF against growth/margin shocks (kept for backwards compatibility)."""
    return build_multi_output_sensitivity(
        historical_data, assumptions, "fcf", growth_shocks, margin_shocks
    )


def build_multi_output_sensitivity(
    historical_data: HistoricalData,
    assumptions: ModelAssumptions,
    output_metric: str = "fcf",
    growth_shocks: list[float] | None = None,
    margin_shocks: list[float] | None = None,
) -> pd.DataFrame:
    """
    2D sensitivity table: revenue growth shock × gross margin shock → average of output_metric.

    Args:
        output_metric: "fcf" | "ebitda" | "net_income"
    """
    growth_shocks = growth_shocks or [-0.02, -0.01, 0.0, 0.01, 0.02]
    margin_shocks = margin_shocks or [-0.015, -0.01, 0.0, 0.01, 0.015]

    table = pd.DataFrame(index=growth_shocks, columns=margin_shocks, dtype=float)

    for g in growth_shocks:
        for m in margin_shocks:
            scenario = ModelAssumptions(**copy.deepcopy(assumptions).__dict__)
            scenario.revenue_growth = [x + g for x in assumptions.revenue_growth]
            scenario.gross_margin = [max(0.01, min(0.9, x + m)) for x in assumptions.gross_margin]
            output = run_three_statement_model(historical_data, scenario)

            if output_metric == "fcf":
                val = float(output.fcf["fcf"].mean())
            elif output_metric == "ebitda":
                val = float(output.income_statement["ebitda"].mean())
            elif output_metric == "net_income":
                val = float(output.income_statement["net_income"].mean())
            else:
                val = float(output.fcf["fcf"].mean())

            table.loc[g, m] = val

    table.index.name = "revenue_growth_shock"
    table.columns.name = "gross_margin_shock"
    return table


def build_tornado_chart(
    historical_data: HistoricalData,
    assumptions: ModelAssumptions,
    output_metric: str = "fcf",
    shock_pct: float = 0.10,
) -> pd.DataFrame:
    """
    Tornado chart data: shock each assumption ±shock_pct and measure impact on avg output.

    Returns a DataFrame sorted by |impact| descending, with columns:
        assumption, base_value, low_value, high_value, low_output, high_output, impact_range
    """
    base_output = run_three_statement_model(historical_data, copy.deepcopy(assumptions))
    base_val = _get_metric(base_output, output_metric)

    shockable = {
        "revenue_growth": ("list_scalar", shock_pct),
        "gross_margin": ("list_scalar", shock_pct),
        "opex_pct_revenue": ("list_scalar", shock_pct),
        "capex_pct_revenue": ("list_scalar", shock_pct),
        "tax_rate": ("scalar", shock_pct),
        "interest_rate_on_debt": ("scalar", shock_pct),
        "dividend_payout_ratio": ("scalar", shock_pct),
    }

    rows = []
    for param, (kind, shock) in shockable.items():
        asm_low = copy.deepcopy(assumptions)
        asm_high = copy.deepcopy(assumptions)
        base_raw = getattr(assumptions, param)

        if kind == "list_scalar":
            setattr(asm_low, param, [v * (1 - shock) for v in base_raw])
            setattr(asm_high, param, [v * (1 + shock) for v in base_raw])
            base_display = float(sum(base_raw) / len(base_raw))
        else:
            setattr(asm_low, param, base_raw * (1 - shock))
            setattr(asm_high, param, base_raw * (1 + shock))
            base_display = base_raw

        low_out = _get_metric(run_three_statement_model(historical_data, asm_low), output_metric)
        high_out = _get_metric(run_three_statement_model(historical_data, asm_high), output_metric)

        rows.append({
            "assumption": param.replace("_", " ").title(),
            "base_value": base_display,
            "low_output": low_out,
            "high_output": high_out,
            "impact_range": abs(high_out - low_out),
            "low_vs_base": low_out - base_val,
            "high_vs_base": high_out - base_val,
        })

    df = pd.DataFrame(rows).sort_values("impact_range", ascending=True)
    return df


def _get_metric(output, metric: str) -> float:
    if metric == "fcf":
        return float(output.fcf["fcf"].mean())
    elif metric == "ebitda":
        return float(output.income_statement["ebitda"].mean())
    elif metric == "net_income":
        return float(output.income_statement["net_income"].mean())
    return float(output.fcf["fcf"].mean())
