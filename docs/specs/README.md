# PyAccountingKit — Spécifications d'Architecture

Ce dossier contient l'ensemble des **24 spécifications d'architecture et de conception** de **PyAccountingKit** (baseline canonique `00` à `23`).

La documentation est organisée en **6 dossiers thématiques** correspondant aux couches et domaines d'architecture.

> 🧭 Pour la grille complète d'ordonnancement par priorité (`P0.1` à `P2.3`) et les justifications doctrinales de chaque document, consultez l'**[`INDEX.md`](./INDEX.md)**.  
> 🗺️ Pour le plan d'exécution concret et les jalons de livraison, consultez la **[`ROADMAP.md`](../ROADMAP.md)**.

---

## 1. Cadrage, Vision & Modèle de Domaine (`00_cadrage/`)

Vision produit, macro-architecture, exigences et bounded contexts :

- [`00_cadrage/00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`](./00_cadrage/00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md) — Analyse des exigences & cadrage initial
- [`00_cadrage/01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`](./00_cadrage/01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md) — Vision du projet et architecture cible
- [`00_cadrage/02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`](./00_cadrage/02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md) — Modèle de domaine et bounded contexts

---

## 2. Cœur Comptable, Règles & Référentiels (`01_core-accounting/`)

Règles métier, invariants d'équilibre, policies d'évaluation, plans de comptes et sous-journaux opérationnels :

- [`01_core-accounting/03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`](./01_core-accounting/03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md) — Règles et invariants comptables
- [`01_core-accounting/04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`](./01_core-accounting/04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md) — Politiques comptables, comptabilisation et évaluation
- [`01_core-accounting/05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`](./01_core-accounting/05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md) — Données de référence comptables
- [`01_core-accounting/06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`](./01_core-accounting/06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md) — Plan comptable entreprise et numérotation
- [`01_core-accounting/15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md`](./01_core-accounting/15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md) — Sous-journaux et comptabilité opérationnelle

---

## 3. Opérations de Grand Livre, Clôtures & Contrôles (`02_ledger-operations/`)

Moteur d'enregistrement, écritures d'ajustement, clôtures périodiques, audit, traçabilité et réconciliation :

- [`02_ledger-operations/07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`](./02_ledger-operations/07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md) — Enregistrement grand livre, lettrage et extourne
- [`02_ledger-operations/08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`](./02_ledger-operations/08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md) — Clôtures, régularisations, provisions et ajustements
- [`02_ledger-operations/09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`](./02_ledger-operations/09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md) — Contrôles internes, audit et traçabilité
- [`02_ledger-operations/22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md`](./02_ledger-operations/22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md) — Moteur de réconciliation et de rapprochement

---

## 4. Reporting, Consolidation & Analyse Financière (`03_reporting-analytics/`)

Plaquettes réglementaires, agrégats d'analyse financière, périmètres et éliminations de consolidation :

- [`03_reporting-analytics/13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`](./03_reporting-analytics/13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md) — États financiers et reporting réglementaire
- [`03_reporting-analytics/14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`](./03_reporting-analytics/14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md) — Analyse financière et indicateurs de performance
- [`03_reporting-analytics/21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md`](./03_reporting-analytics/21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md) — Architecture de consolidation comptable
- [`03_reporting-analytics/23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md`](./03_reporting-analytics/23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md) — Frontières avec l'analyse financière avancée et Corporate Finance

---

## 5. Intégration, Persistance & Conformité (`04_integration-infra/`)

Ports & adapters, mapping réglementaire, imports FEC, API publique et contrats de persistance :

- [`04_integration-infra/10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`](./04_integration-infra/10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md) — Persistance, concurrence et contrats d'adapters
- [`04_integration-infra/12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`](./04_integration-infra/12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md) — Import comptable et adapter FEC
- [`04_integration-infra/16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md`](./04_integration-infra/16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md) — Conception de l'API publique
- [`04_integration-infra/18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md`](./04_integration-infra/18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md) — Plan d'extraction et de migration CFA FRA
- [`04_integration-infra/19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md`](./04_integration-infra/19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md) — Matrice d'intégration des référentiels réglementaires

---

## 6. Gouvernance, Qualité & ADR (`05_engineering-governance/`)

Stratégie de test, politique de versioning et registre centralisé des décisions d'architecture :

- [`05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`](./05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md) — Stratégie de test et qualité
- [`05_engineering-governance/17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md`](./05_engineering-governance/17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md) — Stratégie de versioning et release
- [`05_engineering-governance/20_PYACCOUNTINGKIT_ADR_REGISTER.md`](./05_engineering-governance/20_PYACCOUNTINGKIT_ADR_REGISTER.md) — Registre consolidé des Architecture Decision Records (785 ADRs)

---

## Liens connexes

- [Roadmap d'implémentation (`docs/ROADMAP.md`)](../ROADMAP.md)
- [Ouvrages et sources doctrinales (`docs/books/`)](../books/)
- [Versions archivées et historiques (`docs/archive/`)](../archive/)
