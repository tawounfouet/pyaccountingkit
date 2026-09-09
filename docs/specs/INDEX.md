# PyAccountingKit — Index et Roadmap d'Architecture

Ce document récapitule l'ensemble de la documentation d'architecture de **PyAccountingKit**, ordonnancée par priorité de conception (de `P0.1` à `P2.3`), avec leurs statuts, leurs emplacements dans la nouvelle arborescence modulaire et leurs justifications doctrinales et architecturales.

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

## Liens connexes
- [Table des matières des spécifications (`docs/specs/README.md`)](./README.md)
- [Roadmap d'implémentation (`docs/ROADMAP.md`)](../ROADMAP.md)
- [Ouvrages et sources doctrinales (`docs/books/`)](../books/)
- [Archives historiques (`docs/archive/`)](../archive/)
