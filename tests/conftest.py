"""conftest.py - Racine de configuration Pytest et fixtures globales pour PyAccountingKit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Retourne le chemin absolu du répertoire des fixtures de test."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def load_fixture(fixtures_dir: Path) -> Callable[[str], str]:
    """Helper pour charger le contenu textuel brut d'une fixture."""
    def _loader(relative_path: str) -> str:
        target = fixtures_dir / relative_path
        if not target.exists():
            raise FileNotFoundError(f"Fixture introuvable : {target}")
        return target.read_text(encoding="utf-8")

    return _loader


@pytest.fixture(scope="session")
def load_json_fixture(load_fixture: Callable[[str], str]) -> Callable[[str], Any]:
    """Helper pour charger et parser une fixture JSON."""
    def _json_loader(relative_path: str) -> Any:
        content = load_fixture(relative_path)
        return json.loads(content)

    return _json_loader
