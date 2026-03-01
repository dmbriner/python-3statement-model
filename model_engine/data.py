from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "year",
    "revenue",
    "cogs",
    "opex",
    "depreciation",
    "interest_expense",
    "tax_rate",
    "cash",
    "accounts_receivable",
    "inventory",
    "accounts_payable",
    "ppne",
    "debt",
    "shares_outstanding",
    "capex",
]

# Optional columns — filled with 0 if absent
OPTIONAL_COLUMNS = [
    "equity",             # Total stockholders' equity
    "other_assets",       # Other assets not explicitly tracked (goodwill, intangibles, etc.)
    "other_liabilities",  # Other liabilities not explicitly tracked (deferred taxes, etc.)
]


@dataclass
class HistoricalData:
    ticker: str
    df: pd.DataFrame


def _validate_historical_df(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Historical input is missing required columns: {missing}")

    cleaned = df.copy()
    # Keep all required + any optional columns that are present
    cols_to_keep = REQUIRED_COLUMNS + [c for c in OPTIONAL_COLUMNS if c in cleaned.columns]
    cleaned = cleaned[cols_to_keep]

    # Fill missing optional columns with 0 so downstream code can always access them
    for col in OPTIONAL_COLUMNS:
        if col not in cleaned.columns:
            cleaned[col] = 0.0

    cleaned = cleaned.sort_values("year").reset_index(drop=True)
    return cleaned


def _load_from_csv(csv_path: str | Path, ticker: str) -> HistoricalData:
    df = pd.read_csv(csv_path)
    return HistoricalData(ticker=ticker, df=_validate_historical_df(df))


def _load_from_yfinance(ticker: str) -> HistoricalData:
    import yfinance as yf

    tk = yf.Ticker(ticker)
    is_df = tk.financials.T
    bs_df = tk.balance_sheet.T
    cf_df = tk.cashflow.T

    if is_df.empty or bs_df.empty or cf_df.empty:
        raise ValueError(f"Could not fetch complete financial statements for {ticker}")

    rows = []
    year_index = is_df.index.intersection(bs_df.index).intersection(cf_df.index)

    for dt in sorted(year_index):
        year = dt.year

        def get(df: pd.DataFrame, key: str, default: float = 0.0) -> float:
            if key in df.columns and pd.notna(df.loc[dt, key]):
                return float(df.loc[dt, key])
            return default

        revenue = get(is_df, "Total Revenue")
        cogs = abs(get(is_df, "Cost Of Revenue"))
        opex = abs(get(is_df, "Operating Expense"))
        depreciation = abs(get(cf_df, "Depreciation And Amortization"))
        interest_expense = abs(get(is_df, "Interest Expense"))
        pretax_income = get(is_df, "Pretax Income")
        tax_expense = abs(get(is_df, "Tax Provision"))
        tax_rate = (tax_expense / pretax_income) if pretax_income else 0.24

        cash = get(bs_df, "Cash And Cash Equivalents")
        ar = get(bs_df, "Accounts Receivable")
        inventory = get(bs_df, "Inventory")
        ap = get(bs_df, "Accounts Payable")
        ppne = get(bs_df, "Net PPE")
        debt = get(bs_df, "Total Debt")
        shares = get(bs_df, "Ordinary Shares Number", default=1.0)

        # Equity — try several yfinance field names
        equity = (
            get(bs_df, "Stockholders Equity") or
            get(bs_df, "Common Stock Equity") or
            get(bs_df, "Total Equity Gross Minority Interest") or
            0.0
        )

        # Other assets = total assets minus what we explicitly track
        total_assets = get(bs_df, "Total Assets")
        explicit_assets = cash + ar + inventory + ppne
        other_assets = max(total_assets - explicit_assets, 0.0) if total_assets > 0 else 0.0

        # Other liabilities = total liabilities minus debt and AP
        total_liab = get(bs_df, "Total Liabilities Net Minority Interest") or get(bs_df, "Total Liabilities")
        explicit_liab = debt + ap
        other_liabilities = max(total_liab - explicit_liab, 0.0) if total_liab > 0 else 0.0

        rows.append(
            {
                "year": year,
                "revenue": revenue,
                "cogs": cogs,
                "opex": opex,
                "depreciation": depreciation,
                "interest_expense": interest_expense,
                "tax_rate": min(max(tax_rate, 0.0), 0.45),
                "cash": cash,
                "accounts_receivable": ar,
                "inventory": inventory,
                "accounts_payable": ap,
                "ppne": ppne,
                "debt": debt,
                "shares_outstanding": max(shares, 1.0),
                "capex": abs(get(cf_df, "Capital Expenditure")),
                "equity": equity,
                "other_assets": other_assets,
                "other_liabilities": other_liabilities,
            }
        )

    df = pd.DataFrame(rows)
    df = df[df["revenue"] > 0]
    if df.empty:
        raise ValueError(f"No valid annual rows returned from yfinance for {ticker}")

    return HistoricalData(ticker=ticker, df=_validate_historical_df(df))


def load_historical_data(ticker: str, csv_path: str | Path | None = None) -> HistoricalData:
    """Load historical data from CSV or yfinance.

    CSV takes precedence when provided.
    """
    if csv_path:
        return _load_from_csv(csv_path, ticker=ticker)

    return _load_from_yfinance(ticker)
