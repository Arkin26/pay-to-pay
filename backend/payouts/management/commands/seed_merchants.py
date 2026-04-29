import random
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

from merchants.models import Merchant
from payouts.models import BankAccount, LedgerEntry

User = get_user_model()

MERCHANTS = (
    ("Acme Store", "acme@example.com"),
    ("Velocity Goods", "velocity@example.com"),
    ("Peak Commerce", "peak@example.com"),
)


class Command(BaseCommand):
    help = "Seed merchants with bank accounts and credit ledger entries."

    @transaction.atomic
    def handle(self, *args, **options):
        User.objects.filter(username__startswith="merchant_").delete()

        for name, email in MERCHANTS:
            u = User.objects.create_user(
                username=f"merchant_{email.split('@')[0]}",
                email=email,
                password="seed-password-change-me",
            )
            m = Merchant.objects.create(user=u, name=name, email=email)
            for i in range(2):
                BankAccount.objects.create(
                    merchant=m,
                    account_number=f"{100000 + m.id * 10 + i:08d}",
                    ifsc=f"SBIN0{m.id:06d}"[:11],
                    nickname=f"Account {i + 1}",
                    is_active=True,
                )
            target = random.randint(50_000, 200_000)
            total = 0
            while total < target:
                chunk = random.randint(3_000, 40_000)
                if total + chunk > target:
                    chunk = target - total
                if chunk <= 0:
                    break
                LedgerEntry.objects.create(
                    merchant=m,
                    entry_type=LedgerEntry.ENTRY_CREDIT,
                    amount_paise=chunk,
                    reference_id=uuid.uuid4(),
                )
                total += chunk
            tok, _ = Token.objects.get_or_create(user=u)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{name}: username={u.username} token={tok.key} total_credits_paise={total}"
                )
            )
