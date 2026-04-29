import uuid

from django.db import models
from django.db import transaction
from django.utils import timezone

from merchants.models import Merchant

from .exceptions import IllegalStateTransition


class LedgerEntry(models.Model):
    ENTRY_CREDIT = "credit"
    ENTRY_DEBIT = "debit"
    ENTRY_TYPES = (
        (ENTRY_CREDIT, "credit"),
        (ENTRY_DEBIT, "debit"),
    )

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    entry_type = models.CharField(max_length=16, choices=ENTRY_TYPES)
    amount_paise = models.BigIntegerField()
    reference_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.entry_type} {self.amount_paise} {self.reference_id}"


class BankAccount(models.Model):
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="bank_accounts",
    )
    account_number = models.CharField(max_length=32)
    ifsc = models.CharField(max_length=11)
    nickname = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nickname or self.account_number}"


class Payout(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "pending"),
        (STATUS_PROCESSING, "processing"),
        (STATUS_COMPLETED, "completed"),
        (STATUS_FAILED, "failed"),
    )

    LEGAL_TRANSITIONS = {
        STATUS_PENDING: [STATUS_PROCESSING],
        STATUS_PROCESSING: [STATUS_COMPLETED, STATUS_FAILED],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="payouts",
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    amount_paise = models.BigIntegerField()
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    idempotency_key = models.CharField(max_length=64)
    idempotency_expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    held_at = models.DateTimeField(null=True, blank=True)
    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when entering processing; used for hung-timeout detection.",
    )
    last_bank_sim_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Updated by the Celery worker around each bank simulation.",
    )

    class Meta:
        indexes = [
            models.Index(fields=["merchant", "idempotency_key"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Payout {self.id} {self.status}"

    def _reverse_hold_debit(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.ENTRY_CREDIT,
            amount_paise=self.amount_paise,
            reference_id=uuid.uuid4(),
        )

    def transition_to(self, new_status):
        with transaction.atomic():
            if new_status not in self.LEGAL_TRANSITIONS.get(self.status, []):
                raise IllegalStateTransition(
                    f"{self.status} -> {new_status} is not allowed"
                )
            if new_status == self.STATUS_FAILED:
                # Refund and state transition must be atomic.
                self._reverse_hold_debit()
            if new_status == self.STATUS_PROCESSING:
                self.processing_started_at = timezone.now()
            self.status = new_status
            self.save(
                update_fields=[
                    "status",
                    "updated_at",
                    "processing_started_at",
                ]
            )


class IdempotencyRecord(models.Model):
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    key = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    response_status = models.IntegerField(default=201)
    response_body = models.TextField(blank=True, default="")
    payout = models.ForeignKey(
        "Payout",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="idempotency_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "key"], name="uniq_idem_key_per_merchant"
            )
        ]
        indexes = [
            models.Index(fields=["merchant", "key"]),
            models.Index(fields=["expires_at"]),
        ]
