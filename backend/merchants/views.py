from rest_framework.generics import RetrieveAPIView

from payouts.serializers import MerchantMeSerializer

from .models import Merchant


class MerchantMeView(RetrieveAPIView):
    serializer_class = MerchantMeSerializer

    def get_object(self):
        return Merchant.objects.select_related("user").get(user=self.request.user)
