"""Valuation engines for DCF, trading comps, precedent transactions, and LBO."""

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
    tv_pct_of_ev: float
    implied_ev_ebitda: float


@dataclass
class MultipleValuationResult:
    method: str
    enterprise_value: float
    equity_value: float
    value_per_share: float
    reference_multiple: float
    reference_metric: str


@dataclass
class LBOResult:
    entry_ev: float
    debt_funding: float
    sponsor_equity: float
    exit_ev: float
    exit_equity: float
    moic: float
    irr: float
    value_per_share: float


def run_dcf(
    fcf_series: list[float],
    ebitda_series: list[float],
    wacc: float,
    terminal_growth: float,
    net_debt: float,
    shares: float,
) -> DCFResult:
    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth rate for a finite terminal value.")

    n = len(fcf_series)
    pv_fcfs = [fcf / (1 + wacc) ** t for t, fcf in enumerate(fcf_series, start=1)]
    pv_fcf_sum = sum(pv_fcfs)

    final_fcf = fcf_series[-1]
    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal_value = terminal_value / (1 + wacc) ** n

    enterprise_value = pv_fcf_sum + pv_terminal_value
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / max(shares, 1.0)
    tv_pct = pv_terminal_value / enterprise_value if enterprise_value else 0.0

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


def run_multiple_valuation(
    method: str,
    metric_value: float,
    multiple: float,
    net_debt: float,
    shares: float,
    reference_metric: str,
) -> MultipleValuationResult:
    enterprise_value = metric_value * multiple
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / max(shares, 1.0)
    return MultipleValuationResult(
        method=method,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        value_per_share=value_per_share,
        reference_multiple=multiple,
        reference_metric=reference_metric,
    )


def run_precedent_transactions(
    revenue: float,
    ebitda: float,
    net_debt: float,
    shares: float,
    ev_revenue_multiple: float,
    ev_ebitda_multiple: float,
    control_premium: float,
) -> list[MultipleValuationResult]:
    premium_factor = 1 + control_premium
    return [
        run_multiple_valuation(
            "Precedent EV / Revenue",
            revenue,
            ev_revenue_multiple * premium_factor,
            net_debt,
            shares,
            "Revenue",
        ),
        run_multiple_valuation(
            "Precedent EV / EBITDA",
            ebitda,
            ev_ebitda_multiple * premium_factor,
            net_debt,
            shares,
            "EBITDA",
        ),
    ]


def run_lbo(
    ebitda_series: list[float],
    fcf_series: list[float],
    net_debt: float,
    shares: float,
    entry_multiple: float,
    exit_multiple: float,
    debt_multiple: float,
    interest_rate: float,
) -> LBOResult:
    if not ebitda_series:
        raise ValueError("LBO valuation requires projected EBITDA.")

    entry_ebitda = max(ebitda_series[0], 0.0)
    exit_ebitda = max(ebitda_series[-1], 0.0)
    entry_ev = entry_ebitda * entry_multiple

    opening_debt = max(entry_ebitda * debt_multiple, 0.0)
    sponsor_equity = max(entry_ev - opening_debt, 0.0)

    debt_balance = opening_debt
    for fcf in fcf_series:
        cash_available = max(fcf, 0.0)
        interest = debt_balance * interest_rate
        debt_balance = max(debt_balance + interest - cash_available, 0.0)

    exit_ev = exit_ebitda * exit_multiple
    exit_equity = exit_ev - debt_balance - max(net_debt, 0.0)
    moic = exit_equity / sponsor_equity if sponsor_equity else 0.0
    years = max(len(fcf_series), 1)
    irr = (moic ** (1 / years) - 1) if moic > 0 else -1.0
    value_per_share = exit_equity / max(shares, 1.0)

    return LBOResult(
        entry_ev=entry_ev,
        debt_funding=opening_debt,
        sponsor_equity=sponsor_equity,
        exit_ev=exit_ev,
        exit_equity=exit_equity,
        moic=moic,
        irr=irr,
        value_per_share=value_per_share,
    )


def valuation_summary_table(
    dcf_result: DCFResult,
    comps_results: list[MultipleValuationResult],
    precedent_results: list[MultipleValuationResult],
    lbo_result: LBOResult,
) -> pd.DataFrame:
    rows = [
        {"Method": "DCF", "Enterprise Value": dcf_result.enterprise_value, "Equity Value": dcf_result.equity_value, "Per Share": dcf_result.value_per_share},
        *[
            {"Method": result.method, "Enterprise Value": result.enterprise_value, "Equity Value": result.equity_value, "Per Share": result.value_per_share}
            for result in comps_results
        ],
        *[
            {"Method": result.method, "Enterprise Value": result.enterprise_value, "Equity Value": result.equity_value, "Per Share": result.value_per_share}
            for result in precedent_results
        ],
        {"Method": "LBO", "Enterprise Value": lbo_result.exit_ev, "Equity Value": lbo_result.exit_equity, "Per Share": lbo_result.value_per_share},
    ]
    return pd.DataFrame(rows)


def wacc_terminal_sensitivity(
    fcf_series: list[float],
    ebitda_series: list[float],
    net_debt: float,
    shares: float,
    wacc_range: list[float] | None = None,
    growth_range: list[float] | None = None,
    output: str = "value_per_share",
) -> pd.DataFrame:
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
