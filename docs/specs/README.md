# PyAccountingKit — Spécifications d'Architecture

Ce dossier contient actuellement **28 spécifications d'architecture et de conception versionnées dans GitHub** :

```text
00 → 23
+
35 → 38
```

La documentation est organisée en **7 dossiers thématiques**.

> [!IMPORTANT]
> La roadmap d'architecture référence également les specs `24 → 32`. À la date de cette mise à jour, ces neuf documents ne sont pas encore physiquement présents dans `docs/specs/` sur `main`. Ils restent donc **PENDING_INTEGRATION** et ne sont pas représentés ici par des liens artificiels.

La baseline repository-hosted est donc :

```text
00..23
35..38
```

tandis que la baseline architecturale visée par la roadmap est :

```text
00..38
```

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

## 7. Architecture Evolution — Lifecycle, State & Events (`06_architecture-evolution/`)

Spécifications transverses ajoutées après l'audit et la révision de la roadmap. Elles préparent directement le modeling gate de `LOT-40` :

- [`06_architecture-evolution/35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md`](./06_architecture-evolution/35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md) — Catalogue canonique des cycles de vie métier ; distinction lifecycle explicite, dérivé, stateless et process lifecycle
- [`06_architecture-evolution/36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md`](./06_architecture-evolution/36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md) — États, transitions légales/interdites, guards, terminalité, reopen/reversal, concurrence et persistance
- [`06_architecture-evolution/37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md`](./06_architecture-evolution/37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md) — Couverture des Domain Events, classification REQUIRED/OPTIONAL/application/audit/operational/no-event et règles d'émission
- [`06_architecture-evolution/38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md`](./06_architecture-evolution/38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md) — Matrice canonique objet → lifecycle → state machine → transition → fait métier → DomainEvent → audit/outbox/intégration

Chaîne de modélisation :

```text
35 Business Lifecycles
    ↓
36 State Machines
    ↓
37 Domain Event Coverage
    ↓
38 Lifecycle / State / Event Mapping
    ↓
25 Event Envelope / Causality
    ↓
LOT-40 implementation
```

> [!NOTE]
> La spec `25` est référencée par cette chaîne comme cible architecturale, mais reste `PENDING_INTEGRATION` dans le repository tant que le fichier correspondant n'est pas ajouté sous `docs/specs/`.

---

## 8. État d'intégration documentaire

| Plage | Statut repository | Rôle |
|---|---|---|
| `00 → 23` | ✅ Présente | baseline historique canonique |
| `24 → 32` | ⏳ Pending integration | architecture hardening / evolution référencée par la roadmap |
| `33 → 34` | ✅ Présente dans `docs/plans/` | pilotage / alignement audit-remédiation-roadmap |
| `35 → 38` | ✅ Présente | lifecycle / state-machine / event modeling |

Règle de gouvernance :

```text
ROADMAP_REFERENCE
does not imply
REPOSITORY_FILE_PRESENT
```

Un document n'est considéré `REPOSITORY_HOSTED` qu'après création et vérification du fichier sur `main`.

---

## Liens connexes

- [Roadmap d'implémentation (`docs/ROADMAP.md`)](../ROADMAP.md)
- [Index des plans d'implémentation (`docs/plans/README.md`)](../plans/README.md)
- [Next Steps Implementation Plan (`33`)](../plans/33_PYACCOUNTINGKIT_NEXT_STEPS_IMPLEMENTATION_PLAN.md)
- [Audit / Remediation / Roadmap Alignment (`34`)](../plans/34_PYACCOUNTINGKIT_AUDIT_REMEDIATION_AND_ROADMAP_ALIGNMENT.md)
- [Ouvrages et sources doctrinales (`docs/books/`)](../books/)
- [Versions archivées et historiques (`docs/archive/`)](../archive/)
