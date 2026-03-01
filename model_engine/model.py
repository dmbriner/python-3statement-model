from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ModelAssumptions
from .data import HistoricalData


@dataclass
class ModelOutput:
    income_statement: pd.DataFrame
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    fcf: pd.DataFrame
    ppe_schedule: pd.DataFrame
    debt_schedule: pd.DataFrame
    equity_schedule: pd.DataFrame


def _base_year(df: pd.DataFrame) -> pd.Series:
    return df.sort_values("year").iloc[-1]


def run_three_statement_model(historical_data: HistoricalData, assumptions: ModelAssumptions) -> ModelOutput:
    assumptions.normalize()
    hist = historical_data.df
    base = _base_year(hist)

    years = [int(base["year"]) + i for i in range(1, assumptions.projection_years + 1)]

    income_rows: list[dict] = []
    balance_rows: list[dict] = []
    cash_rows: list[dict] = []
    fcf_rows: list[dict] = []
    ppe_rows: list[dict] = []
    debt_rows: list[dict] = []
    equity_rows: list[dict] = []

    prev_revenue = float(base["revenue"])
    prev_ar = float(base["accounts_receivable"])
    prev_inventory = float(base["inventory"])
    prev_ap = float(base["accounts_payable"])
    prev_ppne = float(base["ppne"])
    prev_debt = float(base["debt"])
    prev_cash = float(base["cash"])
    shares = max(float(base["shares_outstanding"]), 1.0)

    # Balance sheet "other" items — held constant at base year values
    other_assets = float(base.get("other_assets", 0.0))
    other_liabilities = float(base.get("other_liabilities", 0.0))

    # Starting equity from historical data (or approximate from assets - liabilities)
    base_equity = float(base.get("equity", 0.0))
    if base_equity == 0.0:
        # Estimate: total observable assets minus total observable liabilities
        base_equity = (
            float(base["cash"]) + float(base["accounts_receivable"]) +
            float(base["inventory"]) + float(base["ppne"]) + other_assets -
            float(base["debt"]) - float(base["accounts_payable"]) - other_liabilities
        )
    prev_equity = base_equity

    for i, year in enumerate(years):
        revenue = prev_revenue * (1 + assumptions.revenue_growth[i])
        gross_profit = revenue * assumptions.gross_margin[i]
        cogs = revenue - gross_profit
        opex = revenue * assumptions.opex_pct_revenue[i]

        ebitda = gross_profit - opex
        depreciation = prev_ppne * assumptions.depreciation_pct_ppne
        ebit = ebitda - depreciation

        average_debt = (prev_debt + max(prev_debt - assumptions.debt_amortization[i], 0.0)) / 2
        interest_expense = average_debt * assumptions.interest_rate_on_debt
        ebt = ebit - interest_expense
        taxes = max(ebt, 0.0) * assumptions.tax_rate
        net_income = ebt - taxes

        ar = revenue / 365.0 * assumptions.dso_days[i]
        inventory = cogs / 365.0 * assumptions.dio_days[i]
        ap = cogs / 365.0 * assumptions.dpo_days[i]
        nwc = ar + inventory - ap
        prev_nwc = prev_ar + prev_inventory - prev_ap
        change_nwc = nwc - prev_nwc

        capex = revenue * assumptions.capex_pct_revenue[i]
        ppne = prev_ppne + capex - depreciation

        debt_repayment = min(prev_debt, assumptions.debt_amortization[i])
        debt = max(prev_debt - debt_repayment, 0.0)

        cfo = net_income + depreciation - change_nwc
        cfi = -capex
        dividends = max(net_income, 0.0) * assumptions.dividend_payout_ratio
        cff_pre_cash_sweep = -debt_repayment - dividends

        ending_cash = prev_cash + cfo + cfi + cff_pre_cash_sweep
        min_cash = revenue * assumptions.target_min_cash_pct_revenue

        debt_draw = 0.0
        excess_cash_sweep = 0.0
        if ending_cash < min_cash:
            debt_draw = min_cash - ending_cash
            ending_cash = min_cash
            debt += debt_draw
        elif ending_cash > min_cash * 1.5:
            excess_cash_sweep = ending_cash - min_cash * 1.5
            debt_paydown = min(excess_cash_sweep, debt)
            debt -= debt_paydown
            ending_cash -= debt_paydown

        cff = cff_pre_cash_sweep + debt_draw - excess_cash_sweep
        free_cash_flow = ebit * (1 - assumptions.tax_rate) + depreciation - capex - change_nwc

        # Equity rollforward (for display in equity schedule)
        retained_add = net_income - dividends
        ending_equity = prev_equity + retained_add

        # Full balance sheet totals — equity is the PLUG so balance sheet always balances
        total_assets = ending_cash + ar + inventory + ppne + other_assets
        total_liabilities = debt + ap + other_liabilities
        total_equity_plug = total_assets - total_liabilities   # Ensures Assets = Liabilities + Equity
        # Plug vs rollforward difference = unmodeled balance sheet changes (deferred taxes, goodwill, etc.)
        bs_plug = total_equity_plug - ending_equity

        income_rows.append(
            {
                "year": year,
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross_profit,
                "opex": opex,
                "ebitda": ebitda,
                "depreciation": depreciation,
                "ebit": ebit,
                "interest_expense": interest_expense,
                "ebt": ebt,
                "taxes": taxes,
                "net_income": net_income,
                "eps": net_income / shares,
            }
        )

        balance_rows.append(
            {
                "year": year,
                # Assets
                "cash": ending_cash,
                "accounts_receivable": ar,
                "inventory": inventory,
                "other_assets": other_assets,
                "ppne": ppne,
                "total_assets": total_assets,
                # Liabilities
                "accounts_payable": ap,
                "debt": debt,
                "other_liabilities": other_liabilities,
                "total_liabilities": total_liabilities,
                # Equity
                "total_equity": total_equity_plug,
                "equity_rollforward": ending_equity,
                "total_liabilities_and_equity": total_liabilities + total_equity_plug,
                "bs_plug": bs_plug,
                # Working capital (for schedules tab)
                "nwc": nwc,
            }
        )

        cash_rows.append(
            {
                "year": year,
                "net_income": net_income,
                "depreciation": depreciation,
                "change_nwc": -change_nwc,  # sign convention: negative change = cash inflow
                "cfo": cfo,
                "capex": -capex,
                "cfi": cfi,
                "debt_draw": debt_draw,
                "debt_repayment": -(debt_repayment + excess_cash_sweep),
                "dividends": -dividends,
                "cff": cff,
                "net_change_cash": cfo + cfi + cff,
            }
        )

        fcf_rows.append(
            {
                "year": year,
                "ebitda": ebitda,
                "nopat": ebit * (1 - assumptions.tax_rate),
                "depreciation": depreciation,
                "capex": capex,
                "change_nwc": change_nwc,
                "fcf": free_cash_flow,
            }
        )

        ppe_rows.append(
            {
                "year": year,
                "beginning_ppne": prev_ppne,
                "capex": capex,
                "depreciation": depreciation,
                "ending_ppne": ppne,
            }
        )

        debt_rows.append(
            {
                "year": year,
                "beginning_debt": prev_debt,
                "debt_draw": debt_draw,
                "debt_repayment": debt_repayment + excess_cash_sweep,
                "ending_debt": debt,
                "interest_expense": interest_expense,
                "avg_debt": average_debt,
            }
        )

        equity_rows.append(
            {
                "year": year,
                "beginning_equity": prev_equity,
                "net_income": net_income,
                "dividends": dividends,
                "other_changes": 0.0,   # share issuance / buybacks (not modeled)
                "ending_equity": ending_equity,
            }
        )

        prev_revenue = revenue
        prev_ar = ar
        prev_inventory = inventory
        prev_ap = ap
        prev_ppne = ppne
        prev_debt = debt
        prev_cash = ending_cash
        prev_equity = ending_equity

    income_df = pd.DataFrame(income_rows)
    balance_df = pd.DataFrame(balance_rows)
    cash_df = pd.DataFrame(cash_rows)
    fcf_df = pd.DataFrame(fcf_rows)
    ppe_df = pd.DataFrame(ppe_rows)
    debt_df = pd.DataFrame(debt_rows)
    equity_df = pd.DataFrame(equity_rows)

    for frame in (income_df, balance_df, cash_df, fcf_df, ppe_df, debt_df, equity_df):
        numeric_cols = [c for c in frame.columns if c != "year"]
        frame[numeric_cols] = frame[numeric_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    return ModelOutput(
        income_statement=income_df,
        balance_sheet=balance_df,
        cash_flow=cash_df,
        fcf=fcf_df,
        ppe_schedule=ppe_df,
        debt_schedule=debt_df,
        equity_schedule=equity_df,
    )
