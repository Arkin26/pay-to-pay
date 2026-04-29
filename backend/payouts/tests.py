import json
import unittest
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.contrib.auth import get_user_model
from django.db import connection
from django.db import transaction
from django.db.models import Sum
from django.test import LiveServerTestCase
from rest_framework.authtoken.models import Token

from merchants.models import Merchant
from payouts.models import BankAccount, LedgerEntry, Payout
from payouts.services import calculate_available_balance_paise

User = get_user_model()


@unittest.skipUnless(
    connection.vendor == "postgresql",
    "Concurrent payout test requires PostgreSQL row-level locking semantics",
)
class PayoutConcurrencyLiveTests(LiveServerTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="m_conc",
            email="c@example.com",
            password="pw",
        )
        self.merchant = Merchant.objects.create(
            user=self.user, name="Conc Merchant", email="c@example.com"
        )
        self.ba = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="12345678",
            ifsc="SBIN0001234",
            nickname="Main",
            is_active=True,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.ENTRY_CREDIT,
            amount_paise=10_000,
            reference_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        )
        self.token = Token.objects.create(user=self.user)

    def _post_payout(self, idem: str):
        url = f"{self.live_server_url}/api/v1/payouts/"
        body = json.dumps(
            {"amount_paise": 6000, "bank_account_id": self.ba.id}
        ).encode()
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Token {self.token.key}",
                "Idempotency-Key": idem,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_concurrent_payouts_only_one_succeeds(self):
        idem_a = "00000000-0000-4000-8000-0000000000a1"
        idem_b = "00000000-0000-4000-8000-0000000000b2"
        results = []

        def worker(key):
            status, body = self._post_payout(key)
            results.append((status, body))

        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = [
                ex.submit(worker, idem_a),
                ex.submit(worker, idem_b),
            ]
            for f in as_completed(futs):
                f.result()

        statuses = sorted(s for s, _ in results)
        self.assertEqual(statuses, [201, 402])

        debits = LedgerEntry.objects.filter(
            merchant=self.merchant, entry_type=LedgerEntry.ENTRY_DEBIT
        )
        self.assertEqual(debits.count(), 1)
        self.assertEqual(
            debits.aggregate(s=Sum("amount_paise"))["s"],
            6000,
        )
        self.assertEqual(calculate_available_balance_paise(self.merchant), 4000)


class PayoutInsufficientFundsLiveTests(LiveServerTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="m_insuf",
            email="f@example.com",
            password="pw",
        )
        self.merchant = Merchant.objects.create(
            user=self.user, name="Funds Merchant", email="f@example.com"
        )
        self.ba = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="22223333",
            ifsc="SBIN0002222",
            nickname="Main",
            is_active=True,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.ENTRY_CREDIT,
            amount_paise=5_000,
            reference_id=uuid.UUID("00000000-0000-4000-8000-000000000003"),
        )
        self.token = Token.objects.create(user=self.user)

    def test_insufficient_funds_returns_402(self):
        url = f"{self.live_server_url}/api/v1/payouts/"
        body = json.dumps(
            {"amount_paise": 6000, "bank_account_id": self.ba.id}
        ).encode()
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Token {self.token.key}",
                "Idempotency-Key": "00000000-0000-4000-8000-00000000feed",
            },
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=30)
        self.assertEqual(ctx.exception.code, 402)


class PayoutIdempotencyLiveTests(LiveServerTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="m_idem",
            email="i@example.com",
            password="pw",
        )
        self.merchant = Merchant.objects.create(
            user=self.user, name="Idem Merchant", email="i@example.com"
        )
        self.ba = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="87654321",
            ifsc="SBIN0004321",
            nickname="Main",
            is_active=True,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.ENTRY_CREDIT,
            amount_paise=50_000,
            reference_id=uuid.UUID("00000000-0000-4000-8000-000000000002"),
        )
        self.token = Token.objects.create(user=self.user)

    def test_same_idempotency_key_returns_same_response(self):
        key = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeee1234"
        url = f"{self.live_server_url}/api/v1/payouts/"
        body = json.dumps(
            {"amount_paise": 1000, "bank_account_id": self.ba.id}
        ).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.token.key}",
            "Idempotency-Key": key,
        }
        req1 = urllib.request.Request(url, data=body, method="POST", headers=headers)
        with urllib.request.urlopen(req1, timeout=30) as resp:
            self.assertEqual(resp.status, 201)
            first = resp.read()

        req2 = urllib.request.Request(url, data=body, method="POST", headers=headers)
        with urllib.request.urlopen(req2, timeout=30) as resp:
            self.assertEqual(resp.status, 201)
            second = resp.read()

        self.assertEqual(first, second)
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)

    def test_idempotency_replay_is_stable_even_if_payout_changes(self):
        key = "bbbbbbbb-cccc-4ddd-eeee-ffffffff9999"
        url = f"{self.live_server_url}/api/v1/payouts/"
        body = json.dumps({"amount_paise": 1000, "bank_account_id": self.ba.id}).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.token.key}",
            "Idempotency-Key": key,
        }

        req1 = urllib.request.Request(url, data=body, method="POST", headers=headers)
        with urllib.request.urlopen(req1, timeout=30) as resp:
            self.assertEqual(resp.status, 201)
            first = resp.read()

        # Mutate the payout in between calls (simulates async worker completion).
        p = Payout.objects.get(merchant=self.merchant)
        with transaction.atomic():
            locked = Payout.objects.select_for_update().get(pk=p.pk)
            locked.status = Payout.STATUS_COMPLETED
            locked.save(update_fields=["status", "updated_at"])

        req2 = urllib.request.Request(url, data=body, method="POST", headers=headers)
        with urllib.request.urlopen(req2, timeout=30) as resp:
            self.assertEqual(resp.status, 201)
            second = resp.read()

        self.assertEqual(first, second)
