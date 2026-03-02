# Self-Hosted Deployment Guide

## Target setup

- One VPS you control
- `Docker Compose`
- `Caddy` for HTTPS
- `Next.js` frontend
- `FastAPI` backend
- `Postgres`
- `Clerk` for auth

## 1. Provision the server

Use Ubuntu on a VPS.

Install Docker:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

## 2. Clone the repo

```bash
git clone YOUR_REPO_URL
cd python-3statement-model
```

## 3. Configure secrets

Create and fill:

- `frontend/.env`
- `backend/.env`
- `deploy/.env`

Use [`frontend/.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/frontend/.env.example), [`backend/.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend/.env.example), and [`deploy/selfhost.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/deploy/selfhost.env.example) as templates.

For Docker Compose, backend database access should target the internal Postgres service:

```env
DATABASE_URL=postgresql+psycopg://statement_model:change_me@postgres:5432/statement_model
```

## 4. DNS

Point your domain at the VPS public IP.

Then set:

```env
DOMAIN=yourdomain.com
```

in `deploy/.env`.

## 5. Run migrations

```bash
docker compose --env-file deploy/.env run --rm backend alembic upgrade head
```

## 6. Start the app

```bash
docker compose --env-file deploy/.env up -d --build
```

## 7. Verify

- `https://yourdomain.com`
- `https://yourdomain.com/api/healthz`

## 8. Common operations

Rebuild after code changes:

```bash
docker compose --env-file deploy/.env up -d --build
```

View logs:

```bash
docker compose logs -f
```

Run migrations after schema changes:

```bash
docker compose --env-file deploy/.env run --rm backend alembic upgrade head
```

## 9. Security notes

- change the default Postgres password
- keep ports `80` and `443` open, but do not expose Postgres publicly
- keep your Clerk secret key only in `backend/.env`
- back up the Postgres volume regularly
