# Playto Payout Engine — EXPLAINER

Short, implementation-focused answers.

## 1) Paste the balance query. Why derived and not stored?

Balance is computed from `LedgerEntry` rows only (credits minus debits). Money in transit is represented as debits at payout creation time, so there is no separate “stored balance” that can drift from the ledger.

```10:20:playto/backend/payouts/services.py
def calculate_available_balance_paise(merchant: Merchant) -> int:
    row = LedgerEntry.objects.filter(merchant=merchant).aggregate(
        total=Sum(
            Case(
                When(entry_type=LedgerEntry.ENTRY_CREDIT, then=F("amount_paise")),
                When(entry_type=LedgerEntry.ENTRY_DEBIT, then=-F("amount_paise")),
                output_field=BigIntegerField(),
            )
        )
    )
    return row["total"] or 0
```

**Why derived:** a stored balance would be a second source of truth that can disagree with ledger history after bugs, partial writes, or manual fixes. The ledger is the audit trail; the aggregate is the authoritative number.

## 2) Paste the `select_for_update()` block. What does it lock?

```62:76:playto/backend/payouts/services.py
    with transaction.atomic():
        locked_merchant = Merchant.objects.select_for_update().get(pk=merchant.pk)

        now = timezone.now()
        existing = (
            Payout.objects.filter(
                merchant=locked_merchant,
                idempotency_key=idempotency_key,
                idempotency_expires_at__gt=now,
            )
            .select_for_update()
            .first()
        )
        if existing:
            return existing, False
```

**What it locks:** the `Merchant` row for `merchant.pk` is locked for update for the duration of the atomic block. On PostgreSQL this is a row-level lock on `merchants_merchant`. If an idempotent payout row already exists and matches the filter, that payout row is also locked (`select_for_update()` on the payout queryset) before returning it.

The lock serializes payout creation for a single merchant so two simultaneous spend attempts cannot both read the same pre-debit balance.

## 3) How is idempotency checked? What happens on concurrent duplicate?

Inside the same `transaction.atomic()` block as the merchant lock, we look for an existing non-expired payout with the same `(merchant, idempotency_key)` (`idempotency_expires_at > now`). If found, we return that payout and the API responds with the same serialized payload and `201` (per product requirement).

**Concurrent duplicate:** two requests with the same key hit the same merchant row lock. The second blocks on `Merchant.objects.select_for_update()` until the first commits, then re-runs the lookup and returns the existing payout instead of inserting a second row.

## 4) Where is `failed -> completed` blocked? Paste the check.

`failed` is not a key in `LEGAL_TRANSITIONS`, so `LEGAL_TRANSITIONS.get(self.status, [])` is empty for a failed payout and any transition is rejected.

```63:66:playto/backend/payouts/models.py
    LEGAL_TRANSITIONS = {
        STATUS_PENDING: [STATUS_PROCESSING],
        STATUS_PROCESSING: [STATUS_COMPLETED, STATUS_FAILED],
    }
```

```119:123:playto/backend/payouts/models.py
    def transition_to(self, new_status):
        if new_status not in self.LEGAL_TRANSITIONS.get(self.status, []):
            raise IllegalStateTransition(
                f"{self.status} -> {new_status} is not allowed"
            )
```

## 5) One place AI wrote subtly wrong code — what was it, what did you fix?

**Celery payout pickup + bank simulation in one database transaction.** An early version ran the random “bank” outcome inside the same `transaction.atomic()` that moved `pending -> processing`. If the simulator raised (or an illegal transition occurred), Django rolled back the whole atomic block, undoing the move to `processing` even though the payout should remain in-flight for retries.

**Fix:** split `process_payout` into two short atomic sections: first commit `pending -> processing` and bump `attempts` / `last_bank_sim_at`, then open a second atomic block to run `_run_bank_simulation` so a simulation failure cannot roll back the processing transition.

```33:48:playto/backend/payouts/tasks.py
    with transaction.atomic():
        try:
            p = Payout.objects.select_for_update().get(pk=pk, status=Payout.STATUS_PENDING)
        except Payout.DoesNotExist:
            return
        p.transition_to(Payout.STATUS_PROCESSING)
        p.attempts += 1
        p.last_bank_sim_at = timezone.now()
        p.save(update_fields=["attempts", "last_bank_sim_at", "updated_at"])
    with transaction.atomic():
        try:
            p2 = Payout.objects.select_for_update().get(pk=pk, status=Payout.STATUS_PROCESSING)
        except Payout.DoesNotExist:
            return
        try:
            _run_bank_simulation(p2)
```

**Testing note:** the concurrent HTTP test is skipped on SQLite because row-locking semantics differ; run it with `FORCE_PG_TESTS=1` and a real Postgres `DATABASE_URL` (see `README.md`).
