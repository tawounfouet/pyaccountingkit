# PLAN-04 : Comptes Auxiliaires, Lettrage & Analyse Financière (Release 0.4.0)

Ce plan d'implémentation opérationnel couvre les lots **LOT-18 à LOT-20** de la [Roadmap](../ROADMAP.md). Il formalise la comptabilité opérationnelle des tiers (clients, fournisseurs), le lettrage comptable, la balance âgée et le moteur d'analyse financière rétrospective (SIG, BFR, CAF, ratios de solvabilité).

---

## 1. Contexte & Spécifications de Référence

- **Specs applicables** :
  - Comptes auxiliaires & opérationnels : [`15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md`](../specs/01_core-accounting/15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md)
  - Analyse financière & métriques comptables : [`14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`](../specs/03_reporting-analytics/14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md)
  - Invariants comptables : [`03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`](../specs/01_core-accounting/03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md)
  - Grand livre et balance : [`07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`](../specs/02_ledger-operations/07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md)
  - Frontières Corporate Finance : [`23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md`](../specs/03_reporting-analytics/23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md)
- **Doctrine comptable & Références financières** :
  - 📊 [`Maxi_fiches_de_Gestion_financiere_de_l_entreprise.md`](../books/Maxi_fiches_de_Gestion_financiere_de_l_entreprise.md) (Fiches 1 à 15 : Soldes Intermédiaires de Gestion - SIG, Capacité d'Autofinancement - CAF, Fonds de Roulement Net Global - FRNG, Besoin en Fonds de Roulement - BFR d'exploitation, délais de rotation DSO / DPO et ratios de solvabilité).
  - 📖 [`Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md`](../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md) (Opérations courantes avec les tiers, créances clients, dettes fournisseurs, lettrage comptable et balances âgées).
  - 📁 Datasets réglementaires de reporting : [`docs/referentiels/datasets/reporting/`](../referentiels/datasets/reporting/) (grilles de restitution et de regroupement des comptes pour les SIG et le bilan fonctionnel).

---

## 2. Inventaire des Fichiers à Implémenter & Liens Relatifs

### 2.1. Comptabilité Auxiliaire des Tiers (`domain/subledgers`)
- Gestion des tiers & comptes de sous-registres :
  - [`src/pyaccountingkit/domain/subledgers/parties.py`](../../src/pyaccountingkit/domain/subledgers/parties.py) (`ThirdParty`, `PartyRole` : Client, Fournisseur, Salarié)
  - [`src/pyaccountingkit/domain/subledgers/subledger.py`](../../src/pyaccountingkit/domain/subledgers/subledger.py) (`SubledgerAccount`, liaison Compte Collectif 411/401 $\leftrightarrow$ Compte Tiers)
  - [`src/pyaccountingkit/domain/subledgers/due_items.py`](../../src/pyaccountingkit/domain/subledgers/due_items.py) (`DueItem`, échéances, dates d'exigibilité)
  - [`src/pyaccountingkit/domain/subledgers/receivables.py`](../../src/pyaccountingkit/domain/subledgers/receivables.py) (`ReceivablesBook`, registre clients)
  - [`src/pyaccountingkit/domain/subledgers/payables.py`](../../src/pyaccountingkit/domain/subledgers/payables.py) (`PayablesBook`, registre fournisseurs)
- Lettrage, Règlements & Balances Âgées :
  - [`src/pyaccountingkit/domain/subledgers/matching.py`](../../src/pyaccountingkit/domain/subledgers/matching.py) (`MatchingGroup`, code lettrage `AA`, délettrage)
  - [`src/pyaccountingkit/domain/subledgers/settlements.py`](../../src/pyaccountingkit/domain/subledgers/settlements.py) (`Settlement`, imputation de paiements)
  - [`src/pyaccountingkit/domain/subledgers/allocations.py`](../../src/pyaccountingkit/domain/subledgers/allocations.py) (`PartialAllocation`, gestion des soldes résiduels)
  - [`src/pyaccountingkit/domain/subledgers/aging.py`](../../src/pyaccountingkit/domain/subledgers/aging.py) (`AgedBalance`, tranches : non échu, 0-30j, 30-60j, 60-90j, >90j)

### 2.2. Moteur d'Analyse Financière Rétrospective (`domain/analysis`)
- Métriques d'exploitation & de structure financière :
  - [`src/pyaccountingkit/domain/analysis/indicators.py`](../../src/pyaccountingkit/domain/analysis/indicators.py) (Soldes Intermédiaires de Gestion : Marge, VA, EBE, REX, RN)
  - [`src/pyaccountingkit/domain/analysis/working_capital.py`](../../src/pyaccountingkit/domain/analysis/working_capital.py) (FRNG, BFR d'exploitation, Trésorerie Nette)
  - [`src/pyaccountingkit/domain/analysis/functional_balance.py`](../../src/pyaccountingkit/domain/analysis/functional_balance.py) (Bilan Fonctionnel normalisé)
  - [`src/pyaccountingkit/domain/analysis/ratios.py`](../../src/pyaccountingkit/domain/analysis/ratios.py) (Ratios financiers : liquidité, solvabilité, DSO, DPO)
  - [`src/pyaccountingkit/domain/analysis/trends.py`](../../src/pyaccountingkit/domain/analysis/trends.py) (Analyses comparatives N / N-1)
  - [`src/pyaccountingkit/domain/analysis/analysis_snapshot.py`](../../src/pyaccountingkit/domain/analysis/analysis_snapshot.py) (`FinancialAnalysisSnapshot` scellé)

### 2.3. Suites de Tests Dédiées (`tests`)
- Tests unitaires :
  - [`tests/unit/domain/test_subledger.py`](../../tests/unit/domain/test_subledger.py)
  - [`tests/unit/domain/test_matching.py`](../../tests/unit/domain/test_matching.py)
  - [`tests/unit/domain/test_aged_balance.py`](../../tests/unit/domain/test_aged_balance.py)
  - [`tests/unit/domain/test_financial_analysis.py`](../../tests/unit/domain/test_financial_analysis.py)

---

## 3. Détails Techniques & Extraits de Code Concrets

### 3.1. Lettrage de Lignes Auxiliaires (`src/pyaccountingkit/domain/subledgers/matching.py`)

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pyaccountingkit.core.errors import UnbalancedMatchingError, InvalidMatchingLineError
from pyaccountingkit.core.identifiers import LineId
from pyaccountingkit.core.money import Money


@dataclass(frozen=True)
class MatchingLineReference:
    """Ligne auxiliaire candidate au lettrage."""

    line_id: LineId
    debit: Money
    credit: Money


@dataclass(frozen=True)
class MatchingGroup:
    """Groupe de lettrage équilibré (débit == crédit)."""

    code: str  # ex: "AA", "AB"
    matched_at: datetime
    matched_by_user_id: str
    lines: tuple[MatchingLineReference, ...]

    def __post_init__(self) -> None:
        if len(self.lines) < 2:
            raise InvalidMatchingLineError("Un lettrage requiert au minimum 2 lignes")
        tot_deb = sum((l.debit.amount for l in self.lines), Decimal("0.00"))
        tot_crd = sum((l.credit.amount for l in self.lines), Decimal("0.00"))
        if tot_deb != tot_crd:
            raise UnbalancedMatchingError(
                f"Lettrage {self.code} déséquilibré : Débit={tot_deb} != Crédit={tot_crd}"
            )
```

### 3.2. Calculateur de Balance Âgée (`src/pyaccountingkit/domain/subledgers/aging.py`)

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.due_items import DueItem


@dataclass(frozen=True)
class AgedBalanceBucket:
    """Ventilation de créances ou dettes par tranche de retard."""

    current: Money       # Non échu
    bucket_1_30: Money   # Retard 1 à 30 jours
    bucket_31_60: Money  # Retard 31 à 60 jours
    bucket_61_90: Money  # Retard 61 à 90 jours
    bucket_over_90: Money # Retard > 90 jours

    @property
    def total_overdue(self) -> Money:
        return self.bucket_1_30 + self.bucket_31_60 + self.bucket_61_90 + self.bucket_over_90


class AgedBalanceCalculator:
    """Calcule la balance âgée d'un tiers à une date d'arrêté donnée."""

    @staticmethod
    def compute(due_items: list[DueItem], as_of_date: date) -> AgedBalanceBucket:
        first_curr = due_items[0].remaining_amount.currency if due_items else None
        # Implémentation du dispatching par tranche d'écart en jours : (as_of_date - due_date).days
        ...
```

### 3.3. Équation Fondamentale du BFR & FRNG (`src/pyaccountingkit/domain/analysis/working_capital.py`)

$$\text{FRNG} = \text{Capitaux Permanents} - \text{Actif Immobilisé Brut}$$
$$\text{BFR} = \text{Actif Circulant d'Exploitation} - \text{Passif Circulant d'Exploitation}$$
$$\text{Trésorerie Nette} = \text{FRNG} - \text{BFR} = \text{Trésorerie Active} - \text{Trésorerie Passive}$$

```python
from __future__ import annotations

from dataclasses import dataclass
from pyaccountingkit.core.money import Money


@dataclass(frozen=True)
class WorkingCapitalMetrics:
    """Grandeurs caractéristiques de l'équilibre financier de l'entité."""

    frng: Money                 # Fonds de Roulement Net Global
    bfr_exploitation: Money     # Besoin en Fonds de Roulement d'Exploitation
    bfr_hors_exploitation: Money
    tresorerie_nette: Money

    def validate_identity(self) -> bool:
        """Vérifie l'identité fondamentale : TN == FRNG - BFR_total."""
        bfr_total = self.bfr_exploitation + self.bfr_hors_exploitation
        return self.tresorerie_nette == (self.frng - bfr_total)
```

---

## 4. Matrice des Gates & Critères de Qualité

- **`GA` (Accounting Invariants & Reconciliation)** :
  - Un lettrage valide requiert impérativement $\sum Débit = \sum Crédit$.
  - Interdiction de modifier ou supprimer un lettrage sans générer une trace de délettrage datée.
- **`GP` (Performance Gate)** :
  - Le calcul des balances âgées sur un grand livre auxiliaire de 50 000 pièces doit s'exécuter en temps linéaire $O(N)$ sans requêtes $N+1$.

---

## 5. Definition of Done (DoD Spécifique)

- [ ] Tout compte de tiers lettrable interdit le lettrage de lignes de devises différentes sans conversion préalable.
- [ ] La balance âgée classe fidèlement les créances échues et non échues à la date de référence choisie.
- [ ] Le calcul des Soldes Intermédiaires de Gestion (SIG) concorde exactement avec le Compte de Résultat certifié.
- [ ] L'égalité comptable $\text{Trésorerie Nette} = \text{FRNG} - \text{BFR}$ est vérifiée au centime près sur l'ensemble des jeux d'essai.

---

## 6. Procédure de Recette Exécutable

```bash
# Tests de comptabilité auxiliaire et lettrage
pytest tests/unit/domain/test_subledger.py -v
pytest tests/unit/domain/test_matching.py -v
pytest tests/unit/domain/test_aged_balance.py -v

# Tests de l'analyse financière (SIG, BFR, Ratios)
pytest tests/unit/domain/test_financial_analysis.py -v

# Typage strict
mypy src/pyaccountingkit/domain/subledgers src/pyaccountingkit/domain/analysis
```
