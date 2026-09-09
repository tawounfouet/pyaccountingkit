# PLAN-03 : Ingestion Universelle, Adaptateur FEC & États Financiers (Release 0.3.0)

Ce plan d'implémentation opérationnel couvre les lots **LOT-14 à LOT-17** de la [Roadmap](../ROADMAP.md). Il formalise le pipeline d'importation comptable, le support natif du Fichier des Écritures Comptables (FEC) français et la génération certifiée des états financiers de synthèse (Bilan, Compte de résultat, Flux de trésorerie).

---

## 1. Contexte & Spécifications de Référence

- **Specs applicables** :
  - Imports comptables & adaptateur FEC : [`12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`](../specs/04_integration-infra/12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md)
  - États financiers & reporting réglementaire : [`13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`](../specs/03_reporting-analytics/13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md)
  - Invariants comptables : [`03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`](../specs/01_core-accounting/03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md)
  - Grand livre et balance : [`07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`](../specs/02_ledger-operations/07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md)
  - Matrice réglementaire : [`19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md`](../specs/04_integration-infra/19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md)
- **Doctrine comptable & Référentiels de données** :
  - 📖 [`Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md`](../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md) (Documents de synthèse : Bilan, Compte de résultat, Tableau de financement, principes de rattachement et force probante des écritures importées).
  - 📁 Datasets réglementaires de reporting : [`docs/referentiels/datasets/reporting/`](../referentiels/datasets/reporting/) (structures officielles et nomenclatures des états financiers PCG et SYSCOHADA).

---

## 2. Inventaire des Fichiers à Implémenter & Liens Relatifs

### 2.1. Pipeline d'Importation & Staging (`domain/imports`)
- Modélisation du flux de données d'ingestion :
  - [`src/pyaccountingkit/domain/imports/raw_record.py`](../../src/pyaccountingkit/domain/imports/raw_record.py) (`RawImportRecord`, données brutes non validées)
  - [`src/pyaccountingkit/domain/imports/normalized_record.py`](../../src/pyaccountingkit/domain/imports/normalized_record.py) (`NormalizedImportRecord`, types certifiés)
  - [`src/pyaccountingkit/domain/imports/batch.py`](../../src/pyaccountingkit/domain/imports/batch.py) (`ImportBatch`, agrégat de staging)
  - [`src/pyaccountingkit/domain/imports/issues.py`](../../src/pyaccountingkit/domain/imports/issues.py) (`ImportIssue`, typologie d'erreurs et alertes)
  - [`src/pyaccountingkit/domain/imports/source_artifact.py`](../../src/pyaccountingkit/domain/imports/source_artifact.py) (Empreinte SHA-256 du fichier d'origine)
  - [`src/pyaccountingkit/domain/imports/import_plan.py`](../../src/pyaccountingkit/domain/imports/import_plan.py) (Plan de validation et conversion en `JournalEntry`)

### 2.2. Adaptateurs FEC Français (`adapters/imports`, `adapters/regulatory`)
- Lecture et écriture du format légal français (Article A.47 A-1 du LPF) :
  - [`src/pyaccountingkit/adapters/imports/fec_reader.py`](../../src/pyaccountingkit/adapters/imports/fec_reader.py) (Parser FEC tabulaire / pipe-separated)
  - [`src/pyaccountingkit/adapters/regulatory/fec_writer.py`](../../src/pyaccountingkit/adapters/regulatory/fec_writer.py) (Générateur conforme aux normes DGFiP)

### 2.3. États Financiers & Reporting (`domain/reporting`)
- Moteur d'états de synthèse :
  - [`src/pyaccountingkit/domain/reporting/statement_definition.py`](../../src/pyaccountingkit/domain/reporting/statement_definition.py) (`StatementDefinition`, arborescence du Bilan / CDR)
  - [`src/pyaccountingkit/domain/reporting/statement_line.py`](../../src/pyaccountingkit/domain/reporting/statement_line.py) (`StatementLine`, règles de calcul et regroupements)
  - [`src/pyaccountingkit/domain/reporting/mappings.py`](../../src/pyaccountingkit/domain/reporting/mappings.py) (`StatementMapping`, liaison Comptes $\rightarrow$ Postes)
  - [`src/pyaccountingkit/domain/reporting/report_snapshot.py`](../../src/pyaccountingkit/domain/reporting/report_snapshot.py) (`ReportSnapshot`, rapport financier certifié scellé)
  - [`src/pyaccountingkit/domain/reporting/regulatory_profile.py`](../../src/pyaccountingkit/domain/reporting/regulatory_profile.py) (`RegulatoryProfile`, liasse fiscale CERFA)

### 2.4. Suites de Tests Associées (`tests`)
- Tests unitaires et d'intégration :
  - [`tests/unit/domain/test_import_pipeline.py`](../../tests/unit/domain/test_import_pipeline.py)
  - [`tests/unit/domain/test_fec_reader.py`](../../tests/unit/domain/test_fec_reader.py)
  - [`tests/unit/domain/test_fec_writer.py`](../../tests/unit/domain/test_fec_writer.py)
  - [`tests/unit/domain/test_financial_statements.py`](../../tests/unit/domain/test_financial_statements.py)
- Tests de conformité DGFiP :
  - [`tests/golden/regulatory/test_fec_compliance.py`](../../tests/golden/regulatory/test_fec_compliance.py)

---

## 3. Détails Techniques & Extraits de Code Concrets

### 3.1. Structure du Fichier des Écritures Comptables (FEC)
Le format officiel impose 18 colonnes obligatoires séparées par des tabulations ou des barres verticales (`|`).

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterator


@dataclass(frozen=True)
class FECRecord:
    """Ligne conforme aux 18 colonnes de l'article A.47 A-1 du LPF."""

    journal_code: str       # JournalCode
    journal_lib: str        # JournalLib
    ecriture_num: str       # EcritureNum
    ecriture_date: date     # EcritureDate (YYYYMMDD)
    compte_num: str         # CompteNum
    compte_lib: str         # CompteLib
    compte_aux_num: str     # CompAuxNum (optionnel)
    compte_aux_lib: str     # CompAuxLib (optionnel)
    piece_ref: str          # PieceRef
    piece_date: date        # PieceDate (YYYYMMDD)
    ecriture_lib: str       # EcritureLib
    debit: Decimal          # Debit
    credit: Decimal         # Credit
    ecriture_let: str       # EcritureLet (lettrage)
    date_let: date | None   # DateLet
    valid_date: date        # ValidDate (date de validation)
    montant_devise: Decimal # Montantdevise
    idevise: str            # Idevise (Code ISO)

    def to_fec_line(self, separator: str = "\t") -> str:
        def fmt_date(d: date | None) -> str:
            return d.strftime("%Y%m%d") if d else ""

        def fmt_amount(amt: Decimal) -> str:
            return f"{amt:.2f}".replace(".", ",")

        fields = [
            self.journal_code,
            self.journal_lib,
            self.ecriture_num,
            fmt_date(self.ecriture_date),
            self.compte_num,
            self.compte_lib,
            self.compte_aux_num,
            self.compte_aux_lib,
            self.piece_ref,
            fmt_date(self.piece_date),
            self.ecriture_lib,
            fmt_amount(self.debit),
            fmt_amount(self.credit),
            self.ecriture_let,
            fmt_date(self.date_let),
            fmt_date(self.valid_date),
            fmt_amount(self.montant_devise),
            self.idevise,
        ]
        return separator.join(fields)
```

### 3.2. Moteur de Définition des États Financiers (`src/pyaccountingkit/domain/reporting/statement_definition.py`)

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.ledger.trial_balance import TrialBalance


class StatementType(str, Enum):
    BALANCE_SHEET = "BALANCE_SHEET"           # Bilan
    INCOME_STATEMENT = "INCOME_STATEMENT"     # Compte de Résultat
    CASH_FLOW = "CASH_FLOW"                   # Tableau des flux de trésorerie


@dataclass(frozen=True)
class StatementItem:
    """Poste agrégé d'un état financier (ex: Actif Circulant, Capitaux Propres)."""

    code: str
    title: str
    account_patterns: tuple[str, ...]  # ex: ("411*", "413*")
    subtract_patterns: tuple[str, ...] = ()  # ex: ("491*") dépréciations

    def evaluate(self, balance: TrialBalance) -> Money:
        total = Money.zero(balance.currency)
        for line in balance.lines:
            for pat in self.account_patterns:
                if self._match(line.account_number, pat):
                    total += line.net_debit_balance()
            for sub_pat in self.subtract_patterns:
                if self._match(line.account_number, sub_pat):
                    total -= line.net_credit_balance()
        return total

    @staticmethod
    def _match(account: str, pattern: str) -> bool:
        if pattern.endswith("*"):
            return account.startswith(pattern[:-1])
        return account == pattern
```

---

## 4. Matrice des Gates & Critères de Qualité

- **`GR` (Regulatory FEC Gate)** :
  - Respect scrupuleux des en-têtes et des 18 champs obligatoires du FEC.
  - Validation que $\sum Débit = \sum Crédit$ sur l'ensemble du fichier généré.
  - Les dates doivent être cohérentes avec les bornes temporelles de l'exercice fiscal.
- **`GI` (Audit & Staging Immutability)** :
  - Tout lot d'importation passe obligatoirement par une étape de `Staging` hermétique (`ImportBatch`) avant conversion en écritures comptabilisées.
  - Sauvegarde de l'empreinte SHA-256 du fichier d'origine dans le journal d'audit.

---

## 5. Definition of Done (DoD Spécifique)

- [ ] L'adaptateur `FECReader` parse sans erreur un FEC de test de 10 000 lignes issu de comptabilités réelles.
- [ ] L'adaptateur `FECWriter` produit un fichier conforme, validable par l'outil officiel *Test Compta Demat* de la DGFiP.
- [ ] Le Bilan Actif / Passif produit est rigoureusement équilibré (`Total Actif == Total Passif + Résultat`).
- [ ] Le Compte de Résultat sépare clairement résultat d'exploitation, financier et exceptionnel.
- [ ] Les snapshots d'états financiers (`ReportSnapshot`) sont immuables et rejouables.

---

## 6. Procédure de Recette Exécutable

```bash
# Tests du parser et writer FEC
pytest tests/unit/domain/test_fec_reader.py -v
pytest tests/unit/domain/test_fec_writer.py -v

# Validation des états financiers
pytest tests/unit/domain/test_financial_statements.py -v

# Test golden de conformité réglementaire DGFiP
pytest tests/golden/regulatory/test_fec_compliance.py -v

# Vérification du typage Mypy
mypy src/pyaccountingkit/domain/imports src/pyaccountingkit/domain/reporting src/pyaccountingkit/adapters/imports
```
