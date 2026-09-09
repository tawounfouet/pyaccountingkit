# Fixtures de Tests Techniques — PyAccountingKit (`tests/fixtures/`)

Ce répertoire contient les **fichiers d'entrée techniques déterministes** utilisés par la suite de tests automatisés (tests unitaires, tests de contrat, tests d'intégration, tests de propriétés).

---

## 1. Distinction Fondamentale des Niveaux de Données

| Emplacement | Nature | Public cible | Usage & Règle |
| :--- | :--- | :--- | :--- |
| **`tests/fixtures/`** (ici) | **Entrées de test déterministes** | Automates de tests (Pytest / CI) | Petits fichiers figés, représentatifs d'un cas d'usage ou d'un cas limite (ex: FEC déséquilibré, JSON corrompu, paire d'écritures). |
| **`tests/golden/`** | **Oracles de comportement & Attentes** | Tests de conformité & non-régression | Couples entrée/sortie certifiés avec checksums. Sert pour la parité avec CFA FRA (`tests/golden/cfa_fra/`) et la conformité légale (`tests/golden/regulatory/`). |
| **`data/samples/`** | **Données didactiques publiques** | Utilisateurs humains & développeurs | Données synthétiques réalistes pour les tutoriels, le README, les quickstarts et les démonstrateurs CLI. Ne doit pas être une dépendance des tests unitaires. |

---

## 2. Organisation par Domaine Fonctionnel

```text
tests/fixtures/
├── README.md               # Le présent document
│
├── accounting/             # Entrées JSON/CSV pour tests du moteur comptable
│   ├── balanced_entry_sample.json     # Écriture équilibrée valide
│   └── unbalanced_entry_sample.json   # Écriture déséquilibrée (test de rejet UnbalancedEntryError)
│
├── fec/                    # Échantillons de fichiers FEC pour tests du parseur
│   ├── valid_standard_fec.txt         # Fichier FEC minimal conforme
│   └── invalid_unbalanced_fec.txt     # Fichier FEC avec rupture d'équilibre
│
├── reporting/              # Balances et grands livres de test pour les états financiers
├── subledgers/             # Échéances, factures et encaissements pour tests de lettrage
├── reconciliation/         # Paires d'items pour tests des règles d'appariement et tolérances
├── consolidation/          # Balances filiales pour tests des conversions de devises et éliminations
└── regulatory/             # Extraits minimaux de plans de comptes pour tester AccountingReferenceProvider
    └── minimal_pcg_structure.json     # Structure minimale pour isolation complète des tests
```

---

## 3. Règles d'Or pour les Fixtures

1. **Immutabilité stricte** : Aucun test ne doit écrire ou muter un fichier dans `tests/fixtures/`. Si un test a besoin de modifier une entrée, il doit la copier dans un répertoire temporaire (`tmp_path`).
2. **Minimalisme** : Une fixture doit être aussi compacte que possible, ciblée sur l'assertion qu'elle doit provoquer.
3. **Zéro donnée confidentielle** : Tout nom, montant ou identifiant doit être fictif ou généré.
