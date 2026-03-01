# Python 3-Statement Financial Model

A fully interactive financial modeling platform built in Python. Enter any stock ticker (or upload a CSV) and get a linked Income Statement, Balance Sheet, and Cash Flow projection — with DCF valuation, sensitivity analysis, and auto-generated interpretation.

**[Live Demo →](https://share.streamlit.io)** *(deploy your own with one click — see below)*

---

## What it does

Type a ticker like `AAPL`, `MSFT`, or `UPS`, click **Analyze Company**, and the app:

1. Pulls historical financials via `yfinance`
2. Calculates key historical metrics (revenue CAGR, avg margins, working capital days, leverage)
3. Auto-populates assumption sliders based on the company's own history
4. Projects all 3 financial statements 5 years forward across Base / Bull / Bear scenarios
5. Runs a DCF valuation with WACC sensitivity
6. Generates a written interpretation of the model output

All assumptions are fully adjustable — sliders update every chart and table instantly.

---

## Features

| Module | What it covers |
|--------|---------------|
| **Income Statement** | Revenue → Gross Profit → EBITDA → EBIT → Net Income, all scenarios |
| **Balance Sheet** | Full projected balance sheet with equity rollforward and integrity checks |
| **Cash Flow** | CFO / CFI / CFF breakdown, FCF build, cash sweep logic |
| **PP&E Schedule** | CapEx + depreciation → ending PP&E each year |
| **Debt Schedule** | Amortization, cash sweeps, interest on average debt |
| **Working Capital** | DSO / DIO / DPO → NWC change → CFO impact |
| **Sensitivity** | 2D heatmap (growth × margin) and tornado chart for FCF, EBITDA, or Net Income |
| **DCF Valuation** | PV of FCFs + Gordon Growth terminal value → EV → equity value → per-share price |
| **Interpretation** | Auto-generated narrative on growth, margins, leverage, coverage, and key risks |
| **Integrity Checks** | Balance sheet balance, cash reconciliation, covenant warnings |

---

## Screenshots

*(Add screenshots here after deploying)*

---

## Running locally

```bash
git clone https://github.com/yourusername/python-3statement-model
cd python-3statement-model

pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Deploying to the web (free)

1. Push this repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your repo → set main file to `app.py` → **Deploy**

You'll get a public URL like `yourname-3statement-model.streamlit.app` in ~2 minutes.

---

## Using a CSV instead of yfinance

If yfinance doesn't have data for a company (private company, international, etc.), upload a CSV matching this format:

```
year, revenue, cogs, opex, depreciation, interest_expense, tax_rate,
cash, accounts_receivable, inventory, accounts_payable, ppne, debt,
shares_outstanding, capex, equity, other_assets, other_liabilities
```

See [`data/ups_historical_template.csv`](data/ups_historical_template.csv) for a working example with UPS 2021–2024 data.

---

## Project structure

```
app.py                          # Streamlit dashboard (9 tabs)
run_model.py                    # CLI entry point (Excel export)
requirements.txt

model_engine/
  config.py                     # ModelAssumptions dataclass
  data.py                       # yfinance loader + CSV parser
  model.py                      # 3-statement projection engine
  analyzer.py                   # Historical metrics + smart defaults
  valuation.py                  # DCF + WACC sensitivity grid
  integrity.py                  # Balance sheet + cash flow checks
  sensitivity.py                # 2D heatmap + tornado chart
  export.py                     # Excel workbook export

data/
  ups_historical_template.csv   # Sample historical data (UPS 2021–2024)
```

---

## How the model works

```
Historical Data (yfinance or CSV)
        │
        ▼
  analyze_historical_data()  →  HistoricalMetrics
        │                        (CAGR, margins, WC days, leverage)
        ▼
  suggest_scenarios()        →  Base / Bull / Bear ModelAssumptions
        │
        ▼
  run_three_statement_model()
        │
        ├─ Income Statement   (Revenue → EBIT → Net Income)
        ├─ Balance Sheet      (Assets = Liabilities + Equity plug)
        ├─ Cash Flow          (CFO + CFI + CFF → ending cash)
        ├─ FCF                (NOPAT + D&A − CapEx − ΔNWC)
        ├─ PP&E Schedule
        ├─ Debt Schedule
        └─ Equity Schedule
        │
        ▼
  run_dcf()                  →  EV → Equity Value → Per Share
  check_integrity()          →  Balance + cash reconciliation checks
  build_tornado_chart()      →  Which assumptions move the needle most
```

---

## Key modeling assumptions

- **Bull scenario:** Base + 2.5pp revenue growth, +1.5pp gross margin each year
- **Bear scenario:** Base − 2.5pp revenue growth, −2.0pp gross margin each year
- **Cash sweep:** Excess cash (above 1.5× minimum buffer) automatically repays debt
- **Equity:** Computed as a plug (Assets − Liabilities) to ensure the balance sheet always balances; rollforward tracked separately
- **Terminal value:** Gordon Growth Model — `FCF_final × (1 + g) / (WACC − g)`

---

## Tech stack

- **Python 3.12**
- **Streamlit** — interactive dashboard
- **Plotly** — charts (line, bar, waterfall, heatmap, pie, tornado)
- **pandas / numpy** — data manipulation and modeling
- **yfinance** — live financial data
- **openpyxl** — Excel export

---

*Built as a portfolio project to demonstrate financial modeling, Python engineering, and data visualization.*
