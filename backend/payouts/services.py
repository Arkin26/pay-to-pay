from __future__ import annotations

from django.db.models import BigIntegerField, Case, F, Sum, When

from merchants.models import Merchant

from .models import IdempotencyRecord, LedgerEntry, Payout


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


def calculate_held_balance_paise(merchant: Merchant) -> int:
    row = (
        Payout.objects.filter(
            merchant=merchant,
            status__in=(Payout.STATUS_PENDING, Payout.STATUS_PROCESSING),
        )
        .aggregate(s=Sum("amount_paise"))
    )
    return row["s"] or 0


def calculate_total_paid_out_paise(merchant: Merchant) -> int:
    row = (
        Payout.objects.filter(
            merchant=merchant,
            status=Payout.STATUS_COMPLETED,
        )
        .aggregate(s=Sum("amount_paise"))
    )
    return row["s"] or 0


def create_payout_atomic(
    *,
    merchant: Merchant,
    bank_account_id: int,
    amount_paise: int,
    idempotency_key: str,
) -> tuple[Payout, bool]:
    """
    Create payout under merchant row lock. Returns (payout, created).
    If an active idempotent match exists, returns that payout and created=False.
    """
    from django.db import transaction
    from django.utils import timezone

    from .exceptions import InsufficientFunds
    from .models import BankAccount

    with transaction.atomic():
        locked_merchant = Merchant.objects.select_for_update().get(pk=merchant.pk)

        now = timezone.now()
        record = (
            IdempotencyRecord.objects.select_for_update()
            .filter(merchant=locked_merchant, key=idempotency_key)
            .first()
        )
        if record and record.expires_at > now and record.payout_id:
            existing = (
                Payout.objects.select_for_update()
                .filter(pk=record.payout_id, merchant=locked_merchant)
                .first()
            )
            if existing:
                return existing, False

        try:
            bank_account = BankAccount.objects.select_for_update().get(
                pk=bank_account_id,
                merchant=locked_merchant,
                is_active=True,
            )
        except BankAccount.DoesNotExist as exc:
            raise ValueError("Invalid or inactive bank account") from exc

        available = calculate_available_balance_paise(locked_merchant)
        if available < amount_paise:
            raise InsufficientFunds()

        payout = Payout.objects.create(
            merchant=locked_merchant,
            bank_account=bank_account,
            amount_paise=amount_paise,
            status=Payout.STATUS_PENDING,
            idempotency_key=idempotency_key,
            idempotency_expires_at=now + timezone.timedelta(hours=24),
            held_at=now,
        )
        LedgerEntry.objects.create(
            merchant=locked_merchant,
            entry_type=LedgerEntry.ENTRY_DEBIT,
            amount_paise=amount_paise,
            reference_id=payout.id,
        )

        expires_at = now + timezone.timedelta(hours=24)
        if record and record.expires_at <= now:
            # Allow reuse after expiry by overwriting the existing record.
            record.payout = payout
            record.expires_at = expires_at
            record.response_body = ""
            record.response_status = 201
            record.save(
                update_fields=[
                    "payout",
                    "expires_at",
                    "response_body",
                    "response_status",
                    "updated_at",
                ]
            )
        elif not record:
            IdempotencyRecord.objects.create(
                merchant=locked_merchant,
                key=idempotency_key,
                expires_at=expires_at,
                payout=payout,
                response_status=201,
                response_body="",
            )
        return payout, True
