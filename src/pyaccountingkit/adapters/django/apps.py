"""Django application configuration for the optional PostgreSQL adapter."""

from django.apps import AppConfig


class PyAccountingKitDjangoConfig(AppConfig):
    """Isolated Django app containing only PyAccountingKit persistence models."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "pyaccountingkit.adapters.django"
    label = "pyaccountingkit_django"
    verbose_name = "PyAccountingKit Django Adapter"


__all__ = ["PyAccountingKitDjangoConfig"]
