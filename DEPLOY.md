# Deployment Guide

## 1. Push to GitHub

Create a new GitHub repository, then run:

```bash
git init
git add .
git commit -m "Initial public research platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

If the repo already exists locally, only run the last three commands with your actual GitHub URL.

## 2. Deploy on Render

1. Sign in to Render.
2. Create a new `Web Service`.
3. Connect your GitHub repository.
4. Render should detect [render.yaml](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/render.yaml).
5. Add these environment variables:

```text
FMP_API_KEY=your_financial_modeling_prep_key
APP_ACCESS_PASSWORD=optional_password
```

6. Deploy and use the generated public URL.

## 3. Optional custom domain

After deployment, attach your own domain in Render settings, for example:

```text
research.yourdomain.com
```

## 4. Streamlit Community Cloud alternative

1. Push the repo to GitHub.
2. Create a new app in Streamlit Community Cloud.
3. Set the entrypoint to `app.py`.
4. Add `FMP_API_KEY` and optional `APP_ACCESS_PASSWORD`.

## 5. What the public website will expose

- Home / landing page
- Company research workspace
- Historical annual and quarterly views
- Forecast model
- Sensitivity analysis
- DCF, comps, precedents, and LBO valuation

## 6. What still requires a stronger backend if you want a real product

- User accounts
- Saved models
- Database-backed watchlists
- Team collaboration
- Premium transaction datasets
