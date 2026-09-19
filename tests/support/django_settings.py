"""Minimal Django settings for typing and PostgreSQL adapter qualification."""

from __future__ import annotations

import os

SECRET_KEY = "pyaccountingkit-test-only"
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "pyaccountingkit.adapters.django.apps.PyAccountingKitDjangoConfig",
]

if os.getenv("PYAK_POSTGRES_TEST") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("PYAK_DB_NAME", "pyaccountingkit"),
            "USER": os.getenv("PYAK_DB_USER", "pyaccountingkit"),
            "PASSWORD": os.getenv("PYAK_DB_PASSWORD", "pyaccountingkit"),
            "HOST": os.getenv("PYAK_DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("PYAK_DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
