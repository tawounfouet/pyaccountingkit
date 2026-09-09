from django.db import models


class TrialBalanceVariant(models.TextChoices):
    BEFORE_ADJUSTMENTS = "BEFORE_ADJUSTMENTS", "Balance avant ajustements"
    ADJUSTED = "ADJUSTED", "Balance ajustée"
    POST_CLOSING = "POST_CLOSING", "Balance post-clôture"
