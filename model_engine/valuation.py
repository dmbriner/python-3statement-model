"""DCF valuation engine with WACC sensitivity grid."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class DCFResult:
    wacc: float
    terminal_growth_rate: float
    pv_fcf_sum: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    value_per_share: float
    tv_pct_of_ev: float           # % of EV attributable to terminal value (a useful sanity check)
    implied_ev_ebitda: float      # EV / last-year EBITDA


def run_dcf(
    fcf_series: list[float],
    ebitda_series: list[float],
    wacc: float,
    terminal_growth: float,
    net_debt: float,
    shares: float,
) -> DCFResult:
    """
    Standard unlevered DCF:
      1. Discount each year's FCF at WACC
      2. Terminal value via Gordon Growth Model: FCF_final × (1+g) / (WACC − g)
      3. EV = PV(FCFs) + PV(TV)
      4. Equity Value = EV − Net Debt
      5. Per Share = Equity Value / Shares

    Args:
        fcf_series: List of projected FCFs (year 1 … year N)
        ebitda_series: List of projected EBITDAs (for EV/EBITDA multiple)
        wacc: Weighted average cost of capital (e.g. 0.09 for 9%)
        terminal_growth: Terminal FCF growth rate (e.g. 0.025 for 2.5%)
        net_debt: Ending debt − ending cash (positive = net borrower)
        shares: Shares outstanding (same units as FCF — millions or actuals)
    """
    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth rate for a finite terminal value.")

    n = len(fcf_series)
    pv_fcfs = []
    for t, fcf in enumerate(fcf_series, start=1):
        pv_fcfs.append(fcf / (1 + wacc) ** t)

    pv_fcf_sum = sum(pv_fcfs)

    # Terminal value at end of year N
    final_fcf = fcf_series[-1]
    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal_value = terminal_value / (1 + wacc) ** n

    enterprise_value = pv_fcf_sum + pv_terminal_value
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / max(shares, 1.0)

    tv_pct = pv_terminal_value / enterprise_value if enterprise_value != 0 else 0.0

    last_ebitda = ebitda_series[-1] if ebitda_series else 0.0
    implied_ev_ebitda = enterprise_value / last_ebitda if last_ebitda > 0 else 0.0

    return DCFResult(
        wacc=wacc,
        terminal_growth_rate=terminal_growth,
        pv_fcf_sum=pv_fcf_sum,
        pv_terminal_value=pv_terminal_value,
        enterprise_value=enterprise_value,
        net_debt=net_debt,
        equity_value=equity_value,
        value_per_share=value_per_share,
        tv_pct_of_ev=tv_pct,
        implied_ev_ebitda=implied_ev_ebitda,
    )


def wacc_terminal_sensitivity(
    fcf_series: list[float],
    ebitda_series: list[float],
    net_debt: float,
    shares: float,
    wacc_range: list[float] | None = None,
    growth_range: list[float] | None = None,
    output: str = "value_per_share",  # "value_per_share" | "enterprise_value" | "equity_value"
) -> pd.DataFrame:
    """
    2D sensitivity grid: WACC (rows) × Terminal Growth Rate (columns).
    Returns the selected output metric for each combination.
    """
    wacc_range = wacc_range or [0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
    growth_range = growth_range or [0.015, 0.020, 0.025, 0.030, 0.035]

    table = pd.DataFrame(index=wacc_range, columns=growth_range, dtype=float)

    for w in wacc_range:
        for g in growth_range:
            if w <= g:
                table.loc[w, g] = np.nan
                continue
            result = run_dcf(fcf_series, ebitda_series, w, g, net_debt, shares)
            table.loc[w, g] = getattr(result, output)

    table.index.name = "wacc"
    table.columns.name = "terminal_growth"
    return table
