# Tickr Deployment Guide

## Goal

Deploy the app as:

- frontend on `Vercel`
- backend on `Railway`
- optional frontend path prefix `/tickr`

## Repo rename

Rename the GitHub repo itself to `tickr` if you want the project branding to match.

You cannot rename a repo to `dmbriner.github.io/tickr`. That string is a site path, not a valid repo name.

## 1. Create the database

Create a Postgres instance and copy `DATABASE_URL`.

## 2. Configure local secrets

Create and fill:

- `frontend/.env`
- `backend/.env`

Use [`frontend/.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/frontend/.env.example) and [`backend/.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend/.env.example) as templates.

## 3. Run migrations

```bash
cd backend
alembic upgrade head
```

## 4. Deploy the backend to Railway

Backend service settings:

- Root Directory: repo root
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

This app imports the shared [`model_engine/`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/model_engine) package from the repo root, so Railway should deploy the whole repo rather than only the `backend/` folder.

Backend variables:

- `DATABASE_URL`
- `CLERK_SECRET_KEY`
- `CLERK_PUBLISHABLE_KEY`
- `CLERK_JWT_ISSUER`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`
- `CORS_ORIGINS`
- `CORS_ORIGIN_REGEX`

Suggested CORS values:

- `CORS_ORIGINS=https://your-frontend.vercel.app`
- `CORS_ORIGIN_REGEX=https://.*\.vercel\.app`

## 5. Deploy the frontend to Vercel

Frontend project settings:

- Framework: `Next.js`
- Root Directory: `frontend`

Frontend variables:

- `NEXT_PUBLIC_API_BASE_URL=https://your-backend.up.railway.app/api`
- `NEXT_PUBLIC_APP_NAME=Tickr`
- `NEXT_PUBLIC_BASE_PATH=/tickr`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...`
- `CLERK_SECRET_KEY=sk_...`

## 6. Portfolio path reality

If your portfolio stays on `GitHub Pages` at `dmbriner.github.io`, it cannot directly host this full app at `/tickr`.

What this code change does give you:

- the frontend can now be built to run from `/tickr`
- you can mount it there later on a platform that supports path-based routing and rewrites

## 7. Verify

- `https://your-frontend.vercel.app/tickr`
- `https://your-backend.up.railway.app/healthz`
- sign in through Clerk
- create an API profile
- create a saved analysis
