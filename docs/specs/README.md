# PyAccountingKit — Spécifications d'Architecture

Ce dossier contient actuellement **37 spécifications d'architecture et de conception versionnées dans GitHub** :

```text
00 → 32
+
35 → 38
```

La documentation est organisée en **7 dossiers thématiques**.

Les documents `33` et `34` ne sont pas des specs d'architecture : ils sont conservés dans `docs/plans/` comme documents de pilotage et d'alignement audit/remédiation/roadmap.

La baseline documentaire complète du repository est donc :

```text
docs/specs : 00..32 + 35..38
docs/plans : 33..34
```

soit une séquence documentaire effectivement hébergée couvrant :

```text
00..38
```

avec séparation explicite entre **specifications** et **plans de pilotage**.

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

## 7. Architecture Evolution & Hardening (`06_architecture-evolution/`)

Spécifications transverses qui durcissent l'architecture existante et préparent les lots stratégiques `LOT-39 → LOT-46`.

### 7.1 Architecture Fitness, Events, Reproducibility & Testing

- [`06_architecture-evolution/24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md`](./06_architecture-evolution/24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md) — Fitness functions exécutables, frontières d'architecture et enforcement CI
- [`06_architecture-evolution/25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md`](./06_architecture-evolution/25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md) — Domain Events, causality, event envelope, audit/outbox/integration boundaries
- [`06_architecture-evolution/26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md`](./06_architecture-evolution/26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md) — Computation manifests, provenance, replay et reproductibilité
- [`06_architecture-evolution/27_PYACCOUNTINGKIT_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS.md`](./06_architecture-evolution/27_PYACCOUNTINGKIT_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS.md) — Golden accounting scenarios, races critiques et qualification cross-adapter
- [`06_architecture-evolution/28_PYACCOUNTINGKIT_TESTING_TOOLKIT_ARCHITECTURE.md`](./06_architecture-evolution/28_PYACCOUNTINGKIT_TESTING_TOOLKIT_ARCHITECTURE.md) — Architecture de `pyaccountingkit.testing`, builders, assertions, scenarios, contracts et harness de concurrence

### 7.2 Package Topology, Recovery & Semantic Layer

- [`06_architecture-evolution/29_PYACCOUNTINGKIT_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION.md`](./06_architecture-evolution/29_PYACCOUNTINGKIT_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION.md) — Migration progressive d'une topologie layer-first vers domain-first
- [`06_architecture-evolution/30_PYACCOUNTINGKIT_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS.md`](./06_architecture-evolution/30_PYACCOUNTINGKIT_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS.md) — Incertitude, recovery, external effects, outbox lifecycle et reconciliation-before-retry
- [`06_architecture-evolution/31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md`](./06_architecture-evolution/31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md) — Couche sémantique financière read-only, datasets, dimensions, measures, metrics et snapshots
- [`06_architecture-evolution/32_PYACCOUNTINGKIT_ARCHITECTURE_STYLE_DDD_HEXAGONAL_CLEAN_VS_MVC.md`](./06_architecture-evolution/32_PYACCOUNTINGKIT_ARCHITECTURE_STYLE_DDD_HEXAGONAL_CLEAN_VS_MVC.md) — Doctrine DDD + Hexagonal + Clean et positionnement de MVC/MVT

### 7.3 Lifecycle, State Machines & Domain Events Modeling

- [`06_architecture-evolution/35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md`](./06_architecture-evolution/35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md) — Catalogue canonique des cycles de vie métier ; distinction lifecycle explicite, dérivé, stateless et process lifecycle
- [`06_architecture-evolution/36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md`](./06_architecture-evolution/36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md) — États, transitions légales/interdites, guards, terminalité, reopen/reversal, concurrence et persistance
- [`06_architecture-evolution/37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md`](./06_architecture-evolution/37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md) — Couverture des Domain Events, classification REQUIRED/OPTIONAL/application/audit/operational/no-event et règles d'émission
- [`06_architecture-evolution/38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md`](./06_architecture-evolution/38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md) — Matrice canonique objet → lifecycle → state machine → transition → fait métier → DomainEvent → audit/outbox/intégration

### Chaîne stratégique

```text
24 Architecture Fitness Functions
    ↓
28 Testing Toolkit Foundations
    ↓
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
LOT-40 Domain Events Implementation
    ↓
26 Reproducibility
    ↓
27 Golden / Concurrency
    ↓
30 Recovery / External Effects
```

Les specs `29` et `31` alimentent respectivement `LOT-45` et `LOT-46`, tandis que `32` gouverne transversalement les lots d'évolution.

---

## 8. État d'intégration documentaire

| Plage | Statut repository | Emplacement | Rôle |
|---|---|---|---|
| `00 → 23` | ✅ Présente | `docs/specs/00_* → 05_*` | baseline historique canonique |
| `24 → 32` | ✅ Présente | `docs/specs/06_architecture-evolution/` | architecture hardening / strategic evolution |
| `33 → 34` | ✅ Présente | `docs/plans/` | pilotage / alignement audit-remédiation-roadmap |
| `35 → 38` | ✅ Présente | `docs/specs/06_architecture-evolution/` | lifecycle / state-machine / event modeling |

La séquence documentaire `00 → 38` référencée par la roadmap est désormais **physiquement couverte dans le repository**, avec `33–34` volontairement séparés des specs.

Règle de gouvernance conservée :

```text
ROADMAP_REFERENCE
must match
REPOSITORY_FILE_OR_EXPLICIT_EXTERNAL_ARTIFACT
```

---

## Liens connexes

- [Roadmap d'implémentation (`docs/ROADMAP.md`)](../ROADMAP.md)
- [Index des plans d'implémentation (`docs/plans/README.md`)](../plans/README.md)
- [Next Steps Implementation Plan (`33`)](../plans/33_PYACCOUNTINGKIT_NEXT_STEPS_IMPLEMENTATION_PLAN.md)
- [Audit / Remediation / Roadmap Alignment (`34`)](../plans/34_PYACCOUNTINGKIT_AUDIT_REMEDIATION_AND_ROADMAP_ALIGNMENT.md)
- [Ouvrages et sources doctrinales (`docs/books/`)](../books/)
- [Versions archivées et historiques (`docs/archive/`)](../archive/)
