# PLAN-01 : Moteur Comptable Central, Invariants & Persistance In-Memory (Release 0.1.0)

Ce plan d'implémentation opérationnel couvre les lots **LOT-01 à LOT-09** de la [Roadmap](../ROADMAP.md) et détaille le cœur algorithmique et doctrinal de PyAccountingKit.

---

## 1. Contexte & Spécifications de Référence

- **Specs applicables** :
  - Invariants comptables & règles cardinales : [`03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`](../specs/01_core-accounting/03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md)
  - Modèle de domaine & agrégats : [`02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`](../specs/00_cadrage/02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md)
  - Grand livre, posting & contrepassation : [`07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`](../specs/02_ledger-operations/07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md)
  - Clôtures, provisions & régularisations : [`08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`](../specs/02_ledger-operations/08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md)
  - Audit, contrôles & traçabilité : [`09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`](../specs/02_ledger-operations/09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md)
  - Persistance & contrats d'adaptateurs : [`10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`](../specs/04_integration-infra/10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md)
  - Stratégie de test : [`11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`](../specs/05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md)
- **Doctrine comptable & Référentiels d'architecture** :
  - 📖 [`Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md`](../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md) (Première Partie : Théorie comptable, partie double, journal, grand livre, balance, clôtures et réouvertures).
  - 🏛️ Référentiels réglementaires : [`docs/referentiels/`](../referentiels/) (Principe d'étanchéité : le cœur `core` et `domain` est agnostique des nomenclatures locales, qui ne sont chargées qu'au palier `PLAN-02`).

---

## 2. Inventaire des Fichiers à Implémenter & Liens Relatifs

### 2.1. Module Fondamental (`core`)
- Primitives monétaires & devises :
  - [`src/pyaccountingkit/core/money.py`](../../src/pyaccountingkit/core/money.py) (Value Object `Money` décimal exact)
  - [`src/pyaccountingkit/core/currency.py`](../../src/pyaccountingkit/core/currency.py) (Devises ISO 4217)
- Identifiants fortement typés :
  - [`src/pyaccountingkit/core/identifiers.py`](../../src/pyaccountingkit/core/identifiers.py) (`EntryId`, `JournalId`, `AccountId`, `PeriodId`)
- Horloge déterministe & idempotence :
  - [`src/pyaccountingkit/core/clock.py`](../../src/pyaccountingkit/core/clock.py) (`ClockProtocol`, `FrozenClock`, `SystemClock`)
  - [`src/pyaccountingkit/core/idempotency.py`](../../src/pyaccountingkit/core/idempotency.py) (`IdempotencyKey`, détection de rejeu)
  - [`src/pyaccountingkit/core/revisions.py`](../../src/pyaccountingkit/core/revisions.py) (Contrôle optimiste de concurrence)
- Hiérarchie d'erreurs du cœur :
  - [`src/pyaccountingkit/core/errors.py`](../../src/pyaccountingkit/core/errors.py) (`UnbalancedEntryError`, `PeriodClosedError`, etc.)
  - [`src/pyaccountingkit/core/results.py`](../../src/pyaccountingkit/core/results.py) (Type monadique `Result[T, E]`)

### 2.2. Modèle de Domaine (`domain`)
- Agrégats Journaux & Écritures :
  - [`src/pyaccountingkit/domain/journals/journal.py`](../../src/pyaccountingkit/domain/journals/journal.py) (Type de journal : Ventes, Achats, Banque, OD)
  - [`src/pyaccountingkit/domain/journals/journal_entry.py`](../../src/pyaccountingkit/domain/journals/journal_entry.py) (Agrégat racine `JournalEntry`)
  - [`src/pyaccountingkit/domain/journals/journal_line.py`](../../src/pyaccountingkit/domain/journals/journal_line.py) (Ligne de débit/crédit `JournalLine`)
- Périodes & Exercices Fiscaux :
  - [`src/pyaccountingkit/domain/periods/accounting_period.py`](../../src/pyaccountingkit/domain/periods/accounting_period.py) (Bornes de période, date de valeur)
  - [`src/pyaccountingkit/domain/periods/closing_status.py`](../../src/pyaccountingkit/domain/periods/closing_status.py) (Statuts `OPEN`, `LOCKED`, `CLOSED`)
  - [`src/pyaccountingkit/domain/identity/fiscal_year.py`](../../src/pyaccountingkit/domain/identity/fiscal_year.py) (Exercice comptable)
- Moteur de Comptabilisation & Grand Livre :
  - [`src/pyaccountingkit/domain/ledger/posting.py`](../../src/pyaccountingkit/domain/ledger/posting.py) (`PostingService` et scellement d'écritures)
  - [`src/pyaccountingkit/domain/ledger/reversal.py`](../../src/pyaccountingkit/domain/ledger/reversal.py) (`ReversalService` avec lien d'antériorité strict)
  - [`src/pyaccountingkit/domain/ledger/general_ledger.py`](../../src/pyaccountingkit/domain/ledger/general_ledger.py) (Grand livre et calcul de soldes)
  - [`src/pyaccountingkit/domain/ledger/trial_balance.py`](../../src/pyaccountingkit/domain/ledger/trial_balance.py) (Balance générale à 2, 4 ou 6 colonnes)
  - [`src/pyaccountingkit/domain/ledger/snapshots.py`](../../src/pyaccountingkit/domain/ledger/snapshots.py) (Snapshots immuables certifiés)
- Audit & Clôture :
  - [`src/pyaccountingkit/domain/audit/events.py`](../../src/pyaccountingkit/domain/audit/events.py) (`AuditEvent`, log append-only)
  - [`src/pyaccountingkit/domain/audit/actor.py`](../../src/pyaccountingkit/domain/audit/actor.py) (Traçabilité utilisateur / système)
  - [`src/pyaccountingkit/domain/closing/closing_run.py`](../../src/pyaccountingkit/domain/closing/closing_run.py) (Orchestration de la clôture périodique)
  - [`src/pyaccountingkit/domain/closing/opening.py`](../../src/pyaccountingkit/domain/closing/opening.py) (Génération automatique de la réouverture / à-nouveaux)

### 2.3. Ports & Adaptateurs In-Memory (`ports`, `adapters`)
- Contrats de persistance :
  - [`src/pyaccountingkit/ports/unit_of_work.py`](../../src/pyaccountingkit/ports/unit_of_work.py) (`UnitOfWorkProtocol`)
  - [`src/pyaccountingkit/ports/repositories.py`](../../src/pyaccountingkit/ports/repositories.py) (`JournalEntryRepositoryProtocol`, `PeriodRepositoryProtocol`)
  - [`src/pyaccountingkit/ports/audit.py`](../../src/pyaccountingkit/ports/audit.py) (`AuditLogSinkProtocol`)
- Implémentation In-Memory :
  - [`src/pyaccountingkit/adapters/in_memory/unit_of_work.py`](../../src/pyaccountingkit/adapters/in_memory/unit_of_work.py)
  - [`src/pyaccountingkit/adapters/in_memory/repositories.py`](../../src/pyaccountingkit/adapters/in_memory/repositories.py)

### 2.4. Suites de Tests Dédiées (`tests`)
- Tests unitaires :
  - [`tests/unit/core/test_money.py`](../../tests/unit/core/test_money.py)
  - [`tests/unit/domain/test_journal_entry.py`](../../tests/unit/domain/test_journal_entry.py)
  - [`tests/unit/domain/test_posting_service.py`](../../tests/unit/domain/test_posting_service.py)
  - [`tests/unit/domain/test_reversal.py`](../../tests/unit/domain/test_reversal.py)
  - [`tests/unit/domain/test_closing.py`](../../tests/unit/domain/test_closing.py)
- Tests de propriétés (Hypothesis) :
  - [`tests/property/test_money_properties.py`](../../tests/property/test_money_properties.py)
  - [`tests/property/test_balance_invariants.py`](../../tests/property/test_balance_invariants.py)
- Tests de contrat de dépôt :
  - [`tests/contract/test_repository_contract.py`](../../tests/contract/test_repository_contract.py)

---

## 3. Détails Techniques & Extraits de Code Concrets

### 3.1. Primitives Monétaires (`src/pyaccountingkit/core/money.py`)
La classe `Money` manipule exclusivement des entiers ou des objets `decimal.Decimal` à précision fixe, interdisant tout recours aux flottants IEEE 754.

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.errors import IncompatibleCurrenciesError, InvalidAmountError


@dataclass(frozen=True, slots=True)
class Money:
    """Montant monétaire immuable avec devise explicite."""

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise InvalidAmountError(f"Le montant doit être un Decimal, reçu: {type(self.amount)}")
        if not self.amount.is_finite():
            raise InvalidAmountError("Le montant doit être un nombre fini")
        # Normalisation automatique aux centimes de la devise
        quantized = self.amount.quantize(self.currency.subunit_exp, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)

    @classmethod
    def from_str(cls, val: str, currency: Currency) -> Money:
        return cls(Decimal(val), currency)

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        return cls(Decimal("0.00"), currency)

    def __add__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def is_zero(self) -> bool:
        return self.amount.is_zero()

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise IncompatibleCurrenciesError(
                f"Opération impossible entre {self.currency.code} et {other.currency.code}"
            )
```

### 3.2. Agrégat `JournalEntry` & Invariant Partie Double (`src/pyaccountingkit/domain/journals/journal_entry.py`)

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Sequence
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.core.errors import UnbalancedEntryError, EmptyEntryError
from pyaccountingkit.domain.journals.journal_line import JournalLine


class EntryStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


@dataclass(frozen=True)
class JournalEntry:
    """Écriture comptable respectant la règle de la partie double."""

    id: EntryId
    journal_id: JournalId
    period_id: PeriodId
    entry_date: date
    description: str
    lines: tuple[JournalLine, ...]
    status: EntryStatus = EntryStatus.DRAFT
    posted_at: datetime | None = None
    reversal_of_id: EntryId | None = None
    reversed_by_id: EntryId | None = None

    def __post_init__(self) -> None:
        if not self.lines:
            raise EmptyEntryError("Une écriture comptable doit comporter au moins 2 lignes")
        if len(self.lines) < 2:
            raise EmptyEntryError("La partie double exige un minimum de deux lignes")

    def total_debit(self) -> Money:
        first_currency = self.lines[0].debit.currency
        total = Money.zero(first_currency)
        for line in self.lines:
            total += line.debit
        return total

    def total_credit(self) -> Money:
        first_currency = self.lines[0].credit.currency
        total = Money.zero(first_currency)
        for line in self.lines:
            total += line.credit
        return total

    def is_balanced(self) -> bool:
        return self.total_debit() == self.total_credit()

    def validate_balance(self) -> None:
        """Valide rigoureusement l'équilibre débit/crédit au centime près."""
        tot_deb = self.total_debit()
        tot_crd = self.total_credit()
        if tot_deb != tot_crd:
            raise UnbalancedEntryError(
                f"Écriture déséquilibrée {self.id}: Débit={tot_deb.amount} != Crédit={tot_crd.amount}"
            )
```

### 3.3. Service de Comptabilisation (`src/pyaccountingkit/domain/ledger/posting.py`)
Ce service applique les invariants légaux : rejet si période fermée, scellement temporel, immutabilité et enregistrement d'audit.

```python
from __future__ import annotations

from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.core.errors import PeriodClosedError, EntryAlreadyPostedError
from pyaccountingkit.domain.journals.journal_entry import JournalEntry, EntryStatus
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.audit import AuditLogSinkProtocol
from pyaccountingkit.domain.audit.events import AuditEvent


class PostingService:
    """Service appliquant le posting irréversible d'une écriture."""

    def __init__(self, clock: ClockProtocol, audit_sink: AuditLogSinkProtocol) -> None:
        self._clock = clock
        self._audit_sink = audit_sink

    def post(self, entry: JournalEntry, period: AccountingPeriod, user_id: str) -> JournalEntry:
        if entry.status != EntryStatus.DRAFT:
            raise EntryAlreadyPostedError(f"L'écriture {entry.id} n'est pas au statut DRAFT")

        if not period.is_open_for_posting():
            raise PeriodClosedError(f"La période {period.id} est verrouillée ou clôturée")

        # Invariant fondamental
        entry.validate_balance()

        now = self._clock.now()
        posted_entry = JournalEntry(
            id=entry.id,
            journal_id=entry.journal_id,
            period_id=entry.period_id,
            entry_date=entry.entry_date,
            description=entry.description,
            lines=entry.lines,
            status=EntryStatus.POSTED,
            posted_at=now,
            reversal_of_id=entry.reversal_of_id,
            reversed_by_id=entry.reversed_by_id,
        )

        self._audit_sink.record(
            AuditEvent(
                event_type="ENTRY_POSTED",
                entity_id=str(entry.id),
                occurred_at=now,
                actor_id=user_id,
                payload={"total": str(posted_entry.total_debit().amount)},
            )
        )
        return posted_entry
```

### 3.4. Contrat du Port UnitOfWork (`src/pyaccountingkit/ports/unit_of_work.py`)

```python
from __future__ import annotations

from typing import Protocol
from pyaccountingkit.ports.repositories import (
    JournalEntryRepositoryProtocol,
    PeriodRepositoryProtocol,
    JournalRepositoryProtocol,
)


class UnitOfWorkProtocol(Protocol):
    """Contrat transactionnel garantissant l'atomicité des mutations comptables."""

    entries: JournalEntryRepositoryProtocol
    periods: PeriodRepositoryProtocol
    journals: JournalRepositoryProtocol

    def __enter__(self) -> UnitOfWorkProtocol: ...
    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

---

## 4. Matrice des Gates & Critères de Qualité

- **`GA` (Accounting Invariants Gate)** :
  - Égalité stricte $\sum Débit = \sum Crédit$ au centime près.
  - Impossibilité absolue d'altérer une écriture une fois au statut `POSTED`.
  - Toute annulation s'effectue par création d'une nouvelle écriture liée en contrepassation (`REVERSED`).
- **`GC` (Currency & Precision Gate)** :
  - Contrôle de non-mélange de devises au sein d'une même écriture sans compte de contre-valeur.
  - Zéro perte d'arrondi décimal.
- **`GI` (Immutability Gate)** :
  - Les instances de `JournalEntry` et `JournalLine` sont figées (`frozen=True`).
  - Le journal et le grand livre sont des structures append-only.

---

## 5. Definition of Done (DoD Spécifique)

- [ ] L'arithmétique `Money` passe 100 % des tests de propriétés Hypothesis (commutativité, associativité, élément neutre).
- [ ] L'agrégat `JournalEntry` rejette immédiatement toute tentative de création déséquilibrée.
- [ ] Le `PostingService` refuse la comptabilisation sur période clôturée avec une exception typée.
- [ ] L'implémentation `InMemoryUnitOfWork` supporte le rollback complet en cas d'erreur sans état résiduel corrompu.
- [ ] Le calcul de la balance générale (`TrialBalance`) concorde exactement avec la somme cumulée des lignes du grand livre.
- [ ] Couverture de tests unitaires sur `core/` et `domain/` $> 95\,\%$.

---

## 6. Procédure de Recette Exécutable

```bash
# Exécution ciblée des tests du cœur comptable
pytest tests/unit/core/test_money.py -v
pytest tests/unit/domain/test_journal_entry.py -v
pytest tests/unit/domain/test_posting_service.py -v
pytest tests/property/test_balance_invariants.py -v
pytest tests/contract/test_repository_contract.py -v

# Vérification du typage strict sur le périmètre
mypy src/pyaccountingkit/core src/pyaccountingkit/domain src/pyaccountingkit/ports
```
