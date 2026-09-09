# PyAccountingKit — Documentation

Bienvenue dans le centre de documentation d'architecture et de conception de **PyAccountingKit**.

---

## Structure du dossier `docs/`

```text
docs/
├── specs/                   # Spécifications d'architecture canoniques (00 à 23)
│   ├── README.md            # Vue d'ensemble des spécifications par domaine
│   ├── INDEX.md             # Matrice d'ordonnancement par priorité (P0.1 à P2.3)
│   ├── 00_cadrage/          # Cadrage initial, vision produit et modèle de domaine
│   ├── 01_core-accounting/  # Invariants comptables, policies, référentiels et plans
│   ├── 02_ledger-operations/# Grand livre, posting, clôtures, audit et réconciliation
│   ├── 03_reporting-analytics/# États financiers, analyse financière et consolidation
│   ├── 04_integration-infra/# Persistance, imports FEC, API publique et conformité
│   └── 05_engineering-governance/# Stratégie de test, release et registre des 785 ADRs
│
├── plans/                   # Plans d'implémentation modulaires (PLAN-00 à PLAN-09)
│   ├── README.md            # Index maître des plans, matrice des gates et chemin critique
│   ├── PLAN-00_REPOSITORY_BOOTSTRAP_0.0.1.md
│   ├── PLAN-01_ACCOUNTING_CORE_0.1.0.md
│   ├── PLAN-02_REFERENCES_CHARTS_POLICIES_0.2.0.md
│   ├── PLAN-03_IMPORTS_REPORTING_0.3.0.md
│   ├── PLAN-04_SUBLEDGERS_FINANCIAL_ANALYSIS_0.4.0.md
│   ├── PLAN-05_PUBLIC_API_ADAPTERS_0.5.0.md
│   ├── PLAN-06_MIGRATION_CFA_FRA_HARDENING_1.0.0.md
│   ├── PLAN-07_RECONCILIATION_1.1.0.md
│   ├── PLAN-08_CONSOLIDATION_1.2.0.md
│   └── PLAN-09_CORPORATE_FINANCE_BOUNDARIES.md
│
├── referentiels/            # Données sources réglementaires (PCG, SYSCOHADA) et schémas JSON
│   ├── datasets/            # Datasets normalisés (concepts, crosswalk, reporting, raw)
│   └── schemas/             # Schémas JSON de validation (accounting-concept, standard, etc.)
│
├── ROADMAP.md               # Feuille de route d'implémentation opérationnelle (lots P0/P1/P2)
├── books/                   # Ouvrages et doctrine comptable de référence
└── archive/                 # Versions historiques et pré-refresh archivées
```

---

## Accès rapides

- 📋 **[Spécifications fonctionnelles & techniques (`docs/specs/README.md`)](./specs/README.md)** : exploration par domaine métier et couches logicielles.
- 🧭 **[Index priorisé des documents (`docs/specs/INDEX.md`)](./specs/INDEX.md)** : ordonnancement par priorité de conception (`P0.1` à `P2.3`) et justification doctrinale.
- 🚀 **[Plans d'implémentation opérationnels (`docs/plans/README.md`)](./plans/README.md)** : découpage opérationnel de la roadmap par release milestone (`PLAN-00` à `PLAN-09`).
- 🏛️ **[Référentiels & Schémas comptables (`docs/referentiels/`)](./referentiels/)** : datasets réglementaires officiels (PCG, SYSCOHADA) et schémas JSON de validation.
- 🗺️ **[Feuille de route d'implémentation (`docs/ROADMAP.md`)](./ROADMAP.md)** : lots de livraison, jalons de versioning (`1.0.0`, `1.1`, `1.2`) et critères de recette.
- 📚 **[Ouvrages de référence (`docs/books/`)](./books/)** : sources doctrinales et académiques (Richard & Collette, Dunod Maxi Fiches).
- 📦 **[Actifs amont et codebases de référence (`resources/`)](../resources/)** :
  - [`cfa_fra_django_mvp_sprint_7/`](../resources/cfa_fra_django_mvp_sprint_7/) : MVP Django historique (oracle comportemental de parité et golden fixtures).
  - [`regulatory-accounting-data-framework/`](../resources/regulatory-accounting-data-framework/) : forge amont des données réglementaires et normatives officielles.
- 🗄️ **[Archives historiques (`docs/archive/`)](./archive/)** : versions antérieures conservées à des fins de traçabilité.
