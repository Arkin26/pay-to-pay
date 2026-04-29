from rest_framework import serializers

from merchants.models import Merchant

from .models import BankAccount, LedgerEntry, Payout
from .services import (
    calculate_available_balance_paise,
    calculate_held_balance_paise,
    calculate_total_paid_out_paise,
)


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ("id", "entry_type", "amount_paise", "reference_id", "created_at")


class BankAccountMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ("id", "nickname", "account_number", "ifsc")


class PayoutSerializer(serializers.ModelSerializer):
    bank_account = BankAccountMiniSerializer(read_only=True)

    class Meta:
        model = Payout
        fields = (
            "id",
            "merchant",
            "bank_account",
            "amount_paise",
            "status",
            "idempotency_key",
            "idempotency_expires_at",
            "attempts",
            "created_at",
            "updated_at",
            "held_at",
            "processing_started_at",
            "last_bank_sim_at",
        )
        read_only_fields = (
            "id",
            "merchant",
            "bank_account",
            "amount_paise",
            "status",
            "idempotency_key",
            "idempotency_expires_at",
            "attempts",
            "created_at",
            "updated_at",
            "held_at",
            "processing_started_at",
            "last_bank_sim_at",
        )


class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.IntegerField(min_value=1)


class MerchantMeSerializer(serializers.ModelSerializer):
    available_balance = serializers.SerializerMethodField()
    held_balance = serializers.SerializerMethodField()
    total_paid_out = serializers.SerializerMethodField()
    recent_ledger_entries = serializers.SerializerMethodField()
    bank_accounts = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = (
            "id",
            "name",
            "email",
            "available_balance",
            "held_balance",
            "total_paid_out",
            "recent_ledger_entries",
            "bank_accounts",
        )

    def get_available_balance(self, obj):
        return calculate_available_balance_paise(obj)

    def get_held_balance(self, obj):
        return calculate_held_balance_paise(obj)

    def get_total_paid_out(self, obj):
        return calculate_total_paid_out_paise(obj)

    def get_recent_ledger_entries(self, obj):
        qs = LedgerEntry.objects.filter(merchant=obj).order_by("-created_at")[:50]
        return LedgerEntrySerializer(qs, many=True).data

    def get_bank_accounts(self, obj):
        qs = BankAccount.objects.filter(merchant=obj, is_active=True).order_by("id")
        return BankAccountMiniSerializer(qs, many=True).data
