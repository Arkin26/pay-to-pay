from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api-token-auth"),
    path("merchants/", include("merchants.urls")),
    path("payouts/", include("payouts.urls")),
]
