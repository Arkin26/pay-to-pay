# Playto — what this project is

This page explains the project in simple words. Read it once and you can tell someone else what Playto does without opening the code.

For setup steps and environment variables, open README.md.

For how money locking, idempotency, and the database work in detail, open EXPLAINER.md.

---

## One sentence

Playto helps merchants get paid to their bank accounts. It keeps a clear money record (a ledger), runs payouts step by step (pending, then processing, then done or failed), and uses background jobs so the website stays responsive.

---

## What problem it solves

Platforms that pay sellers or partners need three things:

- Balances must be right: you cannot pay out more than the merchant actually has.
- The same payout request must not run twice by accident (retries, double clicks).
- There should be a history you can trust: what was credited, debited, and what happened to each payout.

Playto builds those rules into the product.

---

## Main ideas

Merchant: a seller or business that receives payouts. Each merchant is linked to a login in the app.

Bank account: where the money is sent. A merchant can save more than one account.

Ledger: a list of money movements. Credits add money; debits reserve or pay out money. We figure out “how much is available” by adding up the ledger, instead of keeping a separate balance number that could get out of sync.

Payout: one attempt to send a fixed amount to one bank account. It has a status that moves forward (for example from pending to processing to completed or failed).

Money is stored in paise (100 paise = 1 rupee) as whole numbers so we avoid rounding mistakes.

---

## What happens when someone requests a payout

1. The merchant calls the API with a token and asks to send a certain amount to a bank account.
2. The system checks the rules and sets aside the money so two requests at the same time cannot overspend.
3. Background workers (Celery) run on a timer. They act like talking to a bank (in this project that part can be simulated). Then they mark the payout as completed or failed. Failed payouts cannot be flipped back to completed by mistake; see EXPLAINER.md if you want the exact rules.
4. The React dashboard shows merchants, balances, and activity. The API is what other systems should call for real integrations.

---

## Parts of the system

Django REST API: paths under /api/v1/ … login tokens, create and list payouts, and a “me” endpoint for the merchant with balances and bank accounts.

React web app: the dashboard people click through. In development it often talks to Django through a proxy.

PostgreSQL: the main database in production (for example on Supabase). For local work without Postgres, the backend can use SQLite.

Redis and Celery: Redis is a message broker; Celery runs scheduled tasks that process pending payouts and fix stuck ones.

Docker Compose can start the web app, workers, scheduler, and Redis together. The database is usually hosted separately.

---

## Short glossary

Derived balance: the balance we calculate from ledger rows, not a separate stored wallet field.

Idempotency key: a value the client sends so if the same payout is submitted twice, we return the same result instead of paying twice.

Token auth: the API expects a header like Authorization: Token followed by your key. Seed scripts can print tokens for local testing.

---

## Why it is built this way

The ledger plus strict payout statuses gives an audit trail and keeps money math honest.

Important requests lock data briefly so two clicks cannot both pass a balance check at once.

Heavy work runs in workers instead of inside one slow web request.

---

## Where to read more

README.md — how to install, run migrations, Celery, and tests.

EXPLAINER.md — deeper technical notes for developers.

---

## One line you can reuse

Playto is a payout system for merchants: ledger-backed balances, safe payout states, and background workers so platforms can pay banks without double-paying or losing a clear history.
