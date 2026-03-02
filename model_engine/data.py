from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .market_data import CompanyProfile, resolve_company_profile

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

OPTIONAL_COLUMNS = [
    "equity",
    "other_assets",
    "other_liabilities",
    "period_end",
    "period_label",
    "fiscal_quarter",
]


@dataclass
class HistoricalData:
    ticker: str
    df: pd.DataFrame
    annual_df: pd.DataFrame | None = None
    quarterly_df: pd.DataFrame | None = None
    profile: CompanyProfile | None = None

    def annual(self) -> pd.DataFrame:
        return self.annual_df if self.annual_df is not None else self.df

    def quarterly(self) -> pd.DataFrame:
        if self.quarterly_df is not None and not self.quarterly_df.empty:
            return self.quarterly_df
        return self.annual()


def _validate_historical_df(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Historical input is missing required columns: {missing}")

    cleaned = df.copy()
    cols_to_keep = REQUIRED_COLUMNS + [c for c in OPTIONAL_COLUMNS if c in cleaned.columns]
    cleaned = cleaned[cols_to_keep]

    for col in OPTIONAL_COLUMNS:
        if col not in cleaned.columns:
            cleaned[col] = 0.0 if col not in {"period_end", "period_label"} else None

    cleaned = cleaned.sort_values(["year", "fiscal_quarter", "period_end"]).reset_index(drop=True)
    return cleaned


def reporting_frame(hist: HistoricalData, frequency: str) -> tuple[pd.DataFrame, str]:
    if frequency == "Quarterly":
        frame = hist.quarterly().copy()
        x_col = "period_label" if "period_label" in frame.columns else "year"
        return frame, x_col
    frame = hist.annual().copy()
    return frame, "year"


def _load_from_csv(csv_path: str | Path, ticker: str) -> HistoricalData:
    df = pd.read_csv(csv_path)
    validated = _validate_historical_df(df)
    return HistoricalData(ticker=ticker, df=validated, annual_df=validated, quarterly_df=pd.DataFrame())


def _statement_value(df: pd.DataFrame, dt, key: str, default: float = 0.0) -> float:
    if key in df.columns and pd.notna(df.loc[dt, key]):
        return float(df.loc[dt, key])
    return default


def _build_statement_rows(is_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame, period_type: str) -> pd.DataFrame:
    rows: list[dict] = []
    period_index = is_df.index.intersection(bs_df.index).intersection(cf_df.index)

    for dt in sorted(period_index):
        revenue = _statement_value(is_df, dt, "Total Revenue")
        cogs = abs(_statement_value(is_df, dt, "Cost Of Revenue"))
        opex = abs(_statement_value(is_df, dt, "Operating Expense"))
        depreciation = abs(_statement_value(cf_df, dt, "Depreciation And Amortization"))
        interest_expense = abs(_statement_value(is_df, dt, "Interest Expense"))
        pretax_income = _statement_value(is_df, dt, "Pretax Income")
        tax_expense = abs(_statement_value(is_df, dt, "Tax Provision"))
        tax_rate = (tax_expense / pretax_income) if pretax_income else 0.24

        cash = _statement_value(bs_df, dt, "Cash And Cash Equivalents")
        ar = _statement_value(bs_df, dt, "Accounts Receivable")
        inventory = _statement_value(bs_df, dt, "Inventory")
        ap = _statement_value(bs_df, dt, "Accounts Payable")
        ppne = _statement_value(bs_df, dt, "Net PPE")
        debt = _statement_value(bs_df, dt, "Total Debt")
        shares = _statement_value(bs_df, dt, "Ordinary Shares Number", default=1.0)

        equity = (
            _statement_value(bs_df, dt, "Stockholders Equity")
            or _statement_value(bs_df, dt, "Common Stock Equity")
            or _statement_value(bs_df, dt, "Total Equity Gross Minority Interest")
            or 0.0
        )
        total_assets = _statement_value(bs_df, dt, "Total Assets")
        total_liab = _statement_value(bs_df, dt, "Total Liabilities Net Minority Interest") or _statement_value(bs_df, dt, "Total Liabilities")
        explicit_assets = cash + ar + inventory + ppne
        explicit_liab = debt + ap
        other_assets = max(total_assets - explicit_assets, 0.0) if total_assets > 0 else 0.0
        other_liabilities = max(total_liab - explicit_liab, 0.0) if total_liab > 0 else 0.0

        period_end = pd.Timestamp(dt)
        quarter = int(period_end.quarter)
        label = (
            f"{period_end.year} Q{quarter}"
            if period_type == "quarterly"
            else f"FY {period_end.year}"
        )

        rows.append(
            {
                "year": int(period_end.year),
                "period_end": period_end.date().isoformat(),
                "period_label": label,
                "fiscal_quarter": quarter if period_type == "quarterly" else 4,
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
                "capex": abs(_statement_value(cf_df, dt, "Capital Expenditure")),
                "equity": equity,
                "other_assets": other_assets,
                "other_liabilities": other_liabilities,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df[df["revenue"] > 0].reset_index(drop=True)


def _load_from_yfinance(ticker: str) -> HistoricalData:
    import yfinance as yf

    tk = yf.Ticker(ticker)
    annual_is = tk.financials.T
    annual_bs = tk.balance_sheet.T
    annual_cf = tk.cashflow.T
    quarterly_is = tk.quarterly_financials.T
    quarterly_bs = tk.quarterly_balance_sheet.T
    quarterly_cf = tk.quarterly_cashflow.T

    if annual_is.empty or annual_bs.empty or annual_cf.empty:
        raise ValueError(f"Could not fetch complete annual financial statements for {ticker}")

    annual_df = _build_statement_rows(annual_is, annual_bs, annual_cf, period_type="annual")
    quarterly_df = _build_statement_rows(quarterly_is, quarterly_bs, quarterly_cf, period_type="quarterly")

    if annual_df.empty:
        raise ValueError(f"No valid annual rows returned from yfinance for {ticker}")

    annual_df = _validate_historical_df(annual_df)
    quarterly_df = _validate_historical_df(quarterly_df) if not quarterly_df.empty else pd.DataFrame()

    profile = None
    try:
        profile = resolve_company_profile(ticker)
    except Exception:
        profile = None

    return HistoricalData(
        ticker=ticker,
        df=annual_df,
        annual_df=annual_df,
        quarterly_df=quarterly_df,
        profile=profile,
    )


def load_historical_data(ticker: str, csv_path: str | Path | None = None) -> HistoricalData:
    if csv_path:
        return _load_from_csv(csv_path, ticker=ticker)
    return _load_from_yfinance(ticker)
