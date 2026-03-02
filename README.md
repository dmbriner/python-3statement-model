# Python 3-Statement Research And Valuation Platform

A public-facing Streamlit website for equity research, 3-statement forecasting, sensitivity analysis, and multi-method valuation.

## What it now includes

- Company search with ticker selection and logo support
- Annual and quarterly historical financial views
- Linked 3-statement forecasting across Base, Bull, and Bear cases
- Hover definitions and formulas for core line items
- Broader chart coverage across operations, balance sheet, cash flow, and valuation
- Four valuation methods: DCF, trading comps, precedent transactions, and LBO
- Research workspace for peer comps, analyst targets/estimates, earnings events, and precedent headlines
- Cloud deployment files for Streamlit-style hosting

## Data providers

- `SEC EDGAR` as the primary source for annual financial statements on US-listed companies
- `yfinance` as the fallback for annual statements and the default source for quarterly history, plus better non-US coverage
- `Financial Modeling Prep` for optional peer comps, analyst research, earnings events, precedent transaction headlines, and stronger cloud-ready search

To enable the research workspace and live market-data enrichment, set:

```bash
export ALPHA_VANTAGE_API_KEY=your_key_here
export FMP_API_KEY=your_key_here
```

Optional access control for a public deployment:

```bash
export APP_ACCESS_PASSWORD=choose_a_password
```

For the new multi-user flow, define users and saved API key profiles in `.streamlit/secrets.toml`. A template is included at `.streamlit/secrets.example.toml`.

Without `FMP_API_KEY`, the main modeling app still works because statement loading relies on SEC and Yahoo Finance first. `FMP_API_KEY` is optional and mainly improves search, comps, analyst data, and precedent coverage.

If you want materially richer keyed data than SEC + `yfinance`, the best fit for this codebase is `Financial Modeling Prep` because it already has integration points here. For institutional-grade coverage, vendors like FactSet, S&P Capital IQ, Bloomberg, or Refinitiv are stronger, but they require separate commercial integrations.

Obvious places to plug in keys:

- Local Streamlit runs: `.streamlit/secrets.toml`
- Local template for login/profile structure: `.streamlit/secrets.example.toml`
- General env-based runs: `.env` using `.env.example` as the template
- Render deployment: environment variables in `render.yaml` / Render dashboard

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to the cloud

This repo is already prepared for public deployment.

### Option 1: Render

Recommended for this project because it is better suited for environment variables and future API expansion.

1. Push this repo to GitHub.
2. Create a new `Web Service` in Render and connect the repo.
3. Render will detect [render.yaml](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/render.yaml).
4. Add `FMP_API_KEY` in Render environment settings.
5. Deploy and use the generated public URL.

Exact Git and deployment steps are in [DEPLOY.md](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/DEPLOY.md).

### Option 2: Streamlit Community Cloud

1. Push this repo to GitHub.
2. Create a new app in Streamlit Community Cloud.
3. Set the main file to `app.py`.
4. Add `FMP_API_KEY` in the app secrets or environment settings.
5. Deploy.

## Deployment files included

- [Procfile](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/Procfile)
- [render.yaml](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/render.yaml)
- [runtime.txt](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/runtime.txt)
- [.streamlit/config.toml](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/.streamlit/config.toml)
- [.env.example](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/.env.example)
- [DEPLOY.md](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/DEPLOY.md)

## Project structure

```text
app.py
run_model.py
requirements.txt
Procfile
render.yaml
runtime.txt

model_engine/
  analyzer.py
  config.py
  data.py
  export.py
  integrity.py
  line_items.py
  market_data.py
  model.py
  sensitivity.py
  valuation.py
```

## Remaining platform gap

The app is materially broader now, but it is still not a full institutional research platform. The largest remaining gap is deep transaction-detail data and fully automated peer-universe curation across sectors and geographies. Those can be added next if you choose a data vendor with broader coverage.
