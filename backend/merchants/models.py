from django.conf import settings
from django.db import models


class Merchant(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_profile",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()

    def __str__(self):
        return self.name
