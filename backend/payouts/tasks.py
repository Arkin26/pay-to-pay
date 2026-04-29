import logging
import random
import uuid
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .exceptions import IllegalStateTransition
from .models import Payout

logger = logging.getLogger(__name__)


def _run_bank_simulation(payout: Payout) -> None:
    r = random.random()
    if r < 0.7:
        payout.transition_to(Payout.STATUS_COMPLETED)
    elif r < 0.9:
        payout.transition_to(Payout.STATUS_FAILED)
    else:
        if payout.attempts >= 3:
            payout.transition_to(Payout.STATUS_FAILED)
        else:
            payout.last_bank_sim_at = timezone.now()
            payout.save(update_fields=["last_bank_sim_at", "updated_at"])


@shared_task
def process_payout(payout_id: str) -> None:
    pk = uuid.UUID(str(payout_id))
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
        except IllegalStateTransition:
            logger.exception("Illegal payout transition for %s", pk)


@shared_task
def dispatch_pending_payouts() -> None:
    with transaction.atomic():
        ids = list(
            Payout.objects.filter(status=Payout.STATUS_PENDING)
            .select_for_update(skip_locked=True)
            .values_list("id", flat=True)[:100]
        )
    for pid in ids:
        process_payout.delay(str(pid))


@shared_task
def resume_stuck_processing_payouts() -> None:
    candidates = Payout.objects.filter(status=Payout.STATUS_PROCESSING).order_by(
        "created_at"
    )[:200]
    for pid in candidates.values_list("id", flat=True):
        resume_single_processing_payout.delay(str(pid))


@shared_task
def resume_single_processing_payout(payout_id: str) -> None:
    pk = uuid.UUID(str(payout_id))
    with transaction.atomic():
        try:
            p = Payout.objects.select_for_update().get(pk=pk, status=Payout.STATUS_PROCESSING)
        except Payout.DoesNotExist:
            return

        now = timezone.now()
        if not p.last_bank_sim_at:
            p.last_bank_sim_at = now
            p.save(update_fields=["last_bank_sim_at", "updated_at"])
            return

        delay_sec = 30 * (2 ** (p.attempts - 1))
        if now < p.last_bank_sim_at + timedelta(seconds=delay_sec):
            return

        p.attempts += 1
        p.last_bank_sim_at = now
        p.save(update_fields=["attempts", "last_bank_sim_at", "updated_at"])
        try:
            _run_bank_simulation(p)
        except IllegalStateTransition:
            logger.exception("Illegal payout transition on resume for %s", pk)
