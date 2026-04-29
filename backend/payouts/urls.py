from django.urls import path

from .views import PayoutDetailView, PayoutListCreateView

urlpatterns = [
    path("", PayoutListCreateView.as_view(), name="payout-list-create"),
    path("<uuid:pk>/", PayoutDetailView.as_view(), name="payout-detail"),
]
