# Plan d'Implémentation 00 — Repository Bootstrap & Architecture Safety Net

> **Milestone cible** : Release `0.0.1`  
> **Lot couvert** : `LOT-00`  
> **Statut** : Cadrage & Socle initial  
> **Document d'architecture parent** : [`specs/05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`](../specs/05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md)

---

## 1. Objectif du plan & Références Doctrinales

Mettre en place le socle structurel, l'outillage de qualité de code, le harnais d'isolation architecturale et le pipeline CI/CD minimal de **PyAccountingKit**.  
Ce plan garantit que le framework démarre sur des bases saines, sans dette technique initiale, et impose des frontières strictes d'importation dès le premier commit.

- **Cadre doctrinal et méthodologique** :
  - 📖 [`Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md`](../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md) (Principes généraux de tenue des livres, force probante et intangibilité des journaux).
  - 🏛️ Référentiels & Schémas JSON de validation : [`docs/referentiels/`](../referentiels/) ([`schemas/`](../referentiels/schemas/) et [`datasets/`](../referentiels/datasets/)).
- **Actifs amont & données de qualification** :
  - 📦 Codebases amont : [`resources/`](../../resources/) ([`cfa_fra_django_mvp_sprint_7/`](../../resources/cfa_fra_django_mvp_sprint_7/) et [`regulatory-accounting-data-framework/`](../../resources/regulatory-accounting-data-framework/)) pour l'extraction initiale des jeux de tests et fixtures golden.

---

## 2. Inventaire des Fichiers à Implémenter & Liens Relatifs

### 2.1. Fichiers de Configuration & Packaging
- Configuration globale de build et outillage : [`pyproject.toml`](../../pyproject.toml)
- Définition des métadonnées du package racine : [`src/pyaccountingkit/__init__.py`](../../src/pyaccountingkit/__init__.py)
- Marqueur de conformité de typage PEP 561 : [`src/pyaccountingkit/py.typed`](../../src/pyaccountingkit/py.typed)
- Documentation légale et de contribution :
  - [`README.md`](../../README.md)
  - [`LICENSE`](../../LICENSE)
  - [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
  - [`CHANGELOG.md`](../../CHANGELOG.md)

### 2.2. Pipeline CI/CD & Automatisation
- Workflow d'intégration continue GitHub Actions : [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
- Script de vérification de parité et validation rapide : [`scripts/check_hygiene.sh`](../../scripts/check_hygiene.sh)

### 2.3. Harnais de Tests & Gardes Architecturaux
- Configuration racine de Pytest : [`tests/conftest.py`](../../tests/conftest.py)
- Test d'inviolabilité des frontières d'import : [`tests/unit/test_architecture_boundaries.py`](../../tests/unit/test_architecture_boundaries.py)
- Répertoire des fixtures techniques d'entrée : [`tests/fixtures/`](../../tests/fixtures/) (`accounting/`, `fec/`, `reporting/`, `regulatory/`)
- Initialisation des répertoires de fixtures golden : [`tests/golden/cfa_fra/__init__.py`](../../tests/golden/cfa_fra/__init__.py)

### 2.4. Arborescence de Données de Démonstration (`data/`)
- Gouvernance, doctrine et sécurité des données : [`data/README.md`](../../data/README.md)
- Échantillons publics didactiques versionnés : [`data/samples/`](../../data/samples/) (`accounting/`, `fec/`, `bank/`, `subledgers/`, `reconciliation/`, `consolidation/`)
- Répertoires non versionnés (ignorés par Git) : `data/local/`, `data/cache/`, `data/generated/`

---

## 3. Détails Techniques & Extraits de Code Concrets

### 3.1. Configuration de Référence `pyproject.toml`
Le fichier de configuration doit imposer le typage strict (`mypy --strict`), le formatage déterministe (`ruff`) et la gestion modulaire des extras sans dépendances obligatoires dans le cœur.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyaccountingkit"
version = "0.0.1"
description = "Doctrinal accounting engine and financial ledger framework in Python"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "PyAccountingKit Team" }]
classifiers = [
    "Development Status :: 2 - Pre-Alpha",
    "Intended Audience :: Financial and Insurance Industry",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]
dependencies = []

[project.optional-dependencies]
django = ["django>=4.2"]
sqlalchemy = ["sqlalchemy>=2.0", "psycopg[binary]>=3.1"]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
    "hypothesis>=6.90",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
    "build>=1.1.0",
    "twine>=5.0.0",
    "testcontainers[postgres]>=4.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "PT", "RET", "SIM"]
ignore = []

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --strict-markers"
```

### 3.2. Initialisation du Package et Point d'Entrée (`src/pyaccountingkit/__init__.py`)
L'import de base expose la version et prépare la structure des namespaces publics sans déclencher d'importations lourdes d'adaptateurs.

```python
"""PyAccountingKit - Core Accounting Framework."""

from __future__ import annotations

__version__ = "0.0.1"
__author__ = "PyAccountingKit Authors"
__all__ = ["__version__"]
```

### 3.3. Test de Garde Architecturale (`tests/unit/test_architecture_boundaries.py`)
Ce test garantit par inspection statique d'AST qu'aucun module du cœur (`core`, `domain`, `ports`) ne charge de framework externe ou de composant d'infrastructure.

```python
"""Tests de conformité et d'étanchéité des frontières architecturales."""

from __future__ import annotations

import ast
from pathlib import Path
import pytest

ROOT_SRC = Path(__file__).parents[2] / "src" / "pyaccountingkit"

FORBIDDEN_CORE_IMPORTS = {
    "django",
    "sqlalchemy",
    "flask",
    "fastapi",
    "requests",
    "aiohttp",
    "pyaccountingkit.adapters",
    "pyaccountingkit.integrations",
}


def get_imports_from_file(path: Path) -> list[str]:
    """Extrait tous les imports d'un fichier Python via l'AST."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_core_and_domain_isolation() -> None:
    """Valide que core et domain sont strictement agnostiques de toute infra."""
    core_dirs = [ROOT_SRC / "core", ROOT_SRC / "domain", ROOT_SRC / "ports"]
    violations: list[str] = []

    for directory in core_dirs:
        for py_file in directory.rglob("*.py"):
            imported_modules = get_imports_from_file(py_file)
            for mod in imported_modules:
                for forbidden in FORBIDDEN_CORE_IMPORTS:
                    if mod == forbidden or mod.startswith(f"{forbidden}."):
                        violations.append(f"{py_file.relative_to(ROOT_SRC)} -> import interdit: {mod}")

    assert not violations, "Violations d'architecture détectées:\n" + "\n".join(violations)
```

### 3.4. Pipeline CI/CD GitHub Actions (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: "pip"
      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install .[dev]
      - name: Lint and Formatting
        run: |
          ruff check src/ tests/
          ruff format --check src/ tests/
      - name: Strict Type Checking
        run: |
          mypy src/ tests/
      - name: Architecture Boundary Tests
        run: |
          pytest tests/unit/test_architecture_boundaries.py
      - name: Package Build Verification
        run: |
          python -m build
          twine check dist/*
```

---

## 4. Modèle de Validation et Gates Requises

- **`G0` (Local Hygiene Gate)** :
  - Formatage 100 % conforme à Ruff.
  - Typage strict validé par Mypy sans avertissement.
- **`G1` (Pull Request Gate)** :
  - Exécution du test `test_architecture_boundaries.py` au vert.
  - Aucune dépendance tierce dans `core`, `domain`, `ports`.
- **`G2` (Build Gate)** :
  - `python -m build` génère `pyaccountingkit-0.0.1.tar.gz` et `pyaccountingkit-0.0.1-py3-none-any.whl`.
  - `twine check dist/*` confirme l'absence d'erreurs de métadonnées.

---

## 5. Definition of Done (DoD Spécifique)

- [ ] `pyproject.toml` configuré et verrouillé pour Python `>=3.11`.
- [ ] Présence du marqueur `src/pyaccountingkit/py.typed`.
- [ ] Zéro dépendance obligatoire à l'installation (`pip install -e .` léger et immédiat).
- [ ] Test d'architecture automatisé validé en intégration continue.
- [ ] Workflow GitHub Actions fonctionnel en moins de 90 secondes.
- [ ] Répertoire `tests/golden/cfa_fra/` prêt pour l'accueil des fixtures de référence.

---

## 6. Procédure de Recette Exécutable

```bash
# 1. Vérification de l'installation en mode éditable vierge
python3 -m venv .venv_test
source .venv_test/bin/activate
pip install -e ".[dev]"

# 2. Contrôle de style et de typage strict
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/ tests/

# 3. Validation des barrières d'architecture
pytest tests/unit/test_architecture_boundaries.py

# 4. Packaging et vérification PyPI
python -m build
twine check dist/*

# Nettoyage
deactivate
rm -rf .venv_test dist/ build/ *.egg-info
```
