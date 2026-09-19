"""Alembic helpers for the SQLAlchemy/PostgreSQL adapter."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

_MIGRATIONS = Path(__file__).resolve().parent


def migration_config(database_url: str) -> Config:
    """Return an Alembic config bound to the packaged migration environment."""

    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade(database_url: str, revision: str = "head") -> None:
    """Upgrade one database using the packaged SQLAlchemy migration lineage."""

    command.upgrade(migration_config(database_url), revision)


__all__ = ["migration_config", "upgrade"]
