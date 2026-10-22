# PyAccountingKit — Index et Roadmap d'Architecture

Ce document récapitule l'ensemble de la documentation d'architecture de **PyAccountingKit**, depuis la baseline historique `P0.1 → P2.3` jusqu'à la phase d'évolution architecturale `P3`, avec leurs statuts, leurs emplacements et leurs justifications doctrinales et architecturales.

---

## Tableau de synthèse de la baseline architecturale

| Priorité | Pourquoi maintenant / Rôle architectural | Document | Emplacement |
|:---:|---|---|---|
| **P0.1** | Ajouter les deux ouvrages comme sources doctrinales, introduire *Accounting Policies & Measurement* et *Financial Analysis*, clarifier la frontière comptabilité / corporate finance. | [`00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`](./00_cadrage/00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md) | `specs/00_cadrage/` |
| **P0.2** | Faire évoluer la macro-architecture : *Reference → Policies → Accounting Core → Ledger → Reporting → Financial Analysis*. | [`01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`](./00_cadrage/01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md) | `specs/00_cadrage/` |
| **P0.3** | Ajouter les bounded contexts *Accounting Policies & Measurement* et *Financial Analysis*, plus les futurs contexts *Inventory*, *Fixed Assets*, *Accruals & Provisions*, *Consolidation*. | [`02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`](./00_cadrage/02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md) | `specs/00_cadrage/` |
| **P0.4** | Cœur invariant : partie double, périodes, rattachement, prudence, continuité, permanence, immutabilité, posting, reversal. | [`03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`](./01_core-accounting/03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md) | `specs/01_core-accounting/` |
| **P0.5** | Reconnaissance, évaluation initiale/ultérieure, coût, juste valeur, dépréciation, amortissement, méthodes dépendantes du référentiel. | [`04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`](./01_core-accounting/04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md) | `specs/01_core-accounting/` |
| **P0.6** | Contrat détaillé avec `regulatory-accounting-data-framework`. | [`05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`](./01_core-accounting/05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md) | `specs/01_core-accounting/` |
| **P0.7** | Référentiel → plan entreprise, longueurs 6/8/9/n, segmentation, règles spécifiques de codification (conventions propres à chaque plan non universelles). | [`06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`](./01_core-accounting/06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md) | `specs/01_core-accounting/` |
| **P0.8** | Journal, grand livre, validation, posting, immutabilité, extourne, balances et projections. | [`07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`](./02_ledger-operations/07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md) | `specs/02_ledger-operations/` |
| **P0.9** | Inventaire, cut-off, charges/produits à rattacher, provisions, dépréciations, ajustements, clôture et réouverture. | [`08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`](./02_ledger-operations/08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md) | `specs/02_ledger-operations/` |
| **P0.10** | Contrôles bloquants, piste d'audit (audit trail), provenance, reproductibilité et rejouabilité. | [`09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`](./02_ledger-operations/09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md) | `specs/02_ledger-operations/` |
| **P0.11** | Repositories, Unit of Work, transactions, locking optimiste/pessimiste, adapters Django/SQLAlchemy. | [`10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`](./04_integration-infra/10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md) | `specs/04_integration-infra/` |
| **P0.12** | Invariants, tests basés sur les propriétés, tests de contrats, golden tests issus de CFA FRA. | [`11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`](./05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md) | `specs/05_engineering-governance/` |
| **P1.1** | Import générique et FEC comme adapter français optionnel. | [`12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`](./04_integration-infra/12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md) | `specs/04_integration-infra/` |
| **P1.2** | Bilan, résultat, cash-flow, mappings, présentation réglementaire, snapshots. | [`13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`](./03_reporting-analytics/13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md) | `specs/03_reporting-analytics/` |
| **P1.3** | Bounded context analyse financière : SIG, EBE, CAF, FRNG, BFR, trésorerie, ratios, scores, diagnostic. | [`14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`](./03_reporting-analytics/14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md) | `specs/03_reporting-analytics/` |
| **P1.4** | Clients, fournisseurs, règlements, banque, taxes, immobilisations, stocks et auxiliaires. | [`15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md`](./01_core-accounting/15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md) | `specs/01_core-accounting/` |
| **P1.5** | API Python publique stable : `AccountingEngine`, commands, queries, facades. | [`16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md`](./04_integration-infra/16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md) | `specs/04_integration-infra/` |
| **P1.6** | Version PyAccountingKit ≠ édition réglementaire ≠ dataset ≠ version plan comptable ≠ version mapping. | [`17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md`](./05_engineering-governance/17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md) | `specs/05_engineering-governance/` |
| **P1.7** | Cartographier chaque composant CFA FRA vers le nouveau framework avant migration. | [`18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md`](./04_integration-infra/18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md) | `specs/04_integration-infra/` |
| **P1.8** | Mapping exhaustif des datasets réglementaires vers les objets PyAccountingKit. | [`19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md`](./04_integration-infra/19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md) | `specs/04_integration-infra/` |
| **P1.9** | Centraliser toutes les décisions d’architecture (785 ADRs consolidés sur 24 namespaces). | [`20_PYACCOUNTINGKIT_ADR_REGISTER.md`](./05_engineering-governance/20_PYACCOUNTINGKIT_ADR_REGISTER.md) | `specs/05_engineering-governance/` |
| **P2.1** | Groupes, périmètre, éliminations, goodwill, minoritaires, mapping groupe, méthodes de consolidation. | [`21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md`](./03_reporting-analytics/21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md) | `specs/03_reporting-analytics/` |
| **P2.2** | Rapprochement bancaire et de comptes, matching automatique et tolérances. | [`22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md`](./02_ledger-operations/22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md) | `specs/02_ledger-operations/` |
| **P2.3** | Frontière stricte entre PyAccountingKit et le futur framework Corporate Finance (VAN, TRI, WACC, valorisation, risque). | [`23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md`](./03_reporting-analytics/23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md) | `specs/03_reporting-analytics/` |
| **P3.1** | Transformer les principes architecturaux en contrôles exécutables et bloquants en CI. | [`24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md`](./06_architecture-evolution/24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md) | `specs/06_architecture-evolution/` |
| **P3.2** | Introduire les Domain Events, l'identité événementielle, la causalité et l'Event Envelope sans basculer en Event Sourcing. | [`25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md`](./06_architecture-evolution/25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md) | `specs/06_architecture-evolution/` |
| **P3.3** | Formaliser la reproductibilité, les Computation Manifests, la provenance et le replay. | [`26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md`](./06_architecture-evolution/26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md) | `specs/06_architecture-evolution/` |
| **P3.4** | Élever les golden scenarios et les races critiques au niveau d'une qualification transverse framework-wide. | [`27_PYACCOUNTINGKIT_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS.md`](./06_architecture-evolution/27_PYACCOUNTINGKIT_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS.md) | `specs/06_architecture-evolution/` |
| **P3.5** | Construire un toolkit de test réutilisable sans créer de runtime parallèle au framework réel. | [`28_PYACCOUNTINGKIT_TESTING_TOOLKIT_ARCHITECTURE.md`](./06_architecture-evolution/28_PYACCOUNTINGKIT_TESTING_TOOLKIT_ARCHITECTURE.md) | `specs/06_architecture-evolution/` |
| **P3.6** | Préparer une migration progressive de la topologie layer-first vers une organisation domain-first. | [`29_PYACCOUNTINGKIT_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION.md`](./06_architecture-evolution/29_PYACCOUNTINGKIT_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION.md) | `specs/06_architecture-evolution/` |
| **P3.7** | Modéliser explicitement l'incertitude, la recovery et les external effects ; interdire le blind retry après outcome incertain. | [`30_PYACCOUNTINGKIT_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS.md`](./06_architecture-evolution/30_PYACCOUNTINGKIT_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS.md) | `specs/06_architecture-evolution/` |
| **P3.8** | Ajouter une couche sémantique financière read-only pour BI/Data/AI sans concurrencer la vérité comptable. | [`31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md`](./06_architecture-evolution/31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md) | `specs/06_architecture-evolution/` |
| **P3.9** | Fixer la doctrine DDD + Hexagonal + Clean et clarifier le rôle limité de MVC/MVT côté consommateurs. | [`32_PYACCOUNTINGKIT_ARCHITECTURE_STYLE_DDD_HEXAGONAL_CLEAN_VS_MVC.md`](./06_architecture-evolution/32_PYACCOUNTINGKIT_ARCHITECTURE_STYLE_DDD_HEXAGONAL_CLEAN_VS_MVC.md) | `specs/06_architecture-evolution/` |
| **P3.10** | Classifier les objets selon leur véritable lifecycle et éviter la création artificielle de machines à états. | [`35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md`](./06_architecture-evolution/35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md) | `specs/06_architecture-evolution/` |
| **P3.11** | Formaliser les transitions, guards, états terminaux, reopen/reversal et règles de concurrence. | [`36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md`](./06_architecture-evolution/36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md) | `specs/06_architecture-evolution/` |
| **P3.12** | Décider quels faits méritent réellement un Domain Event et lesquels restent silencieux/application/audit-only. | [`37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md`](./06_architecture-evolution/37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md) | `specs/06_architecture-evolution/` |
| **P3.13** | Relier objet, lifecycle, machine à états, transition, fait métier, DomainEvent, Audit, Outbox et Integration. | [`38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md`](./06_architecture-evolution/38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md) | `specs/06_architecture-evolution/` |

---

## Organisation par phase de conception

### Phase P0 : Fondations & Moteur Central (Documents 00 à 11)
- **Cadrage & Modèle** : [`00`](./00_cadrage/00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md), [`01`](./00_cadrage/01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md), [`02`](./00_cadrage/02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md)
- **Règles & Policies** : [`03`](./01_core-accounting/03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md), [`04`](./01_core-accounting/04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md)
- **Plans & Référentiels** : [`05`](./01_core-accounting/05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md), [`06`](./01_core-accounting/06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md)
- **Grand Livre, Clôtures & Audit** : [`07`](./02_ledger-operations/07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md), [`08`](./02_ledger-operations/08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md), [`09`](./02_ledger-operations/09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md)
- **Socle Technique & Qualité** : [`10`](./04_integration-infra/10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md), [`11`](./05_engineering-governance/11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md)

### Phase P1 : Industrialisation & Capacités Métier (Documents 12 à 20)
- **Imports & Reporting** : [`12`](./04_integration-infra/12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md), [`13`](./03_reporting-analytics/13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md)
- **Analyse Financière & Sous-journaux** : [`14`](./03_reporting-analytics/14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md), [`15`](./01_core-accounting/15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md)
- **API, Release & Intégration** : [`16`](./04_integration-infra/16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md), [`17`](./05_engineering-governance/17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md), [`18`](./04_integration-infra/18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md), [`19`](./04_integration-infra/19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md)
- **Index Décisionnel (Gouvernance)** : [`20`](./05_engineering-governance/20_PYACCOUNTINGKIT_ADR_REGISTER.md)

### Phase P2 : Extensions Avancées & Frontières (Documents 21 à 23)
- **Consolidation** : [`21`](./03_reporting-analytics/21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md)
- **Réconciliation** : [`22`](./02_ledger-operations/22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md)
- **Frontières Corporate Finance** : [`23`](./03_reporting-analytics/23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md)

---

### Phase P3 : Architecture Evolution & Hardening (Documents 24 à 32, puis 35 à 38)
- **Fitness & enforcement** : [`24`](./06_architecture-evolution/24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md)
- **Event architecture & reproducibility** : [`25`](./06_architecture-evolution/25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md), [`26`](./06_architecture-evolution/26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md)
- **Golden / concurrency / testing** : [`27`](./06_architecture-evolution/27_PYACCOUNTINGKIT_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS.md), [`28`](./06_architecture-evolution/28_PYACCOUNTINGKIT_TESTING_TOOLKIT_ARCHITECTURE.md)
- **Topology / recovery / semantic layer** : [`29`](./06_architecture-evolution/29_PYACCOUNTINGKIT_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION.md), [`30`](./06_architecture-evolution/30_PYACCOUNTINGKIT_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS.md), [`31`](./06_architecture-evolution/31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md)
- **Architecture doctrine** : [`32`](./06_architecture-evolution/32_PYACCOUNTINGKIT_ARCHITECTURE_STYLE_DDD_HEXAGONAL_CLEAN_VS_MVC.md)
- **Lifecycle / State / Event modeling gate** : [`35`](./06_architecture-evolution/35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md) → [`36`](./06_architecture-evolution/36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md) → [`37`](./06_architecture-evolution/37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md) → [`38`](./06_architecture-evolution/38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md) → [`25`](./06_architecture-evolution/25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md) → `LOT-40`

> Les documents `33` et `34` sont volontairement exclus de cette phase de specs : ils appartiennent à `docs/plans/` comme documents de pilotage.

---

## Liens connexes
- [Table des matières des spécifications (`docs/specs/README.md`)](./README.md)
- [Roadmap d'implémentation (`docs/ROADMAP.md`)](../ROADMAP.md)
- [Index des plans (`docs/plans/README.md`)](../plans/README.md)
- [Next Steps Implementation Plan (`33`)](../plans/33_PYACCOUNTINGKIT_NEXT_STEPS_IMPLEMENTATION_PLAN.md)
- [Audit / Remediation / Roadmap Alignment (`34`)](../plans/34_PYACCOUNTINGKIT_AUDIT_REMEDIATION_AND_ROADMAP_ALIGNMENT.md)
- [Ouvrages et sources doctrinales (`docs/books/`)](../books/)
- [Archives historiques (`docs/archive/`)](../archive/)
