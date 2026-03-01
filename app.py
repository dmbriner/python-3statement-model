"""Streamlit dashboard — Python-powered 3-Statement Model (any ticker)."""

from __future__ import annotations

import copy
import dataclasses
import io
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from model_engine import (
    ModelAssumptions,
    analyze_historical_data,
    build_multi_output_sensitivity,
    build_tornado_chart,
    check_integrity,
    load_historical_data,
    run_dcf,
    run_three_statement_model,
    suggest_scenarios,
    wacc_terminal_sensitivity,
)
from model_engine.data import HistoricalData

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SCENARIO_COLORS = {"Base": "#2563EB", "Bull": "#16A34A", "Bear": "#DC2626"}
SCENARIO_EMOJI  = {"Base": "⚖️", "Bull": "🐂", "Bear": "🐻"}
PROJ_YEARS = 5

SLIDER_DEFAULTS: dict = {
    "growth_y1":  0.05,
    "growth_yn":  0.03,
    "gm_y1":      0.25,
    "gm_yn":      0.25,
    "opex_pct":   0.15,
    "capex_pct":  0.05,
    "dep_pct":    0.12,
    "dso_days":   45,
    "dio_days":   15,
    "dpo_days":   30,
    "tax_rate":   0.24,
    "int_rate":   0.05,
    "div_payout": 0.30,
    "debt_amort": 500,
    "wacc":       0.09,
    "term_growth": 0.025,
}


# ─────────────────────────────────────────────────────────────────────────────
# Format helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fm(v: float) -> str:
    return f"${v:,.0f}M"


def _fp(v: float) -> str:
    return f"{v * 100:.1f}%"


def _millions_df(df: pd.DataFrame, exclude: list[str] | None = None) -> pd.DataFrame:
    """Format all numeric cols as $X,XXXM (except year and excluded cols)."""
    exclude = exclude or []
    out = df.copy()
    for col in out.columns:
        if col == "year" or col in exclude:
            continue
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].apply(lambda v: f"${v:,.0f}M" if not pd.isna(v) else "—")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Session state & assumption helpers
# ─────────────────────────────────────────────────────────────────────────────

def _init_session_state() -> None:
    """Set slider defaults once, on first run."""
    for key, val in SLIDER_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val
    if "metrics" not in st.session_state:
        st.session_state["metrics"] = None
    if "last_ticker" not in st.session_state:
        st.session_state["last_ticker"] = None


def _interp(y1: float, yn: float, n: int = PROJ_YEARS) -> list[float]:
    if n == 1:
        return [y1]
    step = (yn - y1) / (n - 1)
    return [y1 + step * i for i in range(n)]


def _build_base_asm() -> ModelAssumptions:
    """Construct ModelAssumptions from current sidebar slider session state."""
    s = st.session_state
    n = PROJ_YEARS
    return ModelAssumptions(
        projection_years=n,
        revenue_growth=_interp(float(s["growth_y1"]), float(s["growth_yn"]), n),
        gross_margin=_interp(float(s["gm_y1"]), float(s["gm_yn"]), n),
        opex_pct_revenue=[float(s["opex_pct"])] * n,
        capex_pct_revenue=[float(s["capex_pct"])] * n,
        depreciation_pct_ppne=float(s["dep_pct"]),
        tax_rate=float(s["tax_rate"]),
        interest_rate_on_debt=float(s["int_rate"]),
        dividend_payout_ratio=float(s["div_payout"]),
        dso_days=[float(s["dso_days"])] * n,
        dio_days=[max(float(s["dio_days"]), 1.0)] * n,
        dpo_days=[max(float(s["dpo_days"]), 1.0)] * n,
        debt_amortization=[float(s["debt_amort"])] * n,
        target_min_cash_pct_revenue=0.03,
    )


def _shift_asm(base: ModelAssumptions, g_shift: float, m_shift: float) -> ModelAssumptions:
    asm = copy.deepcopy(base)
    asm.revenue_growth = [min(max(g + g_shift, -0.05), 0.30) for g in base.revenue_growth]
    asm.gross_margin   = [min(max(m + m_shift, 0.03), 0.85) for m in base.gross_margin]
    return asm


def _asm_to_json(asm: ModelAssumptions) -> str:
    return json.dumps(dataclasses.asdict(asm), sort_keys=True)


# ─────────────────────────────────────────────────────────────────────────────
# Cached computations
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading historical data…")
def _load_data(ticker: str, csv_bytes: bytes | None) -> pd.DataFrame:
    if csv_bytes:
        hist = load_historical_data(ticker=ticker, csv_path=io.StringIO(csv_bytes.decode()))
    else:
        hist = load_historical_data(ticker=ticker)
    return hist.df


@st.cache_data(show_spinner="Running model…")
def _run_model(hist_json: str, ticker: str, asm_json: str):
    hist_df = pd.read_json(io.StringIO(hist_json))
    hist = HistoricalData(ticker=ticker, df=hist_df)
    asm = ModelAssumptions(**json.loads(asm_json))
    return run_three_statement_model(hist, asm)


@st.cache_data(show_spinner="Running sensitivity analysis (25 scenarios)…")
def _run_sensitivity(hist_json: str, ticker: str, asm_json: str, metric: str):
    hist_df = pd.read_json(io.StringIO(hist_json))
    hist = HistoricalData(ticker=ticker, df=hist_df)
    asm = ModelAssumptions(**json.loads(asm_json))
    return build_multi_output_sensitivity(hist, asm, output_metric=metric)


@st.cache_data(show_spinner="Building tornado chart…")
def _run_tornado(hist_json: str, ticker: str, asm_json: str, metric: str):
    hist_df = pd.read_json(io.StringIO(hist_json))
    hist = HistoricalData(ticker=ticker, df=hist_df)
    asm = ModelAssumptions(**json.loads(asm_json))
    return build_tornado_chart(hist, asm, output_metric=metric)


# ─────────────────────────────────────────────────────────────────────────────
# Reusable chart helpers
# ─────────────────────────────────────────────────────────────────────────────

_LAYOUT = dict(
    hovermode="x unified",
    height=370,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=50, b=10),
    plot_bgcolor="white",
    paper_bgcolor="white",
)


def _line(
    dfs: dict[str, pd.DataFrame],
    x: str,
    y: str,
    title: str,
    pct: bool = False,
) -> go.Figure:
    fig = go.Figure()
    for name, df in dfs.items():
        vals = df[y]
        texts = [_fp(v) for v in vals] if pct else [_fm(v) for v in vals]
        fig.add_trace(go.Scatter(
            x=df[x], y=vals,
            name=f"{SCENARIO_EMOJI[name]} {name}",
            mode="lines+markers",
            line=dict(color=SCENARIO_COLORS[name], width=2.5),
            marker=dict(size=7),
            text=texts,
            hovertemplate="%{text}<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(title=title, **_LAYOUT)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0",
                     tickformat=".0%" if pct else None)
    return fig


def _bar_hist(df: pd.DataFrame, x: str, y: str, title: str, color: str = "#351C15") -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df[x], y=df[y], marker_color=color,
        text=[_fm(v) for v in df[y]], textposition="outside",
        hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(title=title, height=320,
                      margin=dict(l=10, r=10, t=50, b=10),
                      plot_bgcolor="white", paper_bgcolor="white")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(visible=False)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1: Overview
# ─────────────────────────────────────────────────────────────────────────────

def tab_overview(hist_df: pd.DataFrame, ticker: str) -> None:
    st.markdown(f"""
    ### What are we modeling?
    This tool projects **{ticker}'s** financial statements **{PROJ_YEARS} years forward** using
    historical financials as the base and your custom assumptions about growth, margins, and capital.

    **The 3 linked statements:**
    - **Income Statement** → Revenue minus all costs = Net Income
    - **Balance Sheet** → Snapshot of assets owned and liabilities owed (always: Assets = Liabilities + Equity)
    - **Cash Flow Statement** → Reconciles profit to actual cash (profit ≠ cash!)
    """)

    st.divider()
    base = hist_df.sort_values("year").iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue (Latest yr)", _fm(base["revenue"]))
    c2.metric("Gross Margin", _fp((base["revenue"] - base["cogs"]) / base["revenue"]))
    c3.metric("Total Debt", _fm(base["debt"]))
    c4.metric("Cash", _fm(base["cash"]))

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            _bar_hist(hist_df, "year", "revenue", f"{ticker} — Historical Revenue ($M)"),
            use_container_width=True,
        )
    with col2:
        h2 = hist_df.copy()
        h2["Gross Margin"] = (h2["revenue"] - h2["cogs"]) / h2["revenue"]
        h2["EBIT Margin"] = (
            h2["revenue"] - h2["cogs"] - h2["opex"] - h2["depreciation"]
        ) / h2["revenue"]
        fig = go.Figure()
        for col, color in [("Gross Margin", "#351C15"), ("EBIT Margin", "#FFB500")]:
            fig.add_trace(go.Scatter(
                x=h2["year"], y=h2[col], name=col, mode="lines+markers",
                line=dict(color=color, width=2.5),
                text=[_fp(v) for v in h2[col]],
                hovertemplate="%{text}<extra>" + col + "</extra>",
            ))
        fig.update_layout(
            title=f"{ticker} — Historical Margins",
            height=320, hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=50, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(tickformat=".0%", showgrid=True, gridcolor="#f0f0f0"),
        )
        fig.update_xaxes(showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Raw Historical Data", expanded=False):
        st.dataframe(hist_df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2: Drivers
# ─────────────────────────────────────────────────────────────────────────────

def tab_drivers(metrics) -> None:
    if metrics is None:
        st.info(
            "Click **🔍 Analyze Company** in the sidebar to auto-populate assumptions "
            "from historical financials and see detailed driver analysis here."
        )
        st.markdown("""
        #### What are the 5 value drivers?
        Before building a forecast, you need to understand **what actually drives this business**:

        1. **Revenue Growth** — How fast is demand growing? What's the realistic ceiling?
        2. **Margins** — How much of each revenue dollar flows to profit?
        3. **Capital Intensity** — How much CapEx is needed to sustain/grow the business?
        4. **Working Capital** — How efficiently does the company manage cash tied up in operations?
        5. **Financing** — What does debt cost? How leveraged is the company?

        After analyzing, this tab will show calculated metrics for each driver with explanations.
        """)
        return

    st.markdown("### Historical Performance Analysis")
    st.markdown(
        "These metrics were automatically calculated from the company's own financial statements. "
        "They inform the assumption defaults loaded into the model."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue CAGR", _fp(metrics.revenue_growth_cagr))
    c2.metric("Avg Gross Margin", _fp(metrics.gross_margin_avg))
    c3.metric("Avg EBITDA Margin", _fp(metrics.ebitda_margin_avg))

    c4, c5, c6 = st.columns(3)
    c4.metric("Avg Interest Rate", _fp(metrics.interest_rate_avg))
    c5.metric("Avg Net Leverage", f"{metrics.net_leverage_avg:.1f}x EBITDA")
    c6.metric("Avg Interest Coverage", f"{metrics.interest_coverage_avg:.1f}x")

    st.divider()

    driver_cards = [
        ("📈 Revenue Growth",       metrics.growth_note),
        ("💰 Margins",              metrics.margin_note),
        ("🏗️ Capital Intensity",   metrics.capex_note),
        ("🔄 Working Capital",      metrics.wc_note),
        ("🏦 Financing",            metrics.financing_note),
    ]
    for title, note in driver_cards:
        with st.expander(title, expanded=True):
            st.markdown(note)

    st.divider()
    st.markdown("""
    #### How to interpret these drivers
    - **Revenue Growth:** A 2–4% CAGR is typical for mature, large-cap companies.
      Tech and healthcare can sustain 8–15%+. Negative CAGR signals business headwinds.
    - **Margins:** Higher gross margin = more pricing power or efficiency. EBITDA margins
      above ~20% are generally strong for most industries.
    - **Capital Intensity:** Low CapEx/Revenue (< 5%) = asset-light. High (> 10%) = capital-heavy
      like manufacturing, airlines, or telecom. High CapEx reduces free cash flow.
    - **Working Capital:** DSO measures how long customers take to pay. DIO measures how long
      inventory sits. DPO measures how long the company waits to pay suppliers.
      Cash Conversion Cycle = DSO + DIO − DPO. Lower is better.
    - **Financing:** Interest rate × Debt = interest burden. Net Debt/EBITDA > 4x is
      considered highly leveraged. EBIT/Interest < 2x signals covenant risk.
    """)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3: Income Statement
# ─────────────────────────────────────────────────────────────────────────────

def tab_income(outputs: dict) -> None:
    st.markdown("""
    ### Income Statement
    Shows how much **profit** the company earns. Flows top-down:
    **Revenue → Gross Profit → EBITDA → EBIT → EBT → Net Income**

    > **Gross Profit** = Revenue − COGS (cost to make the product/deliver the service)
    > **EBITDA** = Gross Profit − Operating Expenses (a proxy for operating cash flow)
    > **EBIT** = EBITDA − Depreciation (accounting cost of using long-lived assets)
    > **Net Income** = EBIT − Interest − Taxes
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            _line({n: o.income_statement for n, o in outputs.items()},
                  "year", "revenue", "Revenue — All Scenarios ($M)"),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            _line({n: o.income_statement for n, o in outputs.items()},
                  "year", "ebitda", "EBITDA — All Scenarios ($M)"),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(
            _line({n: o.income_statement for n, o in outputs.items()},
                  "year", "ebit", "EBIT — All Scenarios ($M)"),
            use_container_width=True,
        )
    with col4:
        st.plotly_chart(
            _line({n: o.income_statement for n, o in outputs.items()},
                  "year", "net_income", "Net Income — All Scenarios ($M)"),
            use_container_width=True,
        )

    st.divider()
    scen = st.selectbox("View full table for:", ["Base", "Bull", "Bear"], key="is_scen")
    is_df = outputs[scen].income_statement.copy()
    is_df["gross_margin_%"] = is_df["gross_profit"] / is_df["revenue"]
    is_df["ebitda_margin_%"] = is_df["ebitda"] / is_df["revenue"]
    is_df["net_margin_%"] = is_df["net_income"] / is_df["revenue"]

    display = _millions_df(is_df, exclude=["year", "gross_margin_%", "ebitda_margin_%", "net_margin_%", "eps"])
    for c in ["gross_margin_%", "ebitda_margin_%", "net_margin_%"]:
        display[c] = is_df[c].apply(_fp)
    display["eps"] = is_df["eps"].apply(lambda v: f"${v:.2f}")
    display.columns = [c.replace("_", " ").title() for c in display.columns]
    st.dataframe(display, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4: Balance Sheet
# ─────────────────────────────────────────────────────────────────────────────

def tab_balance_sheet(outputs: dict) -> None:
    st.markdown("""
    ### Balance Sheet
    A **snapshot** of what the company owns (assets) and owes (liabilities + equity) at year-end.

    **The fundamental equation:** Total Assets = Total Liabilities + Total Equity *(always)*

    > In this model, equity is computed as the residual (Assets − Liabilities) to ensure
    > the balance sheet always balances. The "equity rollforward" (NI − Dividends) is tracked
    > separately as an informational schedule. Any difference is unmodeled balance sheet items
    > (goodwill, deferred taxes, minority interest, etc.) — normal for simplified models.
    """)

    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="bs_scen")
    output = outputs[scen]
    bs = output.balance_sheet
    integ = check_integrity(output)

    if integ.all_clear:
        st.success("✅ All integrity checks passed.")
    else:
        for w in integ.warnings[:6]:
            st.warning(w)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Total Assets vs. Liabilities + Equity")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Total Assets", x=bs["year"], y=bs["total_assets"],
            marker_color="#2563EB",
            text=[_fm(v) for v in bs["total_assets"]], textposition="auto",
        ))
        fig.add_trace(go.Bar(
            name="Liabilities + Equity", x=bs["year"], y=bs["total_liabilities_and_equity"],
            marker_color="#16A34A", opacity=0.75,
            text=[_fm(v) for v in bs["total_liabilities_and_equity"]], textposition="auto",
        ))
        fig.update_layout(
            barmode="group", height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Equity Rollforward (NI − Dividends)")
        eq = output.equity_schedule
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="Beginning Equity", x=eq["year"], y=eq["beginning_equity"],
            marker_color="#93C5FD",
        ))
        fig2.add_trace(go.Bar(
            name="+ Net Income", x=eq["year"], y=eq["net_income"],
            marker_color="#4ADE80",
        ))
        fig2.add_trace(go.Bar(
            name="− Dividends", x=eq["year"], y=-eq["dividends"],
            marker_color="#FCA5A5",
        ))
        fig2.add_trace(go.Scatter(
            name="Ending Equity", x=eq["year"], y=eq["ending_equity"],
            mode="lines+markers", line=dict(color="#1E40AF", width=3),
            text=[_fm(v) for v in eq["ending_equity"]],
            hovertemplate="%{text}<extra>Ending Equity</extra>",
        ))
        fig2.update_layout(
            barmode="relative", height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        fig2.update_xaxes(showgrid=False)
        fig2.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"#### Full Balance Sheet — {scen} Scenario")
    display_cols = [
        "year", "cash", "accounts_receivable", "inventory", "other_assets", "ppne", "total_assets",
        "accounts_payable", "debt", "other_liabilities", "total_liabilities",
        "total_equity", "total_liabilities_and_equity", "bs_plug",
    ]
    bs_show = bs[[c for c in display_cols if c in bs.columns]].copy()
    formatted = _millions_df(bs_show, exclude=["year"])
    formatted.columns = [c.replace("_", " ").title() for c in formatted.columns]
    st.dataframe(formatted, use_container_width=True, hide_index=True)

    if integ.year_details:
        with st.expander("🔍 Integrity Check Detail", expanded=False):
            _target = ["year", "bs_imbalance_pct", "bs_plug", "cash_diff",
                       "net_leverage", "interest_coverage"]
            detail_df = pd.DataFrame(integ.year_details)
            detail_df = detail_df[[c for c in _target if c in detail_df.columns]]
            if not detail_df.empty:
                if "bs_imbalance_pct" in detail_df.columns:
                    detail_df["bs_imbalance_pct"] = detail_df["bs_imbalance_pct"].apply(
                        lambda v: f"{v * 100:.2f}%"
                    )
                for c in ["bs_plug", "cash_diff"]:
                    if c in detail_df.columns:
                        detail_df[c] = detail_df[c].apply(_fm)
                for c in ["net_leverage"]:
                    if c in detail_df.columns:
                        detail_df[c] = detail_df[c].apply(lambda v: f"{v:.1f}x")
                for c in ["interest_coverage"]:
                    if c in detail_df.columns:
                        detail_df[c] = detail_df[c].apply(lambda v: f"{v:.1f}x")
                detail_df.columns = [c.replace("_", " ").title() for c in detail_df.columns]
                st.dataframe(detail_df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 5: Cash Flow
# ─────────────────────────────────────────────────────────────────────────────

def tab_cash_flow(outputs: dict) -> None:
    st.markdown("""
    ### Cash Flow Statement
    Reconciles **net income to actual cash**. These differ because:
    - Depreciation is a **non-cash** expense (added back in CFO)
    - CapEx is a **cash outflow** not on the income statement (shown in CFI)
    - Working capital changes **tie up or release** cash

    **Three sections:**
    - **CFO (Operating):** Cash generated running the core business
    - **CFI (Investing):** Cash used for long-term assets (mainly CapEx)
    - **CFF (Financing):** Cash from/to debt holders and shareholders (repayments, dividends)
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            _line({n: o.cash_flow for n, o in outputs.items()},
                  "year", "cfo", "Operating Cash Flow ($M)"),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            _line({n: o.fcf for n, o in outputs.items()},
                  "year", "fcf", "Free Cash Flow ($M)"),
            use_container_width=True,
        )

    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="cf_scen")
    cf = outputs[scen].cash_flow

    fig = go.Figure()
    for label, col_name, color in [
        ("CFO", "cfo", "#2563EB"),
        ("CFI", "cfi", "#F97316"),
        ("CFF", "cff", "#7C3AED"),
    ]:
        fig.add_trace(go.Bar(
            name=label, x=cf["year"], y=cf[col_name], marker_color=color,
            text=[_fm(v) for v in cf[col_name]],
            hovertemplate="%{text}<extra>" + label + "</extra>",
        ))
    fig.add_trace(go.Scatter(
        name="Net Change in Cash", x=cf["year"], y=cf["net_change_cash"],
        mode="lines+markers", line=dict(color="#374151", width=2.5, dash="dot"),
        text=[_fm(v) for v in cf["net_change_cash"]],
        hovertemplate="%{text}<extra>Net Change</extra>",
    ))
    fig.update_layout(
        title=f"Cash Flow Components — {SCENARIO_EMOJI[scen]} {scen}",
        barmode="group", height=380, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"#### Full Cash Flow Table — {scen}")
    fmt = _millions_df(cf, exclude=["year"])
    fmt.columns = [c.replace("_", " ").title() for c in fmt.columns]
    st.dataframe(fmt, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 6: Schedules
# ─────────────────────────────────────────────────────────────────────────────

def tab_schedules(outputs: dict, base_asm: ModelAssumptions) -> None:
    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="sched_scen")
    output = outputs[scen]

    sub1, sub2, sub3, sub4 = st.tabs([
        "🏗️ PP&E", "🔄 Working Capital", "🏦 Debt", "📊 Equity Rollforward"
    ])

    with sub1:
        st.markdown("""
        ### PP&E (Property, Plant & Equipment) Schedule
        **Beginning PP&E + CapEx − Depreciation = Ending PP&E** (each year)

        > **Depreciation** is non-cash — it reduces profit but not cash.
        > **CapEx** is a cash outflow — it reduces cash but not current-year profit.
        > Together, they explain how the asset base evolves and why CFO > Net Income in asset-heavy businesses.
        """)
        ppe = output.ppe_schedule
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Beginning PP&E", x=ppe["year"], y=ppe["beginning_ppne"],
                             marker_color="#93C5FD"))
        fig.add_trace(go.Bar(name="+ CapEx", x=ppe["year"], y=ppe["capex"],
                             marker_color="#FFB500"))
        fig.add_trace(go.Bar(name="− Depreciation", x=ppe["year"], y=-ppe["depreciation"],
                             marker_color="#FCA5A5"))
        fig.add_trace(go.Scatter(name="Ending PP&E", x=ppe["year"], y=ppe["ending_ppne"],
                                 mode="lines+markers", line=dict(color="#351C15", width=3),
                                 text=[_fm(v) for v in ppe["ending_ppne"]],
                                 hovertemplate="%{text}<extra>Ending PP&E</extra>"))
        fig.update_layout(
            barmode="relative", height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            _millions_df(ppe, exclude=["year"]).rename(columns=lambda c: c.replace("_", " ").title()),
            use_container_width=True, hide_index=True,
        )

    with sub2:
        st.markdown("""
        ### Working Capital Schedule
        - **DSO (Days Sales Outstanding):** How long customers take to pay (AR/Revenue × 365)
        - **DIO (Days Inventory Outstanding):** How long inventory sits before sold (Inv/COGS × 365)
        - **DPO (Days Payable Outstanding):** How long the company takes to pay suppliers (AP/COGS × 365)

        **Cash Conversion Cycle = DSO + DIO − DPO** (lower = more cash-efficient)
        """)
        base_asm.normalize()
        years = output.balance_sheet["year"].tolist()
        wc_data = pd.DataFrame({
            "year": years,
            "DSO (days)": base_asm.dso_days[:len(years)],
            "DIO (days)": base_asm.dio_days[:len(years)],
            "DPO (days)": base_asm.dpo_days[:len(years)],
        })
        fig2 = go.Figure()
        for col, color in [("DSO (days)", "#2563EB"), ("DIO (days)", "#F97316"), ("DPO (days)", "#16A34A")]:
            fig2.add_trace(go.Scatter(
                x=wc_data["year"], y=wc_data[col], name=col, mode="lines+markers",
                line=dict(color=color, width=2),
                text=[f"{v:.0f} days" for v in wc_data[col]],
                hovertemplate="%{text}<extra>" + col + "</extra>",
            ))
        fig2.update_layout(
            title="Working Capital Days", height=320, hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=50, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        fig2.update_xaxes(showgrid=False)
        fig2.update_yaxes(showgrid=True, gridcolor="#f0f0f0", title="Days")
        st.plotly_chart(fig2, use_container_width=True)
        bs_wc = output.balance_sheet[
            ["year", "accounts_receivable", "inventory", "accounts_payable", "nwc"]
        ].copy()
        st.dataframe(
            _millions_df(bs_wc, exclude=["year"]).rename(columns=lambda c: c.replace("_", " ").title()),
            use_container_width=True, hide_index=True,
        )

    with sub3:
        st.markdown("""
        ### Debt Schedule
        **Beginning Debt − Scheduled Repayment ± Cash Sweep = Ending Debt**

        > **Cash sweep:** If projected cash exceeds 1.5× minimum buffer, excess automatically pays down debt.
        > If cash falls below minimum, a debt draw fills the gap. This mimics real treasury management.
        """)
        debt = output.debt_schedule
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(name="Beginning Debt", x=debt["year"], y=debt["beginning_debt"],
                              marker_color="#FCA5A5"))
        fig3.add_trace(go.Bar(name="+ Draw", x=debt["year"], y=debt["debt_draw"],
                              marker_color="#F97316"))
        fig3.add_trace(go.Bar(name="− Repayment", x=debt["year"], y=-debt["debt_repayment"],
                              marker_color="#4ADE80"))
        fig3.add_trace(go.Scatter(name="Ending Debt", x=debt["year"], y=debt["ending_debt"],
                                  mode="lines+markers", line=dict(color="#DC2626", width=3),
                                  text=[_fm(v) for v in debt["ending_debt"]],
                                  hovertemplate="%{text}<extra>Ending Debt</extra>"))
        fig3.update_layout(
            barmode="relative", height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        fig3.update_xaxes(showgrid=False)
        fig3.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(
            _millions_df(debt, exclude=["year"]).rename(columns=lambda c: c.replace("_", " ").title()),
            use_container_width=True, hide_index=True,
        )

    with sub4:
        st.markdown("""
        ### Equity Rollforward
        **Beginning Equity + Net Income − Dividends = Ending Equity** (each year)

        > Note: This rollforward starts from historical equity and compounds forward via retained earnings.
        > The balance sheet shows equity as a "plug" (Assets − Liabilities), which may differ from
        > the rollforward due to unmodeled items. The difference is shown as **bs_plug**.
        """)
        eq = output.equity_schedule
        st.dataframe(
            _millions_df(eq, exclude=["year"]).rename(columns=lambda c: c.replace("_", " ").title()),
            use_container_width=True, hide_index=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 7: Sensitivity
# ─────────────────────────────────────────────────────────────────────────────

def tab_sensitivity(
    outputs: dict,
    hist_df: pd.DataFrame,
    ticker: str,
    base_asm: ModelAssumptions,
) -> None:
    st.markdown("""
    ### Sensitivity & Scenario Analysis
    Stress-test the model by shocking assumptions to see which ones drive the most value.
    """)

    metric = st.selectbox(
        "Output metric",
        ["fcf", "ebitda", "net_income"],
        format_func=lambda x: {"fcf": "Free Cash Flow", "ebitda": "EBITDA", "net_income": "Net Income"}[x],
        key="sens_metric",
    )
    metric_label = {"fcf": "FCF", "ebitda": "EBITDA", "net_income": "Net Income"}[metric]

    c1, c2, c3 = st.columns(3)
    for col, name in zip([c1, c2, c3], ["Base", "Bull", "Bear"]):
        df = outputs[name].fcf if metric == "fcf" else outputs[name].income_statement
        col_key = "fcf" if metric == "fcf" else metric
        val = df[col_key].mean()
        col.metric(f"{SCENARIO_EMOJI[name]} {name} — Avg {metric_label}", _fm(val))

    st.divider()
    st.markdown("""
    #### 2D Sensitivity Heatmap
    Shows **average projected output** when revenue growth and gross margin are shifted simultaneously.
    Each cell = a separate model run with those shocks applied every year.
    """)

    hist_json = hist_df.to_json()
    asm_json = _asm_to_json(base_asm)
    sens_df = _run_sensitivity(hist_json, ticker, asm_json, metric)

    z = sens_df.values.astype(float)
    fig = px.imshow(
        z,
        x=[f"{v:+.0%}" for v in sens_df.columns],
        y=[f"{v:+.0%}" for v in sens_df.index],
        color_continuous_scale="RdYlGn",
        text_auto=".0f",
        labels={
            "x": "Gross Margin Shock",
            "y": "Revenue Growth Shock",
            "color": f"Avg {metric_label} ($M)",
        },
        title=f"Sensitivity: Avg {metric_label} ($M) — Revenue Growth × Gross Margin",
    )
    fig.update_traces(texttemplate="$%{z:,.0f}M", textfont_size=11)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("""
    #### Tornado Chart — What Matters Most?
    Each assumption is shocked by ±10% and the resulting change in average output is measured.
    **Longer bars = bigger leverage point.** Focus model scrutiny on the longest bars.
    """)

    tornado_df = _run_tornado(hist_json, ticker, asm_json, metric)
    # Already sorted ascending by impact_range — plotly h-bar puts first item at BOTTOM,
    # so smallest impact is at bottom and largest impact at top (correct tornado orientation)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        y=tornado_df["assumption"],
        x=tornado_df["high_vs_base"],
        name="High shock (+10%)",
        orientation="h",
        marker_color="#16A34A",
        text=[_fm(abs(v)) for v in tornado_df["high_vs_base"]],
        textposition="outside",
    ))
    fig2.add_trace(go.Bar(
        y=tornado_df["assumption"],
        x=tornado_df["low_vs_base"],
        name="Low shock (−10%)",
        orientation="h",
        marker_color="#DC2626",
        text=[_fm(abs(v)) for v in tornado_df["low_vs_base"]],
        textposition="outside",
    ))
    fig2.update_layout(
        barmode="overlay",
        title=f"Tornado: Impact on Avg {metric_label} vs. Base ($M)",
        height=max(300, len(tornado_df) * 55),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=120, t=50, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 8: Valuation (DCF)
# ─────────────────────────────────────────────────────────────────────────────

def tab_valuation(outputs: dict, hist_df: pd.DataFrame) -> None:
    st.markdown("""
    ### DCF Valuation
    The **Discounted Cash Flow (DCF)** model values the company as the present value of all
    future free cash flows, discounted at the **WACC** (cost of capital).

    > **WACC** = the blended return required by equity + debt investors. Higher WACC → lower value.
    > Typical public company WACC: 7–12%. Use the lower end for stable businesses, higher for riskier ones.

    > **Terminal Value** = value of all cash flows beyond Year 5, modeled as a growing perpetuity:
    > `TV = FCF_Year5 × (1 + g) / (WACC − g)`. Terminal value typically represents 60–80% of EV.
    """)

    col_w, col_g = st.columns(2)
    with col_w:
        wacc = st.slider(
            "WACC (cost of capital)", 0.05, 0.18, float(st.session_state.get("wacc", 0.09)),
            step=0.005, format="%.1f%%", key="wacc_slider",
        )
    with col_g:
        tg = st.slider(
            "Terminal Growth Rate", 0.00, 0.05,
            float(st.session_state.get("term_growth", 0.025)),
            step=0.005, format="%.1f%%", key="tg_slider",
        )

    if wacc <= tg:
        st.error("⚠️ WACC must be greater than Terminal Growth Rate for a finite DCF to work.")
        return

    scen = st.selectbox("Scenario to value", ["Base", "Bull", "Bear"], key="val_scen")
    output = outputs[scen]
    fcf_list = output.fcf["fcf"].tolist()
    ebitda_list = output.fcf["ebitda"].tolist()
    bs_last = output.balance_sheet.iloc[-1]
    net_debt = float(bs_last["debt"]) - float(bs_last["cash"])
    shares = float(hist_df.sort_values("year").iloc[-1]["shares_outstanding"])

    try:
        result = run_dcf(fcf_list, ebitda_list, wacc, tg, net_debt, shares)
    except ValueError as e:
        st.error(str(e))
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Enterprise Value", _fm(result.enterprise_value))
    c2.metric("Less: Net Debt", _fm(result.net_debt))
    c3.metric("Equity Value", _fm(result.equity_value))
    c4.metric("Value per Share", f"${result.value_per_share:,.2f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("PV of FCFs (Yr 1–5)", _fm(result.pv_fcf_sum))
    c6.metric("PV of Terminal Value", _fm(result.pv_terminal_value))
    c7.metric("Terminal Value % of EV", _fp(result.tv_pct_of_ev))
    c8.metric("Implied EV / EBITDA", f"{result.implied_ev_ebitda:.1f}x")

    # DCF waterfall
    st.markdown("#### DCF Bridge: From FCFs to Equity Value")
    fig_w = go.Figure(go.Waterfall(
        name="DCF Bridge",
        orientation="v",
        measure=["relative", "relative", "total", "relative", "total"],
        x=["PV of FCFs\n(Yr 1–5)", "PV of Terminal\nValue", "Enterprise\nValue",
           "Less:\nNet Debt", "Equity\nValue"],
        y=[result.pv_fcf_sum, result.pv_terminal_value, 0, -result.net_debt, 0],
        text=[_fm(result.pv_fcf_sum), _fm(result.pv_terminal_value), _fm(result.enterprise_value),
              _fm(-result.net_debt), _fm(result.equity_value)],
        textposition="outside",
        connector={"line": {"color": "#94A3B8"}},
        increasing={"marker": {"color": "#16A34A"}},
        decreasing={"marker": {"color": "#DC2626"}},
        totals={"marker": {"color": "#2563EB"}},
    ))
    fig_w.update_layout(
        height=400, margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig_w, use_container_width=True)

    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        pie_vals = [max(result.pv_fcf_sum, 0), max(result.pv_terminal_value, 0)]
        if sum(pie_vals) > 0:
            fig_pie = px.pie(
                names=["Near-term FCFs (Yr 1–5)", "Terminal Value"],
                values=pie_vals,
                title="EV Composition",
                color_discrete_sequence=["#2563EB", "#FFB500"],
                hole=0.4,
            )
            fig_pie.update_layout(height=300, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
    with col_p2:
        tv_pct = result.tv_pct_of_ev * 100
        st.markdown(f"""
        **Terminal Value is {tv_pct:.0f}% of Enterprise Value.**

        - **< 50%:** Unusual — near-term cash flows dominate (very high early FCF)
        - **60–80%:** Normal for mature, profitable businesses ✓
        - **> 85%:** Terminal value dominates — be careful with growth assumptions,
          since a small change in terminal growth rate will swing the valuation significantly
        """)

    # WACC × Terminal Growth sensitivity grid
    st.markdown("#### Equity Value per Share — WACC × Terminal Growth Sensitivity")
    st.markdown("How sensitive is valuation to your two most important DCF inputs?")
    with st.spinner("Building sensitivity grid…"):
        sens_grid = wacc_terminal_sensitivity(fcf_list, ebitda_list, net_debt, shares)
    z_grid = sens_grid.values.astype(float)
    fig_heat = px.imshow(
        z_grid,
        x=[f"{v:.1%}" for v in sens_grid.columns],
        y=[f"{v:.0%}" for v in sens_grid.index],
        color_continuous_scale="RdYlGn",
        text_auto=".1f",
        labels={"x": "Terminal Growth Rate", "y": "WACC", "color": "Per Share ($)"},
        title="Value per Share ($) — WACC × Terminal Growth",
    )
    fig_heat.update_traces(texttemplate="$%{z:.1f}", textfont_size=11)
    fig_heat.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_heat, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 9: Interpretation
# ─────────────────────────────────────────────────────────────────────────────

def tab_interpretation(outputs: dict, ticker: str, metrics) -> None:
    st.markdown("### Model Interpretation")
    st.markdown(
        "Auto-generated analysis based on the model's projected outputs. "
        "Use this as a starting framework — always overlay with qualitative business judgment."
    )

    scen = st.selectbox("Scenario to interpret", ["Base", "Bull", "Bear"], key="interp_scen")
    output = outputs[scen]
    is_df = output.income_statement
    bs_df = output.balance_sheet
    fcf_df = output.fcf
    n = len(is_df)

    # Computed values
    rev_y1 = is_df["revenue"].iloc[0]
    rev_yn = is_df["revenue"].iloc[-1]
    rev_cagr = (rev_yn / rev_y1) ** (1 / max(n - 1, 1)) - 1 if rev_y1 > 0 and n > 1 else 0

    gm_y1 = is_df["gross_profit"].iloc[0] / is_df["revenue"].iloc[0]
    gm_yn = is_df["gross_profit"].iloc[-1] / is_df["revenue"].iloc[-1]

    avg_fcf = fcf_df["fcf"].mean()
    avg_ebitda = is_df["ebitda"].mean()
    fcf_conv = avg_fcf / avg_ebitda if avg_ebitda > 0 else 0

    bs_y1 = bs_df.iloc[0]
    bs_yn = bs_df.iloc[-1]
    lev_y1 = (bs_y1["debt"] - bs_y1["cash"]) / is_df["ebitda"].iloc[0] if is_df["ebitda"].iloc[0] > 0 else 0
    lev_yn = (bs_yn["debt"] - bs_yn["cash"]) / is_df["ebitda"].iloc[-1] if is_df["ebitda"].iloc[-1] > 0 else 0

    ebit_yn = is_df["ebit"].iloc[-1]
    int_yn = is_df["interest_expense"].iloc[-1]
    cov_yn = ebit_yn / int_yn if int_yn > 0 else 999

    integ = check_integrity(output)

    # Narrative labels
    margin_dir = ("expanding" if gm_yn > gm_y1 + 0.005
                  else "compressing" if gm_yn < gm_y1 - 0.005
                  else "stable")
    lev_dir = "declining" if lev_yn < lev_y1 - 0.2 else "rising" if lev_yn > lev_y1 + 0.2 else "stable"
    cov_risk = "low" if cov_yn > 3 else ("medium" if cov_yn > 1.5 else "high")

    st.divider()
    st.markdown(f"""
    #### 📈 Revenue & Growth
    **{ticker}** projects revenue growing from **{_fm(rev_y1)}** (Year 1) to **{_fm(rev_yn)}** (Year {n}),
    implying a **{_fp(rev_cagr)} projected CAGR**.
    {f"This exceeds the trailing historical CAGR of {_fp(metrics.revenue_growth_cagr)}, "
     f"which embeds an assumption of acceleration or market share gains."
     if metrics and rev_cagr > metrics.revenue_growth_cagr + 0.01 else
     f"This is below or in line with the trailing historical CAGR "
     f"({_fp(metrics.revenue_growth_cagr)}), consistent with mean-reversion to more moderate growth."
     if metrics else ""}
    """)

    st.markdown(f"""
    #### 💰 Margin Profile
    Gross margins are **{margin_dir}** from **{_fp(gm_y1)}** (Year 1) to **{_fp(gm_yn)}** (Year {n}).
    {"Expansion reflects assumed pricing power, scale benefits, or a shift toward higher-margin products."
     if margin_dir == "expanding" else
     "Compression may reflect rising input costs, competition, or mix headwinds."
     if margin_dir == "compressing" else
     "Stable margins suggest a steady competitive position with no meaningful structural changes assumed."}
    """)

    st.markdown(f"""
    #### 💵 Cash Generation
    Average projected **Free Cash Flow** is **{_fm(avg_fcf)}** per year.
    FCF conversion (FCF / EBITDA) is **{_fp(fcf_conv)}** —
    {"**above** the ~60% benchmark, indicating capital-efficient operations."
     if fcf_conv > 0.6 else
     "**below** the ~60% benchmark, reflecting heavier CapEx and/or working capital consumption."}
    """)

    st.markdown(f"""
    #### 🏦 Leverage & Debt
    Net Debt/EBITDA starts at **{lev_y1:.1f}x** (Year 1) and {"ends" if lev_dir != "stable" else "remains"} at
    **{lev_yn:.1f}x** (Year {n}) — leverage is **{lev_dir}**.
    {"Declining leverage shows the business naturally deleverages as cash builds."
     if lev_dir == "declining" else
     "Rising leverage could signal aggressive investment, debt draws, or weak cash generation."
     if lev_dir == "rising" else ""}
    {"Leverage is within typical investment-grade thresholds (< 3x)." if lev_yn < 3
     else "Leverage above 3x is elevated — worth monitoring for covenant compliance." if lev_yn < 5
     else "Leverage above 5x is high-yield territory — heightened default risk if cash flows disappoint."}
    """)

    st.markdown(f"""
    #### 🔒 Interest Coverage
    EBIT/Interest in Year {n} is **{cov_yn:.1f}x** — covenant risk is **{cov_risk}**.
    {"Coverage above 3x indicates a comfortable cushion." if cov_yn > 3
     else "Coverage between 1.5x–3x is acceptable but leaves limited margin for error." if cov_yn >= 1.5
     else "Coverage below 1.5x is concerning — nearly all EBIT goes to interest payments."}
    """)

    st.divider()
    st.markdown("#### ✅ Model Integrity")
    if integ.all_clear:
        st.success("All integrity checks passed — model is internally consistent.")
    else:
        st.warning(f"{len(integ.warnings)} warning(s):")
        for w in integ.warnings:
            st.markdown(f"- {w}")

    if metrics:
        st.divider()
        st.markdown("#### ⚠️ Key Model-Derived Risks")
        risks = []
        if metrics and rev_cagr > metrics.revenue_growth_cagr + 0.02:
            risks.append(
                f"**Growth assumption risk:** Projected CAGR ({_fp(rev_cagr)}) materially exceeds "
                f"historical ({_fp(metrics.revenue_growth_cagr)}). Downside if growth disappoints."
            )
        if cov_yn < 2.0:
            risks.append(
                f"**Interest coverage risk:** Coverage of {cov_yn:.1f}x is thin. "
                f"An EBIT shortfall of ~{(1 - 1.5 / max(cov_yn, 0.01)) * 100:.0f}% "
                f"would breach the 1.5x threshold."
            )
        if lev_yn > 4.0:
            risks.append(
                f"**Leverage risk:** Net Debt/EBITDA of {lev_yn:.1f}x at end of projection "
                f"is above typical investment-grade thresholds."
            )
        if fcf_conv < 0.40:
            risks.append(
                f"**CapEx/NWC drag:** FCF conversion of {_fp(fcf_conv)} is low. "
                f"Significant capital is consumed before cash reaches equity holders."
            )
        if not risks:
            risks.append("No significant model-derived risks identified for this scenario.")
        for r in risks:
            st.markdown(f"- {r}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="3-Statement Model",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    [data-testid="metric-container"] {
        background: #f9fafb; border-radius: 8px; padding: 10px 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    _init_session_state()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("# 📊 3-Statement Model")
        st.markdown("*Python-powered financial modeling*")
        st.divider()

        st.markdown("### Data Source")
        ticker = st.text_input("Ticker symbol", value="UPS").upper()
        uploaded = st.file_uploader(
            "Or upload historical CSV", type=["csv"],
            help="Must match the column format in data/ups_historical_template.csv",
        )
        csv_bytes = uploaded.read() if uploaded else None

        analyze_clicked = st.button(
            "🔍 Analyze Company", use_container_width=True, type="primary",
            help="Load data and auto-populate assumption sliders from historical financials.",
        )
        st.divider()

        # Revenue Growth
        with st.expander("📈 Revenue Growth", expanded=True):
            st.slider("Year 1 Growth Rate", -0.10, 0.30, step=0.005, format="%.1f%%", key="growth_y1")
            st.slider(f"Year {PROJ_YEARS} Growth Rate", -0.10, 0.30, step=0.005, format="%.1f%%", key="growth_yn")
            st.caption("Linearly interpolated between Year 1 and Year N.")

        # Margins
        with st.expander("💰 Margins", expanded=True):
            st.slider("Gross Margin — Year 1", 0.05, 0.85, step=0.005, format="%.1f%%", key="gm_y1")
            st.slider(f"Gross Margin — Year {PROJ_YEARS}", 0.05, 0.85, step=0.005, format="%.1f%%", key="gm_yn")
            st.slider("OpEx % of Revenue", 0.01, 0.50, step=0.005, format="%.1f%%", key="opex_pct")

        # Capital Intensity
        with st.expander("🏗️ Capital Intensity", expanded=False):
            st.slider("CapEx % of Revenue", 0.01, 0.20, step=0.005, format="%.1f%%", key="capex_pct")
            st.slider("Depreciation % of PP&E", 0.03, 0.35, step=0.005, format="%.1f%%", key="dep_pct")

        # Working Capital
        with st.expander("🔄 Working Capital (days)", expanded=False):
            st.slider("DSO — Days to collect", 1, 120, step=1, key="dso_days")
            st.slider("DIO — Days inventory held", 1, 120, step=1, key="dio_days")
            st.slider("DPO — Days to pay suppliers", 1, 120, step=1, key="dpo_days")

        # Financing
        with st.expander("🏦 Financing", expanded=False):
            st.slider("Tax Rate", 0.10, 0.40, step=0.005, format="%.1f%%", key="tax_rate")
            st.slider("Interest Rate on Debt", 0.01, 0.15, step=0.005, format="%.1f%%", key="int_rate")
            st.slider("Dividend Payout Ratio", 0.00, 0.80, step=0.01, format="%.0f%%", key="div_payout")
            st.slider("Annual Debt Amortization ($M)", 0, 5000, step=50, key="debt_amort")

        st.divider()
        st.markdown("*🐂 Bull = Base +2.5pp growth, +1.5pp margin*")
        st.markdown("*🐻 Bear = Base −2.5pp growth, −2.0pp margin*")
        st.divider()
        st.markdown("*Built with Python · Streamlit · Plotly*")

    # ── Load data ─────────────────────────────────────────────────────────────
    try:
        hist_df = _load_data(ticker, csv_bytes)
    except Exception as e:
        st.error(f"Could not load data for **{ticker}**: {e}")
        st.info("Try a different ticker symbol, or upload a CSV file using the sidebar.")
        return

    # ── Analyze on button click ───────────────────────────────────────────────
    if analyze_clicked:
        try:
            hist_obj = HistoricalData(ticker=ticker, df=hist_df)
            metrics = analyze_historical_data(hist_obj)
            smart = suggest_scenarios(metrics, years=PROJ_YEARS)
            base_s = smart["Base"]

            # Push smart defaults into session state (sliders will pick these up on rerun)
            st.session_state["growth_y1"]  = round(float(base_s.revenue_growth[0]), 4)
            st.session_state["growth_yn"]  = round(float(base_s.revenue_growth[-1]), 4)
            st.session_state["gm_y1"]      = round(float(base_s.gross_margin[0]), 4)
            st.session_state["gm_yn"]      = round(float(base_s.gross_margin[-1]), 4)
            st.session_state["opex_pct"]   = round(float(base_s.opex_pct_revenue[0]), 4)
            st.session_state["capex_pct"]  = round(float(base_s.capex_pct_revenue[0]), 4)
            st.session_state["dep_pct"]    = round(float(base_s.depreciation_pct_ppne), 4)
            st.session_state["tax_rate"]   = round(float(base_s.tax_rate), 4)
            st.session_state["int_rate"]   = round(float(base_s.interest_rate_on_debt), 4)
            st.session_state["div_payout"] = round(float(base_s.dividend_payout_ratio), 4)
            st.session_state["dso_days"]   = max(int(round(base_s.dso_days[0])), 1)
            st.session_state["dio_days"]   = max(int(round(base_s.dio_days[0])), 1)
            st.session_state["dpo_days"]   = max(int(round(base_s.dpo_days[0])), 1)
            st.session_state["debt_amort"] = max(int(round(base_s.debt_amortization[0])), 0)
            st.session_state["metrics"]    = metrics
            st.session_state["last_ticker"] = ticker

            st.success(
                f"✅ Smart defaults loaded for **{ticker}**! "
                f"Sliders now reflect historical averages. Adjust any assumption and the model updates instantly."
            )
            st.rerun()
        except Exception as e:
            st.error(f"Analysis failed: {e}")

    metrics = st.session_state.get("metrics")
    if st.session_state.get("last_ticker") != ticker:
        metrics = None  # stale metrics from a different ticker

    # ── Build assumptions ─────────────────────────────────────────────────────
    base_asm = _build_base_asm()
    bull_asm = _shift_asm(base_asm, g_shift=+0.025, m_shift=+0.015)
    bear_asm = _shift_asm(base_asm, g_shift=-0.025, m_shift=-0.020)

    # ── Run models ────────────────────────────────────────────────────────────
    hist_json = hist_df.to_json()
    try:
        outputs = {
            "Base": _run_model(hist_json, ticker, _asm_to_json(base_asm)),
            "Bull": _run_model(hist_json, ticker, _asm_to_json(bull_asm)),
            "Bear": _run_model(hist_json, ticker, _asm_to_json(bear_asm)),
        }
    except Exception as e:
        st.error(f"Model error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return

    # ── Header metrics ────────────────────────────────────────────────────────
    st.markdown(f"## {ticker} — 3-Statement Financial Model")
    c1, c2, c3 = st.columns(3)
    for col, name in zip([c1, c2, c3], ["Base", "Bull", "Bear"]):
        avg_fcf = outputs[name].fcf["fcf"].mean()
        col.metric(f"{SCENARIO_EMOJI[name]} {name} — Avg FCF", _fm(avg_fcf))

    if not analyze_clicked and metrics is None:
        st.info(
            "💡 **Tip:** Click **🔍 Analyze Company** in the sidebar to auto-populate assumption "
            "sliders from historical data. Default assumptions are shown for now."
        )

    st.divider()

    # ── 9 Tabs ────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📈 Overview",
        "🎯 Drivers",
        "📋 Income Statement",
        "🏛️ Balance Sheet",
        "💵 Cash Flow",
        "🗂️ Schedules",
        "🔍 Sensitivity",
        "📐 Valuation",
        "💡 Interpretation",
    ])

    with tabs[0]:
        tab_overview(hist_df, ticker)
    with tabs[1]:
        tab_drivers(metrics)
    with tabs[2]:
        tab_income(outputs)
    with tabs[3]:
        tab_balance_sheet(outputs)
    with tabs[4]:
        tab_cash_flow(outputs)
    with tabs[5]:
        tab_schedules(outputs, base_asm)
    with tabs[6]:
        tab_sensitivity(outputs, hist_df, ticker, base_asm)
    with tabs[7]:
        tab_valuation(outputs, hist_df)
    with tabs[8]:
        tab_interpretation(outputs, ticker, metrics)


if __name__ == "__main__":
    main()
