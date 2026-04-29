from django.urls import include, path

urlpatterns = [
    path("merchants/", include("merchants.urls")),
    path("payouts/", include("payouts.urls")),
]
