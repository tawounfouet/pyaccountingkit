# PLAN-02 : Référentiels, Plans de Comptes & Politiques Comptables (Release 0.2.0)

Ce plan d'implémentation opérationnel couvre les lots **LOT-10 à LOT-13** de la [Roadmap](../ROADMAP.md). Il formalise l'intégration des juridictions réglementaires (PCG France, SYSCOHADA), la modélisation du plan de comptes d'entreprise et les politiques d'évaluation et de comptabilisation.

---

## 1. Contexte & Spécifications de Référence

- **Specs applicables** :
  - Architecture des référentiels comptables : [`05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`](../specs/01_core-accounting/05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md)
  - Plan de comptes & règles de numérotation : [`06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`](../specs/01_core-accounting/06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md)
  - Politiques de comptabilisation & mesure : [`04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`](../specs/01_core-accounting/04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md)
  - Modèle de domaine & agrégats : [`02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`](../specs/00_cadrage/02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md)
  - Matrice d'intégration réglementaire : [`19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md`](../specs/04_integration-infra/19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md)
- **Doctrine comptable & Référentiels de données** :
  - 📖 [`Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md`](../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md) (Parties 2 & 3 : Nomenclatures, opérations courantes, coût historique vs juste valeur).
  - 🏛️ Schémas JSON de validation : [`docs/referentiels/schemas/`](../referentiels/schemas/) ([`standard.schema.json`](../referentiels/schemas/standard.schema.json), [`accounting-concept.schema.json`](../referentiels/schemas/accounting-concept.schema.json), [`concept-binding.schema.json`](../referentiels/schemas/concept-binding.schema.json), [`standard-relation.schema.json`](../referentiels/schemas/standard-relation.schema.json)).
  - 📁 Datasets réglementaires : [`docs/referentiels/datasets/`](../referentiels/datasets/) (`concepts/`, `structured/`, `raw/`).
  - 📦 Forge amont des données réglementaires : [`resources/regulatory-accounting-data-framework/`](../../resources/regulatory-accounting-data-framework/) (sources officielles, pipelines de normalisation et bundles normatifs).

---

## 2. Inventaire des Fichiers à Implémenter & Liens Relatifs

### 2.1. Référentiels Comptables Réglementaires (`domain/references`)
- Définition des standards juridictionnels :
  - [`src/pyaccountingkit/domain/references/standards.py`](../../src/pyaccountingkit/domain/references/standards.py) (Énumération `StandardType` : PCG_FRANCE, SYSCOHADA, IFRS)
  - [`src/pyaccountingkit/domain/references/hierarchy.py`](../../src/pyaccountingkit/domain/references/hierarchy.py) (`StandardNode`, classes 1 à 8, rubriques)
  - [`src/pyaccountingkit/domain/references/concepts.py`](../../src/pyaccountingkit/domain/references/concepts.py) (Concepts neutres : `Cash`, `TradePayables`, etc.)
  - [`src/pyaccountingkit/domain/references/relations.py`](../../src/pyaccountingkit/domain/references/relations.py) (Interdictions de solde inversé, contraintes parent/enfant)
  - [`src/pyaccountingkit/domain/references/crosswalks.py`](../../src/pyaccountingkit/domain/references/crosswalks.py) (Tables de correspondance entre standards)
  - [`src/pyaccountingkit/domain/references/snapshots.py`](../../src/pyaccountingkit/domain/references/snapshots.py) (`ReferenceSnapshot` scellé pour traçabilité)
  - [`src/pyaccountingkit/domain/references/capabilities.py`](../../src/pyaccountingkit/domain/references/capabilities.py) (`ReferenceCapabilitySet`)
- Contrat du port de référentiel :
  - [`src/pyaccountingkit/ports/references.py`](../../src/pyaccountingkit/ports/references.py) (`AccountingReferenceProviderProtocol`)

### 2.2. Plan de Comptes d'Entreprise (`domain/charts`)
- Modélisation des comptes et arborescence :
  - [`src/pyaccountingkit/domain/charts/company_account.py`](../../src/pyaccountingkit/domain/charts/company_account.py) (Agrégat `CompanyAccount`)
  - [`src/pyaccountingkit/domain/charts/company_chart.py`](../../src/pyaccountingkit/domain/charts/company_chart.py) (Agrégat racine `CompanyChartOfAccounts`)
  - [`src/pyaccountingkit/domain/charts/numbering.py`](../../src/pyaccountingkit/domain/charts/numbering.py) (`NumberingPolicy`, validation des longueurs et racines)
  - [`src/pyaccountingkit/domain/charts/regulatory_binding.py`](../../src/pyaccountingkit/domain/charts/regulatory_binding.py) (Validation d'alignement au standard)
  - [`src/pyaccountingkit/domain/charts/generation.py`](../../src/pyaccountingkit/domain/charts/generation.py) (Service d'initialisation de plan d'entreprise)

### 2.3. Politiques d'Évaluation & Comptabilisation (`domain/policies`)
- Règles doctrinales d'enregistrement :
  - [`src/pyaccountingkit/domain/policies/recognition.py`](../../src/pyaccountingkit/domain/policies/recognition.py) (`RecognitionPolicy`, dates de comptabilisation et exigibilité)
  - [`src/pyaccountingkit/domain/policies/measurement.py`](../../src/pyaccountingkit/domain/policies/measurement.py) (`MeasurementPolicy`, amortissements, provisions)
  - [`src/pyaccountingkit/domain/policies/policy_set.py`](../../src/pyaccountingkit/domain/policies/policy_set.py) (`CompanyPolicySet`, combinaison de règles par société)
  - [`src/pyaccountingkit/domain/policies/policy_trace.py`](../../src/pyaccountingkit/domain/policies/policy_trace.py) (`PolicyTrace`, justificatif d'évaluation)

### 2.4. Adaptateurs de Fourniture des Référentiels (`adapters/regulatory`)
- Implémentations du port `AccountingReferenceProviderProtocol` :
  - [`src/pyaccountingkit/adapters/regulatory/filesystem.py`](../../src/pyaccountingkit/adapters/regulatory/filesystem.py) (`LocalFilesystemReferenceAdapter`, lecture locale paramétrée)
  - [`src/pyaccountingkit/adapters/regulatory/package.py`](../../src/pyaccountingkit/adapters/regulatory/package.py) (`PackageReferenceAdapter`, bundle Python importé)
  - [`src/pyaccountingkit/adapters/regulatory/http.py`](../../src/pyaccountingkit/adapters/regulatory/http.py) (`HttpReferenceAdapter`, client distant avec cache `data/cache/`)
  - [`src/pyaccountingkit/adapters/regulatory/object_storage.py`](../../src/pyaccountingkit/adapters/regulatory/object_storage.py) (`ObjectStorageReferenceAdapter`, S3/GCS)

### 2.5. Suites de Tests Associées (`tests`)
- Fixtures d'entrée minimales et synthétiques :
  - [`tests/fixtures/regulatory/`](../../tests/fixtures/regulatory/) (fixtures réduites pour tester les contrats sans dépendance externe)
- Tests unitaires :
  - [`tests/unit/domain/test_reference_standards.py`](../../tests/unit/domain/test_reference_standards.py)
  - [`tests/unit/domain/test_company_chart.py`](../../tests/unit/domain/test_company_chart.py)
  - [`tests/unit/domain/test_numbering_policy.py`](../../tests/unit/domain/test_numbering_policy.py)
  - [`tests/unit/domain/test_policies.py`](../../tests/unit/domain/test_policies.py)
- Tests de cohérence réglementaire (Golden Oracles) :
  - [`tests/golden/regulatory/test_pcg_baseline.py`](../../tests/golden/regulatory/test_pcg_baseline.py)
  - [`tests/golden/regulatory/test_syscohada_baseline.py`](../../tests/golden/regulatory/test_syscohada_baseline.py)

---

## 3. Détails Techniques & Extraits de Code Concrets

### 3.1. Nœuds de Référentiel & Standards (`src/pyaccountingkit/domain/references/standards.py`)

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StandardType(str, Enum):
    PCG_FRANCE = "PCG_FRANCE"
    PCG_ASSOCIATIONS = "PCG_ASSOCIATIONS"
    SYSCOHADA = "SYSCOHADA"
    IFRS = "IFRS"


class AccountNature(str, Enum):
    ASSET = "ASSET"              # Actif
    LIABILITY = "LIABILITY"      # Passif
    EQUITY = "EQUITY"            # Capitaux Propres
    EXPENSE = "EXPENSE"          # Charge
    REVENUE = "REVENUE"          # Produit
    SPECIAL = "SPECIAL"          # Comptes spéciaux (engagements)


@dataclass(frozen=True)
class StandardNode:
    """Nœud officiel d'un plan de comptes type réglementaire."""

    code: str
    label: str
    nature: AccountNature
    standard: StandardType
    parent_code: str | None = None
    allows_direct_posting: bool = True
    must_be_debit_balance: bool = False
    must_be_credit_balance: bool = False
```

### 3.2. Compte d'Entreprise & Politique de Numérotation (`src/pyaccountingkit/domain/charts/company_account.py`)

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pyaccountingkit.core.errors import InvalidAccountNumberError
from pyaccountingkit.domain.references.standards import AccountNature, StandardType


@dataclass(frozen=True)
class NumberingPolicy:
    """Règles de validation du format des comptes de l'entité."""

    min_length: int = 4
    max_length: int = 10
    pattern: str = r"^[1-8][0-9A-Z]{3,9}$"

    def validate(self, account_number: str) -> None:
        if not (self.min_length <= len(account_number) <= self.max_length):
            raise InvalidAccountNumberError(
                f"Le compte {account_number} doit comporter entre {self.min_length} "
                f"et {self.max_length} caractères"
            )
        if not re.match(self.pattern, account_number):
            raise InvalidAccountNumberError(
                f"Le compte {account_number} ne respecte pas le format autorisé {self.pattern}"
            )


@dataclass(frozen=True)
class CompanyAccount:
    """Compte utilisé dans le grand livre d'une entité spécifique."""

    number: str
    name: str
    nature: AccountNature
    standard_binding: str | None = None  # Code rattaché dans le référentiel parent
    is_active: bool = True
    reconcilable: bool = False  # Lettrable (ex: 401, 411)

    def validate_with(self, policy: NumberingPolicy) -> None:
        policy.validate(self.number)
```

### 3.3. Contrat du Fournisseur de Référentiels (`src/pyaccountingkit/ports/references.py`)

```python
from __future__ import annotations

from typing import Protocol
from pyaccountingkit.domain.references.standards import StandardNode, StandardType
from pyaccountingkit.domain.references.snapshots import ReferenceSnapshot


class AccountingReferenceProviderProtocol(Protocol):
    """Port fournissant les plans de comptes officiels et les règles doctrinales."""

    def get_standard_node(self, standard: StandardType, code: str) -> StandardNode | None: ...

    def list_nodes_by_standard(self, standard: StandardType) -> list[StandardNode]: ...

    def get_snapshot(self, standard: StandardType, version: str) -> ReferenceSnapshot: ...
```

---

## 4. Matrice des Gates & Critères de Qualité

- **`GR` (Regulatory Compliance Gate)** :
  - Conformité stricte aux nomenclatures du PCG (Règlement ANC n° 2014-03) et SYSCOHADA révisé.
  - Vérification de l'intégrité des relations hiérarchiques (chaque compte rattaché doit avoir un parent valide dans le standard).
- **`GA` (Accounting Architecture Gate)** :
  - Découplage strict entre le référentiel abstrait (`domain/references`) et le plan opérationnel de l'entreprise (`domain/charts`).
  - Immutabilité des snapshots de référentiels utilisés lors de l'enregistrement des écritures.

---

## 5. Definition of Done (DoD Spécifique)

- [ ] L'arbre hiérarchique du PCG France (classes 1 à 7) est chargé et testé sans nœuds orphelins.
- [ ] Le plan SYSCOHADA (classes 1 à 8) est supporté avec validation des règles de débit/crédit interdits.
- [ ] La politique de numérotation (`NumberingPolicy`) rejette tout numéro non conforme.
- [ ] Le rattachement réglementaire (`regulatory_binding`) interdit l'utilisation d'un compte racine non reconnu par la juridiction active.
- [ ] `CompanyPolicySet` permet de configurer explicitement les règles d'évaluation (coût historique vs juste valeur).

---

## 6. Procédure de Recette Exécutable

```bash
# Tests des référentiels et politiques comptables
pytest tests/unit/domain/test_reference_standards.py -v
pytest tests/unit/domain/test_company_chart.py -v
pytest tests/unit/domain/test_numbering_policy.py -v
pytest tests/unit/domain/test_policies.py -v

# Tests de conformité des plans réglementaires
pytest tests/golden/regulatory/ -v

# Vérification Mypy
mypy src/pyaccountingkit/domain/references src/pyaccountingkit/domain/charts src/pyaccountingkit/domain/policies
```
