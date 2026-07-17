# Academic Comeback Package

A FastAPI backend + static-HTML frontend for a digital study-skills product: checkout via Flutterwave (bank transfer / card), a 52-email onboarding/nurture sequence, an affiliate referral program, a small sales-rep subsystem, and an admin dashboard for running all of it.

## Stack

- **Backend**: FastAPI (Python 3.11+), served by Uvicorn
- **Database**: MongoDB (via Motor, the async driver), typically MongoDB Atlas
- **Payments**: Flutterwave V4 (OAuth2 client-credentials flow)
- **Email**: SMTP via `smtplib`, templated with Jinja2 (`backend/templates/emails/`)
- **Background jobs**: APScheduler (email queue processing, affiliate payouts, subscription billing, affiliate nudges)
- **Frontend**: static HTML/CSS/vanilla JS, served directly by FastAPI — no build step
- **Tests**: pytest + pytest-asyncio (`tests/`), against a scratch MongoDB database

## Project layout

```
backend/
  main.py              FastAPI app, static file mounts, page routes
  config.py            Settings (env-var driven, see .env.example)
  database.py          Motor client + index creation
  routes/               API routers (payments, admin, affiliates, sales, library, ...)
  services/             Flutterwave client, email sending, payment completion, ...
  workers/               APScheduler jobs (email queue, payouts, nudges, subscriptions)
  schemas/               Pydantic request/response models
  middleware/            Auth (JWT + session cookie)
  utils/                 JWT/password helpers, rate limiting, error pages
  templates/emails/       Jinja2 email templates
frontend/               Static pages (index, admin dashboard, affiliate pages, sales pages)
deploy/Dockerfile        Production container image
tests/                    pytest suite
```

## Local setup

1. **Create a virtualenv and install dependencies**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # for running tests too:
   pip install -r requirements-dev.txt
   ```

2. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in real values — at minimum a MongoDB connection string, a Flutterwave sandbox/live client ID+secret, SMTP credentials, and a rotated `ADMIN_PASSWORD` (the app refuses to start in production with the shipped default). See `.env.example` for every key and what it's for.

3. **Run the app**

   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

   Visit `http://127.0.0.1:8000`. The admin dashboard is at `/admin`.

4. **Run the tests**

   ```bash
   pytest
   ```

   Each test gets its own throwaway MongoDB database (same cluster, unique name, dropped on teardown) — no separate test DB setup needed beyond a working `MONGODB_URL`.

## Deployment

Deployed on Render via `deploy/Dockerfile`. Environment variables are configured in Render's dashboard, not committed anywhere — keep the local `.env` and Render's env vars in sync manually when either changes.

## Checkout flow (high level)

1. Customer submits name/email on the homepage → `POST /api/payments/initialize` creates a Flutterwave bank-transfer virtual account (or starts a card charge).
2. Customer completes the transfer; the frontend polls `POST /api/payments/verify` while Flutterwave's webhook (`POST /api/payments/webhook`, signature-verified) also confirms the payment server-side — whichever arrives first wins, idempotently.
3. On confirmation, `services/payment_completion.py` creates the user, grants library access, enqueues the welcome email and the 52-email sequence, and records any affiliate referral.
4. Customer lands on `/welcome`, then `/library` using a durable per-customer access token (not a login).
