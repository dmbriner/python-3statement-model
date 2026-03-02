# 3-Statement Platform

Professional equity research and valuation platform, now structured for a fully self-hosted public website.

- Frontend: `Next.js` + `TypeScript`
- Backend: `FastAPI`
- Database: `Postgres`
- Auth: `Clerk`
- Reverse proxy: `Caddy`
- Deployment: `Docker Compose` on your own VPS

The original Python modeling engine remains in [`model_engine/`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/model_engine). The new backend wraps it through API routes instead of serving it through Streamlit.

## Architecture

```text
frontend/   Next.js frontend
backend/    FastAPI API, config, DB models, service layer
db/         Postgres schema
deploy/     self-hosting config
model_engine/  existing Python financial modeling engine
docker-compose.yml
```

## Self-hosted stack

Run everything on one VPS:

- `caddy` handles HTTPS and reverse proxy
- `frontend` serves the Next.js app
- `backend` serves the FastAPI API
- `postgres` stores app data

Public routing:

- `https://yourdomain.com` -> frontend
- `https://yourdomain.com/api/...` -> backend

## Current backend API

- `GET /healthz`
- `GET /api/auth/config`
- `GET /api/auth/me`
- `GET /api/companies/search?query=AAPL`
- `POST /api/companies/analyze`
- `POST /api/exports/workbook`
- `GET/POST/PUT/DELETE /api/me/api-profiles`
- `GET/POST/PUT/DELETE /api/me/analyses`

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Self-hosted deployment

### 1. Prepare a VPS

Use Ubuntu on a VPS from a provider like Hetzner, DigitalOcean, or Linode.

Install:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. Clone the repo

```bash
git clone YOUR_REPO_URL
cd python-3statement-model
```

### 3. Configure env files

Create:

- `frontend/.env`
- `backend/.env`
- `deploy/.env` from [`deploy/selfhost.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/deploy/selfhost.env.example)

For self-hosted Docker Compose, set backend database access like:

```env
DATABASE_URL=postgresql+psycopg://statement_model:change_me@postgres:5432/statement_model
```

### 4. Run database migrations

Before first launch:

```bash
docker compose run --rm backend alembic upgrade head
```

### 5. Start the stack

```bash
docker compose --env-file deploy/.env up -d --build
```

### 6. DNS

Point your domain’s `A` record at the VPS public IP.

Then set in `deploy/.env`:

```env
DOMAIN=yourdomain.com
```

Caddy will handle HTTPS automatically.

## Environment variables

### Backend

See [`backend/.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend/.env.example).

Core variables:

- `DATABASE_URL`
- `CLERK_SECRET_KEY`
- `CLERK_PUBLISHABLE_KEY`
- `CLERK_JWT_ISSUER`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

### Frontend

See [`frontend/.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/frontend/.env.example).

Core variables:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`

### Deploy

See [`deploy/selfhost.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/deploy/selfhost.env.example).

Core variables:

- `DOMAIN`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

## Why this setup

- `Next.js` gives you maximum frontend design freedom
- `FastAPI` keeps the Python finance/modeling logic intact
- `Postgres` fits users, saved models, exports, and structured financial data
- `Docker Compose` keeps the whole site portable
- `Caddy` gives you a clean self-hosted HTTPS/public routing path

## Legacy app

[`app.py`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/app.py) is still present as the older Streamlit interface, but the recommended direction is the self-hosted `Next.js + FastAPI + Postgres` stack above.
