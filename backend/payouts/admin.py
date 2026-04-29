from django.contrib import admin

from .models import BankAccount, LedgerEntry, Payout


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "entry_type", "amount_paise", "created_at")
    list_filter = ("entry_type",)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "nickname", "account_number", "is_active")


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "merchant",
        "amount_paise",
        "status",
        "attempts",
        "created_at",
    )
    list_filter = ("status",)
