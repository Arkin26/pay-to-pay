from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import NotFound

from payouts.serializers import MerchantMeSerializer

from .models import Merchant


class MerchantMeView(RetrieveAPIView):
    serializer_class = MerchantMeSerializer

    def get_object(self):
        try:
            return Merchant.objects.select_related("user").get(user=self.request.user)
        except Merchant.DoesNotExist as exc:
            raise NotFound("Merchant profile not found for this user.") from exc
