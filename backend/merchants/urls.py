from django.urls import path

from .views import MerchantMeView

urlpatterns = [
    path("me/", MerchantMeView.as_view(), name="merchant-me"),
]
