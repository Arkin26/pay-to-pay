import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from django.utils import timezone

from merchants.models import Merchant

from .exceptions import InsufficientFunds
from .models import IdempotencyRecord, Payout
from .serializers import PayoutCreateSerializer, PayoutSerializer
from .services import create_payout_atomic


class PaymentRequiredException(APIException):
    status_code = 402
    default_detail = "Insufficient funds"
    default_code = "insufficient_funds"


class PayoutListCreateView(ListCreateAPIView):
    serializer_class = PayoutSerializer

    def get_queryset(self):
        merchant = Merchant.objects.get(user=self.request.user)
        return Payout.objects.filter(merchant=merchant).select_related(
            "bank_account", "merchant"
        )

    def create(self, request, *args, **kwargs):
        raw_key = request.headers.get("Idempotency-Key") or request.META.get(
            "HTTP_IDEMPOTENCY_KEY"
        )
        if not raw_key:
            raise ValidationError({"Idempotency-Key": "This header is required."})
        try:
            idempotency_key = str(uuid.UUID(raw_key.strip()))
        except ValueError as exc:
            raise ValidationError(
                {"Idempotency-Key": "Must be a valid UUID string."}
            ) from exc

        ser = PayoutCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        merchant = Merchant.objects.get(user=request.user)

        # Fast path: exact replay for active idempotency keys (even if payout changed).
        now = timezone.now()
        record = (
            IdempotencyRecord.objects.filter(merchant=merchant, key=idempotency_key)
            .only("expires_at", "response_status", "response_body")
            .first()
        )
        if record and record.expires_at > now and record.response_body:
            import json

            return Response(
                data=json.loads(record.response_body),
                status=record.response_status or status.HTTP_201_CREATED,
            )

        try:
            payout, created = create_payout_atomic(
                merchant=merchant,
                bank_account_id=ser.validated_data["bank_account_id"],
                amount_paise=ser.validated_data["amount_paise"],
                idempotency_key=idempotency_key,
            )
        except InsufficientFunds:
            raise PaymentRequiredException()
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        data = PayoutSerializer(payout).data

        # Store exact response snapshot for replay.
        try:
            rec = IdempotencyRecord.objects.filter(
                merchant=merchant, key=idempotency_key, expires_at__gt=now
            ).first()
            if rec:
                import json

                rec.response_status = status.HTTP_201_CREATED
                rec.response_body = json.dumps(data, separators=(",", ":"))
                rec.save(update_fields=["response_status", "response_body", "updated_at"])
        except Exception:
            # Idempotency snapshot is best-effort; DB record already enforces key uniqueness.
            pass

        if created:
            from .tasks import process_payout

            if settings.ENABLE_ASYNC:
                process_payout.delay(str(payout.id))
            else:
                process_payout(str(payout.id))

        return Response(data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PayoutDetailView(RetrieveAPIView):
    serializer_class = PayoutSerializer

    def get_queryset(self):
        merchant = Merchant.objects.get(user=self.request.user)
        return Payout.objects.filter(merchant=merchant).select_related(
            "bank_account", "merchant"
        )
