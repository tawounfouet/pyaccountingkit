# PLAN-09 : Garde-fous Architecturaux & Frontières Corporate Finance (Phase P2.3 / LOT-38)

Ce plan d'implémentation opérationnel couvre le lot **LOT-38** de la [Roadmap](../ROADMAP.md). Il formalise les garde-fous architecturaux, les tests d'étanchéité et la définition du contrat d'export de faits financiers (`FinancialFactsSnapshot`), sanctuarisant la séparation doctrinale entre la **comptabilité/analyse financière rétrospective** et la **finance d'entreprise prospective** (Corporate Finance externe).

---

## 1. Contexte & Spécifications de Référence

- **Specs applicables** :
  - Frontières Corporate Finance : [`23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md`](../specs/03_reporting-analytics/23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md)
  - Vision doctrinale & macro-architecture : [`01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`](../specs/00_cadrage/01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md)
  - Modèle de domaine & agrégats : [`02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`](../specs/00_cadrage/02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md)
  - Analyse financière & métriques comptables : [`14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`](../specs/03_reporting-analytics/14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md)
  - Cadre de tests d'architecture & qualité : [`11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`](../specs/05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md)
- **Doctrine financière de démarcation** :
  - 📊 [`Maxi_fiches_de_Gestion_financiere_de_l_entreprise.md`](../books/Maxi_fiches_de_Gestion_financiere_de_l_entreprise.md) (Démarcation stricte : distinction nette entre la partie I « Analyse financière de l'entreprise » [FRNG, BFR, CAF, ratios], traitée par PyAccountingKit, et les parties ultérieures « Choix d'investissement », « Structure financière & coût du capital », « Évaluation d'entreprise — DCF, WACC, multiples », « Ingénierie financière & LBO », formellement rejetées en dehors du périmètre du framework).
  - 🏛️ Référentiels & Schémas JSON : [`docs/referentiels/schemas/`](../referentiels/schemas/) (garantie contractuelle de non-contamination du cœur comptable par des métriques d'actualisation ou d'anticipation de marché).

---

## 2. Inventaire des Fichiers à Implémenter & Liens Relatifs

### 2.1. Contrat de Passerelle Externe (`ports`)
- Interface d'export de faits financiers certains :
  - [`src/pyaccountingkit/ports/valuation.py`](../../src/pyaccountingkit/ports/valuation.py) (`FinancialFactsSnapshot`, `FinancialFactsProviderProtocol`)

### 2.2. Analyse Financière Factuelle (`domain/analysis`)
- Métriques descriptives constatées (incluses dans le cœur) :
  - [`src/pyaccountingkit/domain/analysis/working_capital.py`](../../src/pyaccountingkit/domain/analysis/working_capital.py) (FRNG, BFR d'exploitation, Trésorerie nette)
  - [`src/pyaccountingkit/domain/analysis/functional_balance.py`](../../src/pyaccountingkit/domain/analysis/functional_balance.py) (Bilan fonctionnel)
  - [`src/pyaccountingkit/domain/analysis/indicators.py`](../../src/pyaccountingkit/domain/analysis/indicators.py) (SIG : EBE, REX, RN)

### 2.3. Suites de Tests de Séparation Architecturale (`tests`)
- Tests d'interdiction et de conformité :
  - [`tests/unit/test_architecture_boundaries.py`](../../tests/unit/test_architecture_boundaries.py) (Contrôle d'absence de symboles prospectifs)
  - [`tests/unit/domain/test_financial_facts_export.py`](../../tests/unit/domain/test_financial_facts_export.py) (Validation du contrat de données)

---

## 3. Détails Techniques & Extraits de Code Concrets

### 3.1. Contrat `FinancialFactsSnapshot` (`src/pyaccountingkit/ports/valuation.py`)
Ce contrat permet à des progiciels ou bibliothèques spécialisées de valorisation (DCF, multiples boursiers, LBO) d'extraire la vérité comptable historique sans introduire de dépendance circulaire ni polluer le domaine comptable.

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pyaccountingkit.core.money import Money


@dataclass(frozen=True)
class FinancialFactsSnapshot:
    """Synthèse patrimoniale et d'exploitation certifiée à une date d'arrêté donnée."""

    entity_id: str
    as_of_date: date

    # Bilan & Capitaux
    equity: Money                    # Capitaux propres comptables
    gross_financial_debt: Money      # Dettes financières brutes
    cash_and_equivalents: Money      # Disponibilités et trésorerie active
    net_financial_debt: Money        # Dette financière nette (Dette - Trésorerie)
    net_fixed_assets: Money          # Immobilisations nettes corporelles/incorporelles

    # Exploitation & Performance (SIG)
    ebitda: Money                    # EBE comptable constaté
    ebit: Money                      # Résultat d'exploitation (REX)
    net_income: Money                # Résultat net comptable
    depreciation_and_amort: Money    # Dotations aux amortissements et provisions

    # Équilibre Financier & Trésorerie
    working_capital_requirement: Money # BFR d'exploitation constaté
    operating_cash_flow: Money         # Capacité d'Autofinancement (CAF) historique
```

### 3.2. Test Automatisé de Garde d'Architecture (`tests/unit/test_architecture_boundaries.py`)
Ce test scanne le code source de `pyaccountingkit` et fait échouer la suite de tests si des notions prospectives ou de finance de marché sont détectées.

```python
import ast
from pathlib import Path
import pytest

FORBIDDEN_TERMS = [
    "wacc",
    "dcf",
    "discount_rate",
    "cost_of_capital",
    "terminal_value",
    "free_cash_flow_forecast",
    "black_scholes",
    "monte_carlo",
]


def test_no_corporate_finance_in_core():
    """Garantit l'absence totale de logique projective de Corporate Finance dans le coeur."""
    src_dir = Path(__file__).parents[2] / "src" / "pyaccountingkit"
    violations = []

    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN_TERMS:
            # Recherche stricte hors commentaires ou noms autorisés
            if f"def {term}" in content or f"class {term}" in content:
                violations.append(f"{py_file.name}: contient le symbole interdit '{term}'")

    assert not violations, "Violation des frontières Corporate Finance :\n" + "\n".join(violations)
```

---

## 4. Matrice des Responsabilités Doctrinales

| Domaine | Dans PyAccountingKit (Comptabilité & Analyse) | Hors de PyAccountingKit (Outils Tiers de Finance) |
| :--- | :--- | :--- |
| **Trésorerie** | Trésorerie active réelle, flux passés certifiés | Prévisions glissantes, plans de trésorerie prévisionnels |
| **Rentabilité** | Ratios ROCE / ROE historiques | Valorisation d'entreprise DCF, multiples de valorisation |
| **Financement** | Amortissement financier des emprunts au coût amorti | Coût moyen pondéré du capital (WACC / CMPC), modélisation LBO |
| **Risques** | Provisions pour risques et charges certaines/probables | Simulations stochastiques Monte Carlo, scénarios de marché |

---

## 5. Definition of Done (DoD Spécifique)

- [ ] Aucun concept de WACC, DCF, TRI (IRR) ou VAN (NPV) n'est implémenté dans le cœur de PyAccountingKit.
- [ ] Le contrat `FinancialFactsSnapshot` est validé et exporte les grandeurs comptables exactes.
- [ ] Les tests d'inviolabilité des frontières (`test_architecture_boundaries.py`) s'exécutent en CI sur chaque pull request.

---

## 6. Procédure de Recette Exécutable

```bash
# Contrôle de conformité des frontières d'architecture
pytest tests/unit/test_architecture_boundaries.py -v

# Validation de l'extraction des faits financiers
pytest tests/unit/domain/test_financial_facts_export.py -v
```
