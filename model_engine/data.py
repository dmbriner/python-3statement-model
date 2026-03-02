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

YFINANCE_SYMBOL_REPLACEMENTS = {
    ".": "-",
}


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

    sort_keys = [k for k in ["year", "fiscal_quarter", "period_end"] if k in cleaned.columns]
    cleaned = cleaned.sort_values(sort_keys).reset_index(drop=True)
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
    normalized = _normalize_input_ticker(ticker)
    return HistoricalData(ticker=normalized, df=validated, annual_df=validated, quarterly_df=pd.DataFrame())


def _normalize_input_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def _provider_symbol(ticker: str, provider: str) -> str:
    normalized = _normalize_input_ticker(ticker)
    if provider == "yfinance":
        for old, new in YFINANCE_SYMBOL_REPLACEMENTS.items():
            normalized = normalized.replace(old, new)
    return normalized


def _statement_value(df: pd.DataFrame, dt, key: str | list[str] | tuple[str, ...], default: float = 0.0) -> float:
    keys = [key] if isinstance(key, str) else list(key)
    for candidate in keys:
        if candidate in df.columns and pd.notna(df.loc[dt, candidate]):
            return float(df.loc[dt, candidate])
    return default


def _statement_frame(ticker_obj, annual_names: list[str], quarterly_names: list[str] | None = None) -> pd.DataFrame:
    for attr in annual_names:
        frame = getattr(ticker_obj, attr, pd.DataFrame())
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            return frame.T
    if quarterly_names:
        for attr in quarterly_names:
            frame = getattr(ticker_obj, attr, pd.DataFrame())
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                return frame.T
    return pd.DataFrame()


def _build_statement_rows(is_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame, period_type: str) -> pd.DataFrame:
    """Build HistoricalData rows from yfinance DataFrames.

    yfinance returns values in full dollars (e.g., Apple revenue = 383,285,000,000).
    We divide by 1,000,000 to convert to $M, consistent with the CSV template and EDGAR loader.
    Shares outstanding are also divided by 1,000,000 to express in millions of shares.
    """
    M = 1_000_000
    rows: list[dict] = []
    period_index = is_df.index.intersection(bs_df.index).intersection(cf_df.index)

    for dt in sorted(period_index):
        revenue = _statement_value(
            is_df,
            dt,
            [
                "Total Revenue",
                "Operating Revenue",
                "Revenue",
                "Net Sales",
                "Sales Revenue",
            ],
        ) / M
        if revenue <= 0:
            continue

        cogs = abs(_statement_value(is_df, dt, ["Cost Of Revenue", "Cost of Revenue", "Cost Of Goods Sold"])) / M
        opex = abs(
            _statement_value(
                is_df,
                dt,
                [
                    "Operating Expense",
                    "Operating Expenses",
                    "Selling General And Administration",
                    "Selling General Administrative",
                ],
            )
        ) / M
        depreciation = abs(
            _statement_value(
                cf_df,
                dt,
                [
                    "Depreciation And Amortization",
                    "Depreciation Amortization Depletion",
                    "Depreciation",
                ],
            )
        ) / M
        interest_expense = abs(
            _statement_value(
                is_df,
                dt,
                ["Interest Expense", "Net Interest Income", "Interest Expense Non Operating"],
            )
        ) / M
        pretax_income = _statement_value(is_df, dt, ["Pretax Income", "Pre Tax Income", "Income Before Tax"]) / M
        tax_expense = abs(_statement_value(is_df, dt, ["Tax Provision", "Tax Rate For Calcs", "Income Tax Expense"])) / M
        tax_rate = (tax_expense / pretax_income) if pretax_income else 0.24

        cash = _statement_value(
            bs_df,
            dt,
            [
                "Cash And Cash Equivalents",
                "Cash Cash Equivalents And Short Term Investments",
                "Cash",
            ],
        ) / M
        ar = _statement_value(bs_df, dt, ["Accounts Receivable", "Receivables", "Net Receivables"]) / M
        inventory = _statement_value(bs_df, dt, ["Inventory", "Inventories"]) / M
        ap = _statement_value(bs_df, dt, ["Accounts Payable", "Payables And Accrued Expenses"]) / M
        ppne = _statement_value(bs_df, dt, ["Net PPE", "Property Plant Equipment Net", "Gross PPE"]) / M
        debt = _statement_value(bs_df, dt, ["Total Debt", "Net Debt", "Total Capitalization"]) / M
        if debt <= 0:
            debt = (
                _statement_value(bs_df, dt, ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"])
                + _statement_value(bs_df, dt, ["Current Debt", "Current Debt And Capital Lease Obligation", "Short Long Term Debt"])
            ) / M

        # Shares: yfinance returns actual share count; divide by M to get millions
        shares_raw = _statement_value(
            bs_df,
            dt,
            ["Ordinary Shares Number", "Share Issued", "Common Stock Shares Outstanding"],
            default=M,
        )
        shares = max(shares_raw / M, 1.0)

        # Equity — try multiple yfinance field names
        equity_raw = (
            _statement_value(bs_df, dt, "Stockholders Equity")
            or _statement_value(bs_df, dt, "Common Stock Equity")
            or _statement_value(bs_df, dt, "Total Equity Gross Minority Interest")
            or _statement_value(bs_df, dt, "Total Equity")
            or 0.0
        )
        equity = equity_raw / M

        total_assets = _statement_value(bs_df, dt, ["Total Assets", "Assets"]) / M
        total_liab_raw = (
            _statement_value(bs_df, dt, "Total Liabilities Net Minority Interest")
            or _statement_value(bs_df, dt, "Total Liabilities")
            or _statement_value(bs_df, dt, "Liabilities")
            or 0.0
        )
        total_liab = total_liab_raw / M

        if cogs == 0:
            gross_profit = _statement_value(is_df, dt, ["Gross Profit", "GrossProfit"]) / M
            if gross_profit > 0:
                cogs = max(revenue - gross_profit, 0.0)

        if opex == 0:
            operating_income = _statement_value(is_df, dt, ["Operating Income", "Operating Income Or Loss"]) / M
            gross_profit = max(revenue - cogs, 0.0)
            if gross_profit > 0 and operating_income != 0:
                opex = max(gross_profit - operating_income, 0.0)

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
                "shares_outstanding": shares,
                "capex": abs(
                    _statement_value(
                        cf_df,
                        dt,
                        [
                            "Capital Expenditure",
                            "Capital Expenditure Reported",
                            "Purchase Of PPE",
                            "Investments In Property Plant And Equipment",
                        ],
                    )
                ) / M,
                "equity": equity,
                "other_assets": other_assets,
                "other_liabilities": other_liabilities,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df[df["revenue"] > 0].reset_index(drop=True)


def _load_quarterly_from_yfinance(ticker: str) -> pd.DataFrame:
    """Attempt to load quarterly data from yfinance. Returns empty DataFrame on failure."""
    try:
        import yfinance as yf
        tk = yf.Ticker(_provider_symbol(ticker, "yfinance"))
        q_is = _statement_frame(tk, ["quarterly_income_stmt", "quarterly_financials"])
        q_bs = _statement_frame(tk, ["quarterly_balance_sheet"])
        q_cf = _statement_frame(tk, ["quarterly_cashflow"])
        if q_is.empty or q_bs.empty or q_cf.empty:
            return pd.DataFrame()
        qdf = _build_statement_rows(q_is, q_bs, q_cf, period_type="quarterly")
        if qdf.empty:
            return pd.DataFrame()
        return _validate_historical_df(qdf)
    except Exception:
        return pd.DataFrame()


def _load_from_yfinance(ticker: str) -> HistoricalData:
    import yfinance as yf

    normalized = _normalize_input_ticker(ticker)
    tk = yf.Ticker(_provider_symbol(normalized, "yfinance"))
    annual_is = _statement_frame(tk, ["income_stmt", "financials"])
    annual_bs = _statement_frame(tk, ["balance_sheet"])
    annual_cf = _statement_frame(tk, ["cashflow"])
    quarterly_is = _statement_frame(tk, ["quarterly_income_stmt", "quarterly_financials"])
    quarterly_bs = _statement_frame(tk, ["quarterly_balance_sheet"])
    quarterly_cf = _statement_frame(tk, ["quarterly_cashflow"])

    if annual_is.empty or annual_bs.empty or annual_cf.empty:
        raise ValueError(f"Could not fetch complete annual financial statements for {normalized}")

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
        pass

    return HistoricalData(
        ticker=normalized,
        df=annual_df,
        annual_df=annual_df,
        quarterly_df=quarterly_df,
        profile=profile,
    )


def load_historical_data(ticker: str, csv_path: str | Path | None = None) -> HistoricalData:
    """Load historical financial data for a ticker.

    Load order (when no CSV is provided):
      1. SEC EDGAR  — free, official, no API key, US-listed companies only
      2. yfinance   — free, international coverage, fallback for non-US or EDGAR failures

    All values returned in $M; shares outstanding in millions of shares.
    """
    normalized = _normalize_input_ticker(ticker)
    if csv_path:
        return _load_from_csv(csv_path, ticker=normalized)

    # ── Primary: SEC EDGAR ──────────────────────────────────────────
    try:
        from .edgar import load_from_edgar

        annual_df, entity_name, _ = load_from_edgar(normalized)
        annual_df = _validate_historical_df(annual_df)

        # Supplement with quarterly data from yfinance (EDGAR quarterly parsing is complex)
        quarterly_df = _load_quarterly_from_yfinance(normalized)

        # Market data profile (price, market cap, etc.) from market_data module
        profile: CompanyProfile | None = None
        try:
            profile = resolve_company_profile(_provider_symbol(normalized, "yfinance"))
        except Exception:
            pass

        # If market_data failed, build a minimal profile from the EDGAR entity name
        if profile is None:
            profile = CompanyProfile(symbol=normalized, name=entity_name)

        return HistoricalData(
            ticker=normalized,
            df=annual_df,
            annual_df=annual_df,
            quarterly_df=quarterly_df,
            profile=profile,
        )
    except Exception:
        pass

    # ── Fallback: yfinance ──────────────────────────────────────────
    return _load_from_yfinance(normalized)
