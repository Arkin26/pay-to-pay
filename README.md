# Playto Payout Engine

Full-stack payout management: Django REST Framework + React dashboard, PostgreSQL (Supabase-hosted) for money integrity, Celery + Redis for payout processing.

## Repository layout

- `backend/` — Django project (`playto.settings` reads `DATABASE_URL` / `SUPABASE_DB_URL` from `.env`)
- `frontend/` — React 18 + Vite + Tailwind
- `docker-compose.yml` — Django web, Celery worker, Celery beat, Redis (Postgres/Supabase is external)

## Connect Supabase (PostgreSQL)

Supabase gives a pooled or direct Postgres URI. Typical formats:

- `postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres`
- Session pooler (port `5432`) or transaction pooler (often port `6543`) — use the string from **Project Settings → Database → Connection string** in the Supabase dashboard.

Set it in `.env`:

```bash
DATABASE_URL=postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres
```

`settings.py` also accepts `SUPABASE_DB_URL` as an alias. For Supabase hosts, `sslmode=require` is applied by default via Django `OPTIONS` unless you override `PG_SSLMODE`.

Local development without Supabase: omit `DATABASE_URL` and Django uses `backend/db.sqlite3` (SQLite). Celery still expects Redis for workers.

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then edit DATABASE_URL / SECRET_KEY / REDIS_URL
python manage.py migrate
python manage.py seed_merchants
python manage.py runserver
```

Copy a printed **DRF token** into the React sidebar (or `VITE_AUTH_TOKEN`).

## Run migrations against Supabase

With `DATABASE_URL` pointing at Supabase:

```bash
cd backend
source .venv/bin/activate
python manage.py migrate
```

Use the **migrations** user/URI Supabase recommends if you use a restricted role.

## Celery worker + beat

Redis URL must be reachable (Railway/Render or local Redis):

```bash
cd backend
source .venv/bin/activate
export REDIS_URL=redis://localhost:6379/0

# worker
celery -A playto worker -l info

# beat (10s schedules defined in settings.py)
celery -A playto beat -l info
```

Docker Compose starts `redis`, `web`, `worker`, and `beat` together (configure `.env` with `DATABASE_URL` for Postgres).

## Seed data

```bash
cd backend
source .venv/bin/activate
python manage.py seed_merchants
```

Creates three merchants (Acme Store, Velocity Goods, Peak Commerce), two bank accounts each, random credit ledger entries totaling 50,000–200,000 paise per merchant, and prints `Token` values for API auth.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional `frontend/.env` — see `frontend/.env.example`. By default Vite proxies `/api` to `http://127.0.0.1:8000`.

## Tests

Default `python manage.py test` uses an in-memory SQLite database for speed.

```bash
cd backend
source .venv/bin/activate
python manage.py test payouts.tests -v 2
```

### Concurrent payout test (PostgreSQL)

`select_for_update()` semantics for the concurrent HTTP test are validated on **PostgreSQL**. On SQLite that test is skipped.

Run it against any Postgres (local Docker, Supabase, etc.):

```bash
cd backend
source .venv/bin/activate
export DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres
export FORCE_PG_TESTS=1
python manage.py test payouts.tests.PayoutConcurrencyLiveTests -v 2
```

### CI (runs concurrency test on Postgres)

GitHub Actions runs `payouts.tests` using a disposable Postgres service with `FORCE_PG_TESTS=1`, so the concurrency test does not skip in CI.

## API overview

- `POST /api/v1/payouts/` — headers: `Authorization: Token <key>`, `Idempotency-Key: <uuid>`; body: `{ "amount_paise": int, "bank_account_id": int }`
- `GET /api/v1/payouts/`
- `GET /api/v1/payouts/<uuid>/`
- `GET /api/v1/merchants/me/` — balances + recent ledger + active bank accounts

See `EXPLAINER.md` for money-path details.
# pay-to-pay
