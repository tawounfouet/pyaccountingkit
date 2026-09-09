# 20 - PyAccountingKit - Registre consolidé des Architecture Decision Records (ADR)

> **Projet** : PyAccountingKit  
> **Document** : `20_PYACCOUNTINGKIT_ADR_REGISTER.md`  
> **Statut** : P1.9 - Registre ADR consolidé - **rafraîchi après P2.1/P2.2/P2.3**  
> **Langue** : Français  
> **Baseline couverte** : documents `01` à `23`  
> **Objet** : Centraliser, indexer, gouverner et rendre traçables toutes les décisions d'architecture formalisées dans la documentation PyAccountingKit.

---

# 1. Résumé exécutif

La baseline architecturale actuelle contient désormais **785 ADR distincts**, répartis sur **24 namespaces**.

Le précédent registre P1.9 contenait :

```text
605 ADR
21 namespaces
```

Le refresh P2 ajoute :

```text
ADR-CON : 70
ADR-REC : 60
ADR-AFA : 50
```

Soit :

```text
605 + 70 + 60 + 50 = 785 ADR
```

Le registre couvre maintenant :

```text
P0 - fondations
P1 - capacités métier / industrialisation
P2.1 - consolidation
P2.2 - réconciliation
P2.3 - frontières Corporate Finance
```

Ce fichier reste l'**index décisionnel canonique**. Les documents spécialisés conservent le contexte, les alternatives et les détails d'implémentation.

---

# 2. Statut de la baseline

Tous les ADR extraits des documents actuels sont enregistrés avec :

```text
ACCEPTED_BASELINE
```

Une décision n'est jamais supprimée silencieusement. Elle peut évoluer via :

```text
PROPOSED
ACCEPTED_BASELINE
DEPRECATED
SUPERSEDED
REJECTED
EXPERIMENTAL
```

---

# 3. Convention d'identification

```text
ADR-<NAMESPACE>-<NNN>
```

Exemples :

```text
ADR-LED-001
ADR-CON-070
ADR-REC-060
ADR-AFA-050
```

Les identifiants restent immuables.

---

# 4. Catalogue des namespaces


| Namespace | Domaine | Phase | ADR | Document source |
|---|---|---:|---:|---|
| `ARCH` | Architecture globale | `P0.2` | 19 | `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md` |
| `DOM` | Domain Model & Bounded Contexts | `P0.3` | 30 | `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md` |
| `RULE` | Règles & invariants comptables | `P0.4` | 18 | `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md` |
| `POL` | Policies - Recognition & Measurement | `P0.5` | 20 | `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md` |
| `REF` | Reference Data | `P0.6` | 20 | `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md` |
| `COA` | Company Chart of Accounts | `P0.7` | 24 | `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md` |
| `LED` | Ledger, Posting & Reversal | `P0.8` | 30 | `07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md` |
| `CLOSE` | Closing, Accruals, Provisions & Adjustments | `P0.9` | 30 | `08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md` |
| `CTRL` | Controls | `P0.10` | 10 | `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md` |
| `AUD` | Audit | `P0.10` | 6 | `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md` |
| `TRACE` | Traceability, Provenance & Reproducibility | `P0.10` | 16 | `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md` |
| `PERS` | Persistence, Concurrency & Adapters | `P0.11` | 40 | `10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md` |
| `TEST` | Testing & Quality | `P0.12` | 30 | `11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md` |
| `IMP` | Accounting Imports & FEC | `P1.1` | 40 | `12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md` |
| `REP` | Financial Statements & Regulatory Reporting | `P1.2` | 40 | `13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md` |
| `ANA` | Financial Analysis & Indicators | `P1.3` | 40 | `14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md` |
| `SUB` | Subledgers & Operational Accounting | `P1.4` | 32 | `15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md` |
| `API` | Public API | `P1.5` | 40 | `16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md` |
| `REL` | Release & Versioning | `P1.6` | 40 | `17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md` |
| `CFA` | CFA FRA Extraction & Migration | `P1.7` | 40 | `18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md` |
| `RFM` | Regulatory Framework Integration | `P1.8` | 40 | `19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md` |
| `CON` | Consolidation | `P2.1` | 70 | `21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md` |
| `REC` | Reconciliation | `P2.2` | 60 | `22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md` |
| `AFA` | Advanced Financial Analysis Boundaries | `P2.3` | 50 | `23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md` |

**Total : 785 ADR - 24 namespaces.**


---

# 5. Évolution depuis la baseline précédente

| Namespace ajouté | Document | ADR ajoutés | Effet architectural |
|---|---|---:|---|
| `CON` | `21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md` | 70 | Groupe, périmètre, FX, IC, éliminations, NCI, snapshots |
| `REC` | `22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md` | 60 | Matching générique, différences, résolution, banque, subledger/GL, IC |
| `AFA` | `23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md` | 50 | Frontière ferme entre analyse historique et Corporate Finance |

La progression devient :

```text
P0/P1 baseline
    605 ADR
        |
        +--> Consolidation +70
        +--> Reconciliation +60
        +--> Advanced Finance Boundaries +50
        |
        v
    785 ADR
```

---

# 6. Vue d'ensemble des dépendances conceptuelles

```text
ARCH
  |
  +--> DOM
  |     +--> RULE
  |     +--> POL
  |     +--> REF
  |     +--> COA
  |     +--> LED
  |     +--> CLOSE
  |
  +--> CTRL / AUD / TRACE
  |
  +--> PERS
  |     +--> TEST
  |
  +--> IMP
  +--> REP
  +--> ANA
  +--> SUB
  |
  +--> API
  +--> REL
  +--> CFA
  +--> RFM
  |
  +--> CON
  |     +--> REC
  |
  +--> AFA
```

`CON`, `REC` et `AFA` étendent l'architecture sans remettre en cause les invariants P0/P1.

---

# 7. Décisions transverses structurantes


## 7.1 Architecture hexagonale et neutralité technologique

Le domaine reste indépendant des ORMs, frameworks web et choix de persistance.

| ADR | Décision |
|---|---|
| `ADR-ARCH-001` | Architecture domain-first et ports/adapters |
| `ADR-ARCH-002` | Django et SQLAlchemy restent hors du domaine |
| `ADR-PERS-001` | Le domaine ne dépend d'aucun ORM |
| `ADR-API-003` | L'API publique n'expose ni ORM ni SQL |
| `ADR-CFA-003` | Les modèles Django ne sont pas copiés dans le domain |

## 7.2 Source réglementaire et anti-duplication

`regulatory-accounting-data-framework` demeure la source réglementaire structurée ; PyAccountingKit consomme via provider.

| ADR | Décision |
|---|---|
| `ADR-ARCH-003` | `regulatory-accounting-data-framework` est consommé via provider |
| `ADR-REF-001` | `regulatory-accounting-data-framework` est la source de vérité réglementaire structurée |
| `ADR-REF-002` | PyAccountingKit consomme les données via `AccountingReferenceProvider` |
| `ADR-CFA-030` | Les référentiels locaux CFA FRA cessent d'être source de vérité |
| `ADR-CFA-031` | `regulatory-accounting-data-framework` devient la source réglementaire |
| `ADR-RFM-002` | `regulatory-accounting-data-framework` reste la source réglementaire |

## 7.3 Comptabilité canonique et corrections

`JournalEntry` reste l'agrégat comptable central ; les projections sont dérivées et les corrections postées utilisent reversal/remplacement.

| ADR | Décision |
|---|---|
| `ADR-DOM-002` | `JournalEntry` est un Aggregate Root |
| `ADR-LED-001` | `JournalEntry` est l'Aggregate Root transactionnel central |
| `ADR-LED-003` | La source canonique est constituée des écritures/lignes/comptes/périodes |
| `ADR-CFA-006` | Le workflow DRAFT -> VALIDATED -> POSTED -> REVERSED est conservé |
| `ADR-CFA-010` | Le Reversal comportemental est conservé, la convention de numéro est policy-driven |

## 7.4 Fail-closed et sécurité sémantique

Les ambiguïtés critiques de règle, mapping, autorité réglementaire ou matching ne sont jamais transformées silencieusement en autorité exécutable.

| ADR | Décision |
|---|---|
| `ADR-RULE-018` | Les règles critiques suivent une stratégie fail-closed |
| `ADR-RFM-018` | Un account hint marqué non exécutable reste un candidat |
| `ADR-RFM-019` | Une confidence élevée ne contourne jamais `human_review_required` |
| `ADR-RFM-035` | Les erreurs d'ambiguïté réglementaire sont fail-closed |
| `ADR-REC-013` | Toute ambiguïté de match critique est fail-closed |
| `ADR-AFA-049` | Toute proposition d'ajouter Corporate Finance au core doit passer par un nouvel ADR de scope |

## 7.5 Audit, provenance, snapshots et replay

Les résultats importants restent traçables, pinés et rejouables.

| ADR | Décision |
|---|---|
| `ADR-AUD-001` | `AuditEvent` est append-only |
| `ADR-TRACE-003` | Les reference snapshots sont pinés pour les calculs réglementaires |
| `ADR-TRACE-004` | Les policy versions sont pinées pour les calculs métier |
| `ADR-TRACE-012` | Les snapshots historiques restent immutables |
| `ADR-CON-050` | La reproductibilité pinne scope, ownership, mappings, policies, FX et sources |
| `ADR-REC-043` | Le replay pinne toutes les versions de policies/strategies |

## 7.6 Consolidation vs comptabilité individuelle

La consolidation est un bounded context séparé avec son propre ledger et ses propres snapshots, sans mutation des ledgers individuels.

| ADR | Décision |
|---|---|
| `ADR-CON-001` | `Consolidation` est un bounded context distinct de la comptabilité individuelle |
| `ADR-CON-002` | La consolidation ne modifie jamais les ledgers individuels |
| `ADR-CON-024` | `ConsolidationEntry` possède son propre ledger |
| `ADR-CON-043` | Un ConsolidationSnapshot publié est immutable |
| `ADR-CON-046` | Le drill-down consolidé doit atteindre les JournalEntryLines individuelles |

## 7.7 Réconciliation vs posting et consolidation

La réconciliation rapproche et explique ; le Posting comptabilise et Consolidation reste propriétaire des éliminations.

| ADR | Décision |
|---|---|
| `ADR-REC-001` | `Reconciliation` est un bounded context distinct du Posting |
| `ADR-REC-020` | Toute écriture corrective passe par `JournalEntryProposal` puis Posting normal |
| `ADR-REC-026` | L'intercompany matching peut être délégué à Reconciliation |
| `ADR-REC-027` | Consolidation reste propriétaire des éliminations |
| `ADR-REC-060` | La réconciliation est un consommateur transversal, jamais une seconde source comptable canonique |

## 7.8 Analyse historique vs Corporate Finance

PyAccountingKit conserve l'analyse financière historique ; VAN/TRI/WACC/DCF/Monte Carlo sortent vers un futur framework Corporate Finance/Risk.

| ADR | Décision |
|---|---|
| `ADR-AFA-001` | PyAccountingKit reste un framework comptable et d'analyse financière historique, pas un moteur Corporate Finance général |
| `ADR-AFA-002` | Les capacités nécessitant hypothèses futures, données de marché ou discounting sortent du core |
| `ADR-AFA-011` | VAN/NPV relève du Corporate Finance |
| `ADR-AFA-018` | WACC relève du Corporate Finance |
| `ADR-AFA-020` | DCF, FCFF/FCFE forecast et Terminal Value restent hors core |
| `ADR-AFA-024` | Monte Carlo reste hors PyAccountingKit |

## 7.9 Bridge vers Corporate Finance

`FinancialFactsSnapshot` constitue le bridge conceptuel ; les données de marché, hypothèses et résultats de valorisation restent distincts des accounting facts.

| ADR | Décision |
|---|---|
| `ADR-AFA-032` | `FinancialFactsSnapshot` est le bridge conceptuel recommandé vers Corporate Finance |
| `ADR-AFA-033` | Corporate Finance ne dépend pas des repositories/ORM internes de PyAccountingKit |
| `ADR-AFA-034` | Corporate Finance ne modifie jamais les écritures comptables |
| `ADR-AFA-035` | Les données de marché restent distinctes des données comptables |
| `ADR-AFA-036` | Les assumptions prospectives restent distinctes des accounting facts |
| `ADR-AFA-037` | Les résultats de valuation sont des decision-support artifacts, pas des accounting facts |

## 7.10 API publique et gouvernance de release

La façade publique et les contrats sont versionnés, gelés avant stable et accompagnés de manifests de compatibilité.

| ADR | Décision |
|---|---|
| `ADR-API-001` | `AccountingApplication` est la façade publique principale |
| `ADR-API-040` | Le gel de l'API publique précède la release stable |
| `ADR-REL-001` | PyAccountingKit utilise Semantic Versioning |
| `ADR-REL-013` | Le gel de l'API publique intervient avant `1.0.0` |
| `ADR-RFM-039` | `REGULATORY_COMPATIBILITY_MATRIX` est un artefact de release |


---

# 8. Règles de gouvernance

```text
1. ADR IDs are immutable.
2. Accepted decisions are never silently deleted.
3. Supersession is explicit.
4. Breaking architectural changes require impact analysis.
5. Regulatory authority changes require source evidence.
6. Accounting semantic changes require golden/replay impact analysis.
7. Persistence changes require transaction/concurrency impact analysis.
8. Public API changes require SemVer impact analysis.
9. P2 bounded-context changes must not silently weaken P0/P1 invariants.
10. The register is updated together with the architectural decision.
```

---

# 9. Priorité en cas de contradiction

```text
1. Explicit SUPERSEDED relation
2. Explicit negative regulatory constraint
3. Universal accounting invariant
4. Accepted domain / policy contract
5. Accepted application / persistence contract
6. Accepted bounded-context-specific contract
7. Adapter-specific decision
8. Historical implementation behavior
```

Le simple fait qu'un document soit plus récent ne lui permet pas d'écraser silencieusement un invariant antérieur.

---

# 10. P2 - contraintes de cohérence ajoutées

## 10.1 Consolidation

```text
Consolidation cannot mutate individual ledgers.
ConsolidationEntry uses a separate group ledger.
Published ConsolidationSnapshot is immutable.
```

## 10.2 Reconciliation

```text
Reconciliation is not Posting.
Candidate is not Match.
Tolerance is not Write-Off.
Consolidation remains owner of eliminations.
```

## 10.3 Advanced Financial Analysis

```text
Historical accounting analysis stays in PyAccountingKit.
Forward assumptions / valuation / WACC / NPV / IRR / DCF / Monte Carlo stay outside core.
```

---

# 11. Template d'un nouvel ADR

```markdown
# ADR-<NAMESPACE>-<NNN> - <Titre>

## Statut
PROPOSED

## Contexte
...

## Décision
...

## Alternatives considérées
...

## Conséquences
...

## Compatibilité
- Public API:
- Persistence:
- Regulatory:
- Snapshots:
- Migration:
- Bounded contexts:

## Tests / preuves
...

## Supersession
- supersedes: []
- superseded_by: null
```

---

# 12. Métadonnées machine-readable recommandées

```text
adr_id
title
namespace
status
decision
source_document
introduced_in
last_reviewed_in
supersedes[]
superseded_by?
related_adrs[]
impact_domains[]
breaking?
requires_migration?
requires_regulatory_review?
requires_golden_update?
```

---

# 13. Registre complet des 785 ADR


## 13.1 `ARCH` - Architecture globale

**Phase** : `P0.2`  
**Source** : `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`  
**Nombre d'ADR** : 19

| ADR | Statut | Décision |
|---|---|---|
| `ADR-ARCH-001` | `ACCEPTED_BASELINE` | Architecture domain-first et ports/adapters |
| `ADR-ARCH-002` | `ACCEPTED_BASELINE` | Django et SQLAlchemy restent hors du domaine |
| `ADR-ARCH-003` | `ACCEPTED_BASELINE` | `regulatory-accounting-data-framework` est consommé via provider |
| `ADR-ARCH-004` | `ACCEPTED_BASELINE` | CFA FRA est une référence comportementale, pas une dépendance |
| `ADR-ARCH-005` | `ACCEPTED_BASELINE` | Les ouvrages sont des sources doctrinales, pas des sources réglementaires actuelles |
| `ADR-ARCH-006` | `ACCEPTED_BASELINE` | La chaîne cible est `Reference -> Policies -> Core -> Ledger -> Reporting -> Analysis` |
| `ADR-ARCH-007` | `ACCEPTED_BASELINE` | `AccountingPolicySet` est versionné |
| `ADR-ARCH-008` | `ACCEPTED_BASELINE` | Recognition, Measurement, Posting, Presentation et Analysis sont distincts |
| `ADR-ARCH-009` | `ACCEPTED_BASELINE` | Entries/lines/accounts/periods forment la source canonique minimale |
| `ADR-ARCH-010` | `ACCEPTED_BASELINE` | Ledger et états financiers sont des projections |
| `ADR-ARCH-011` | `ACCEPTED_BASELINE` | Financial Analysis est downstream et read-only |
| `ADR-ARCH-012` | `ACCEPTED_BASELINE` | Posting et reversal sont transactionnels |
| `ADR-ARCH-013` | `ACCEPTED_BASELINE` | FEC est un adapter optionnel |
| `ADR-ARCH-014` | `ACCEPTED_BASELINE` | Mapping réglementaire et mapping de présentation sont distincts |
| `ADR-ARCH-015` | `ACCEPTED_BASELINE` | Les publications peuvent être figées dans `ReportSnapshot` |
| `ADR-ARCH-016` | `ACCEPTED_BASELINE` | Les résultats analytiques peuvent être figés dans `AnalysisSnapshot` |
| `ADR-ARCH-017` | `ACCEPTED_BASELINE` | Les heuristiques sont des suggestions/configurations |
| `ADR-ARCH-018` | `ACCEPTED_BASELINE` | Corporate finance avancée est hors coeur obligatoire |
| `ADR-ARCH-019` | `ACCEPTED_BASELINE` | Le package démarre comme repository unique avec extensions optionnelles |

## 13.2 `DOM` - Domain Model & Bounded Contexts

**Phase** : `P0.3`  
**Source** : `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`  
**Nombre d'ADR** : 30

| ADR | Statut | Décision |
|---|---|---|
| `ADR-DOM-001` | `ACCEPTED_BASELINE` | `AccountingEntity` est le terme générique, `Organization` reste une traduction applicative |
| `ADR-DOM-002` | `ACCEPTED_BASELINE` | `JournalEntry` est un Aggregate Root |
| `ADR-DOM-003` | `ACCEPTED_BASELINE` | `JournalEntryLine` appartient à l'agrégat `JournalEntry` |
| `ADR-DOM-004` | `ACCEPTED_BASELINE` | `CompanyAccount` est un Aggregate Root indépendant |
| `ADR-DOM-005` | `ACCEPTED_BASELINE` | Un chart ne charge pas tous ses comptes comme enfants d'agrégat |
| `ADR-DOM-006` | `ACCEPTED_BASELINE` | `AccountingPeriod` peut être verrouillé comme Aggregate Root indépendant |
| `ADR-DOM-007` | `ACCEPTED_BASELINE` | General Ledger et Trial Balance sont des projections |
| `ADR-DOM-008` | `ACCEPTED_BASELINE` | `ReferenceAccount` est un objet externe immutable |
| `ADR-DOM-009` | `ACCEPTED_BASELINE` | `AccountingPolicySet` est un Aggregate Root versionné |
| `ADR-DOM-010` | `ACCEPTED_BASELINE` | Recognition, Measurement, Posting, Presentation et Analysis sont distincts |
| `ADR-DOM-011` | `ACCEPTED_BASELINE` | `PolicyExecutionTrace` est immutable |
| `ADR-DOM-012` | `ACCEPTED_BASELINE` | `RegulatoryAccountBinding` est distinct de `StatementAccountMapping` |
| `ADR-DOM-013` | `ACCEPTED_BASELINE` | FEC est traduit via Anti-Corruption Layer |
| `ADR-DOM-014` | `ACCEPTED_BASELINE` | `AccountingImportBatch` protège le workflow d'import sans contenir toutes les raw lines |
| `ADR-DOM-015` | `ACCEPTED_BASELINE` | `AuditEvent` est append-only |
| `ADR-DOM-016` | `ACCEPTED_BASELINE` | `ReportSnapshot` final est immutable |
| `ADR-DOM-017` | `ACCEPTED_BASELINE` | `Financial Analysis` est un bounded context read-only downstream |
| `ADR-DOM-018` | `ACCEPTED_BASELINE` | `AnalysisSnapshot` final est immutable |
| `ADR-DOM-019` | `ACCEPTED_BASELINE` | Les heuristiques de mapping ne sont pas des invariants universels |
| `ADR-DOM-020` | `ACCEPTED_BASELINE` | Les transactions inter-agrégats sont orchestrées par l'Application Layer |
| `ADR-DOM-021` | `ACCEPTED_BASELINE` | Les read models peuvent être optimisés indépendamment du write model |
| `ADR-DOM-022` | `ACCEPTED_BASELINE` | Les identités interne, business et réglementaire sont distinctes |
| `ADR-DOM-023` | `ACCEPTED_BASELINE` | `Money` utilise `Decimal` |
| `ADR-DOM-024` | `ACCEPTED_BASELINE` | Le multi-entity scoping est obligatoire dans les ports |
| `ADR-DOM-025` | `ACCEPTED_BASELINE` | Inventory, Fixed Assets et Accruals & Provisions sont des specialized domains futurs |
| `ADR-DOM-026` | `ACCEPTED_BASELINE` | Ces specialized domains produisent des propositions d'écriture mais ne contournent jamais le Posting Engine |
| `ADR-DOM-027` | `ACCEPTED_BASELINE` | Consolidation est un bounded context P2 distinct des ledgers statutaires |
| `ADR-DOM-028` | `ACCEPTED_BASELINE` | Les ajustements de consolidation ne modifient pas les écritures statutaires |
| `ADR-DOM-029` | `ACCEPTED_BASELINE` | Reconciliation reste un supporting context avancé |
| `ADR-DOM-030` | `ACCEPTED_BASELINE` | Corporate Finance avancée reste hors du coeur PyAccountingKit |

## 13.3 `RULE` - Règles & invariants comptables

**Phase** : `P0.4`  
**Source** : `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`  
**Nombre d'ADR** : 18

| ADR | Statut | Décision |
|---|---|---|
| `ADR-RULE-001` | `ACCEPTED_BASELINE` | Toutes les règles sont typées par `RuleKind` |
| `ADR-RULE-002` | `ACCEPTED_BASELINE` | `SUM(debit) = SUM(credit)` est un invariant du moteur |
| `ADR-RULE-003` | `ACCEPTED_BASELINE` | Débit et crédit simultanément positifs sur une ligne sont interdits |
| `ADR-RULE-004` | `ACCEPTED_BASELINE` | `POSTED` est immutable |
| `ADR-RULE-005` | `ACCEPTED_BASELINE` | Les corrections passent par reversal + replacement |
| `ADR-RULE-006` | `ACCEPTED_BASELINE` | Posting normal interdit sur période fermée |
| `ADR-RULE-007` | `ACCEPTED_BASELINE` | Les principes de prudence, continuité et permanence ne sont pas des invariants universels |
| `ADR-RULE-008` | `ACCEPTED_BASELINE` | Le rattachement est une accounting method/policy |
| `ADR-RULE-009` | `ACCEPTED_BASELINE` | Les bases de mesure appartiennent à `MeasurementPolicy` |
| `ADR-RULE-010` | `ACCEPTED_BASELINE` | Toute policy exécutable est versionnée |
| `ADR-RULE-011` | `ACCEPTED_BASELINE` | Toute policy automatisée doit être explicable par `PolicyExecutionTrace` |
| `ADR-RULE-012` | `ACCEPTED_BASELINE` | Les imports ne contournent pas les règles de validation/posting |
| `ADR-RULE-013` | `ACCEPTED_BASELINE` | Les mappings candidats ne sont pas exécutables par défaut |
| `ADR-RULE-014` | `ACCEPTED_BASELINE` | L'égalité de code ne prouve pas l'équivalence sémantique |
| `ADR-RULE-015` | `ACCEPTED_BASELINE` | Les états financiers et balances sont des projections |
| `ADR-RULE-016` | `ACCEPTED_BASELINE` | Les définitions analytiques ne sont pas des règles comptables transactionnelles |
| `ADR-RULE-017` | `ACCEPTED_BASELINE` | `Decimal` est obligatoire pour les montants comptables |
| `ADR-RULE-018` | `ACCEPTED_BASELINE` | Les règles critiques suivent une stratégie fail-closed |

## 13.4 `POL` - Policies - Recognition & Measurement

**Phase** : `P0.5`  
**Source** : `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`  
**Nombre d'ADR** : 20

| ADR | Statut | Décision |
|---|---|---|
| `ADR-POL-001` | `ACCEPTED_BASELINE` | `AccountingPolicySet` est un Aggregate Root versionné |
| `ADR-POL-002` | `ACCEPTED_BASELINE` | Reference Data et Policies sont des bounded contexts distincts |
| `ADR-POL-003` | `ACCEPTED_BASELINE` | Recognition et Measurement sont distincts |
| `ADR-POL-004` | `ACCEPTED_BASELINE` | Initial Measurement et Subsequent Measurement sont distincts |
| `ADR-POL-005` | `ACCEPTED_BASELINE` | `MeasurementBasis` est explicite |
| `ADR-POL-006` | `ACCEPTED_BASELINE` | Une base de mesure disponible n'est pas automatiquement applicable |
| `ADR-POL-007` | `ACCEPTED_BASELINE` | Les policies ne postent jamais directement |
| `ADR-POL-008` | `ACCEPTED_BASELINE` | Les policies produisent des `JournalEntryProposal` |
| `ADR-POL-009` | `ACCEPTED_BASELINE` | Les comptes sont résolus via `AccountRole` |
| `ADR-POL-010` | `ACCEPTED_BASELINE` | Les policies sont résolues par scope et priorité |
| `ADR-POL-011` | `ACCEPTED_BASELINE` | Les conflits de résolution sont fail-closed |
| `ADR-POL-012` | `ACCEPTED_BASELINE` | `PolicyExecutionTrace` est immutable |
| `ADR-POL-013` | `ACCEPTED_BASELINE` | Toute dépendance réglementaire conserve un ReferenceSnapshot |
| `ADR-POL-014` | `ACCEPTED_BASELINE` | Toute observation externe ayant influencé une mesure est tracée |
| `ADR-POL-015` | `ACCEPTED_BASELINE` | Prudence et continuité influencent des policies, pas le Posting Engine |
| `ADR-POL-016` | `ACCEPTED_BASELINE` | La permanence des méthodes est soutenue par le versioning |
| `ADR-POL-017` | `ACCEPTED_BASELINE` | Un changement de méthode passe par `PolicyMigrationPlan` |
| `ADR-POL-018` | `ACCEPTED_BASELINE` | L'héritage de policy n'est jamais implicite |
| `ADR-POL-019` | `ACCEPTED_BASELINE` | Le framework supporte policies déclaratives et policies codées |
| `ADR-POL-020` | `ACCEPTED_BASELINE` | Les specialized domains utilisent le moteur de policy plutôt que de dupliquer les règles |

## 13.5 `REF` - Reference Data

**Phase** : `P0.6`  
**Source** : `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`  
**Nombre d'ADR** : 20

| ADR | Statut | Décision |
|---|---|---|
| `ADR-REF-001` | `ACCEPTED_BASELINE` | `regulatory-accounting-data-framework` est la source de vérité réglementaire structurée |
| `ADR-REF-002` | `ACCEPTED_BASELINE` | PyAccountingKit consomme les données via `AccountingReferenceProvider` |
| `ADR-REF-003` | `ACCEPTED_BASELINE` | Le domaine ne connaît aucun chemin de repository |
| `ADR-REF-004` | `ACCEPTED_BASELINE` | Les identifiants réglementaires externes sont préservés |
| `ADR-REF-005` | `ACCEPTED_BASELINE` | `ReferenceAccount` est immutable |
| `ADR-REF-006` | `ACCEPTED_BASELINE` | Parent/enfants structurés sont consommés tels quels |
| `ADR-REF-007` | `ACCEPTED_BASELINE` | Un effective plan fourni par la source est consommé directement |
| `ADR-REF-008` | `ACCEPTED_BASELINE` | PyAccountingKit ne rejoue pas arbitrairement les overlays si un effective plan existe |
| `ADR-REF-009` | `ACCEPTED_BASELINE` | Relation de famille et héritage sont distincts |
| `ADR-REF-010` | `ACCEPTED_BASELINE` | Les negative constraints sont préservées |
| `ADR-REF-011` | `ACCEPTED_BASELINE` | L'égalité de code ne prouve pas l'équivalence sémantique |
| `ADR-REF-012` | `ACCEPTED_BASELINE` | Les crosswalks candidats restent non exécutables jusqu'à validation |
| `ADR-REF-013` | `ACCEPTED_BASELINE` | Les concepts neutres ne sont pas des règles comptables |
| `ADR-REF-014` | `ACCEPTED_BASELINE` | Les concept bindings absents ne sont jamais inventés |
| `ADR-REF-015` | `ACCEPTED_BASELINE` | Structure de reporting officielle et account hints candidats sont séparés |
| `ADR-REF-016` | `ACCEPTED_BASELINE` | `account_hints_executable=false` est fail-closed |
| `ADR-REF-017` | `ACCEPTED_BASELINE` | Les versions de dataset et éditions de standard sont distinctes |
| `ADR-REF-018` | `ACCEPTED_BASELINE` | Les références utilisées en production sont figées dans `AccountingReferenceSnapshot` |
| `ADR-REF-019` | `ACCEPTED_BASELINE` | Une mise à jour réglementaire ne mute pas automatiquement les charts existants |
| `ADR-REF-020` | `ACCEPTED_BASELINE` | Tous les adapters passent une contract suite commune |

## 13.6 `COA` - Company Chart of Accounts

**Phase** : `P0.7`  
**Source** : `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`  
**Nombre d'ADR** : 24

| ADR | Statut | Décision |
|---|---|---|
| `ADR-COA-001` | `ACCEPTED_BASELINE` | `CompanyAccount.code` est une chaîne |
| `ADR-COA-002` | `ACCEPTED_BASELINE` | La longueur d'un code n'est pas un invariant universel |
| `ADR-COA-003` | `ACCEPTED_BASELINE` | Les conventions numériques d'un référentiel sont `REFERENCE_SPECIFIC_RULE` |
| `ADR-COA-004` | `ACCEPTED_BASELINE` | `CompanyAccount` et `ReferenceAccount` sont des objets distincts |
| `ADR-COA-005` | `ACCEPTED_BASELINE` | Un compte d'entreprise conserve un `RegulatoryAccountBinding` explicite |
| `ADR-COA-006` | `ACCEPTED_BASELINE` | Un même `ReferenceAccount` peut être lié à plusieurs `CompanyAccount` |
| `ADR-COA-007` | `ACCEPTED_BASELINE` | `CompanyChartOfAccounts` ne contient pas tous les comptes comme enfants d'agrégat |
| `ADR-COA-008` | `ACCEPTED_BASELINE` | `CompanyAccount` est un Aggregate Root indépendant |
| `ADR-COA-009` | `ACCEPTED_BASELINE` | Parent/enfant est une relation explicite, pas une inférence obligatoire par préfixe |
| `ADR-COA-010` | `ACCEPTED_BASELINE` | Numeric fixed, numeric variable, segmented et alphanumeric sont supportés |
| `ADR-COA-011` | `ACCEPTED_BASELINE` | La longueur peut varier par famille de comptes |
| `ADR-COA-012` | `ACCEPTED_BASELINE` | `REFERENCE_ONLY` est le mode de génération prudent par défaut |
| `ADR-COA-013` | `ACCEPTED_BASELINE` | `PAD_TO_LENGTH` n'est utilisé que par policy explicite |
| `ADR-COA-014` | `ACCEPTED_BASELINE` | Compte collectif et compte auxiliaire sont distincts |
| `ADR-COA-015` | `ACCEPTED_BASELINE` | `SUBLEDGER`, `EXTENDED_ACCOUNT_CODE` et `HYBRID` sont des modes différents |
| `ADR-COA-016` | `ACCEPTED_BASELINE` | Les heuristiques de préfixe ne sont jamais des invariants universels |
| `ADR-COA-017` | `ACCEPTED_BASELINE` | `AccountRole` est distinct du code et du binding réglementaire |
| `ADR-COA-018` | `ACCEPTED_BASELINE` | Les changements majeurs de codification passent par une migration versionnée |
| `ADR-COA-019` | `ACCEPTED_BASELINE` | Les codes retirés ne sont pas réutilisés automatiquement |
| `ADR-COA-020` | `ACCEPTED_BASELINE` | Un nouveau référentiel ne mute pas silencieusement le chart actif |
| `ADR-COA-021` | `ACCEPTED_BASELINE` | Le generator consomme les effective plans déjà résolus |
| `ADR-COA-022` | `ACCEPTED_BASELINE` | L'unicité du code est garantie dans le scope du chart |
| `ADR-COA-023` | `ACCEPTED_BASELINE` | L'absence de cycles de hiérarchie est un invariant |
| `ADR-COA-024` | `ACCEPTED_BASELINE` | Les mappings candidats ne deviennent pas des bindings actifs sans validation |

## 13.7 `LED` - Ledger, Posting & Reversal

**Phase** : `P0.8`  
**Source** : `07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`  
**Nombre d'ADR** : 30

| ADR | Statut | Décision |
|---|---|---|
| `ADR-LED-001` | `ACCEPTED_BASELINE` | `JournalEntry` est l'Aggregate Root transactionnel central |
| `ADR-LED-002` | `ACCEPTED_BASELINE` | `JournalEntryLine` appartient à `JournalEntry` |
| `ADR-LED-003` | `ACCEPTED_BASELINE` | La source canonique est constituée des écritures/lignes/comptes/périodes |
| `ADR-LED-004` | `ACCEPTED_BASELINE` | Journal report, General Ledger et Trial Balance sont des projections |
| `ADR-LED-005` | `ACCEPTED_BASELINE` | DRAFT ne contribue pas au ledger |
| `ADR-LED-006` | `ACCEPTED_BASELINE` | VALIDATED ne contribue pas au ledger |
| `ADR-LED-007` | `ACCEPTED_BASELINE` | Toute écriture postée est équilibrée |
| `ADR-LED-008` | `ACCEPTED_BASELINE` | Toute écriture POSTED est immutable |
| `ADR-LED-009` | `ACCEPTED_BASELINE` | La correction passe par reversal + nouvelle écriture |
| `ADR-LED-010` | `ACCEPTED_BASELINE` | Une reversal est une nouvelle écriture |
| `ADR-LED-011` | `ACCEPTED_BASELINE` | L'écriture originale reste historiquement visible |
| `ADR-LED-012` | `ACCEPTED_BASELINE` | Les lignes d'une écriture REVERSED restent dans le ledger ; la neutralisation vient de la reversal |
| `ADR-LED-013` | `ACCEPTED_BASELINE` | P0 supporte la reversal intégrale |
| `ADR-LED-014` | `ACCEPTED_BASELINE` | Posting et reversal sont atomiques |
| `ADR-LED-015` | `ACCEPTED_BASELINE` | Le domaine exprime la concurrence sans dépendre d'un mécanisme SQL |
| `ADR-LED-016` | `ACCEPTED_BASELINE` | `revision` supporte optimistic concurrency |
| `ADR-LED-017` | `ACCEPTED_BASELINE` | Les adapters peuvent utiliser pessimistic locking |
| `ADR-LED-018` | `ACCEPTED_BASELINE` | `signed_balance = debit - credit` est une convention de projection P0 |
| `ADR-LED-019` | `ACCEPTED_BASELINE` | Running balance utilise un ordre déterministe |
| `ADR-LED-020` | `ACCEPTED_BASELINE` | Opening balance est calculé depuis les mouvements antérieurs |
| `ADR-LED-021` | `ACCEPTED_BASELINE` | BEFORE_ADJUSTMENTS / ADJUSTED / POST_CLOSING sont des variants de projection |
| `ADR-LED-022` | `ACCEPTED_BASELINE` | La composition des variants est versionnée par policy |
| `ADR-LED-023` | `ACCEPTED_BASELINE` | Les comptes à solde nul sont une option de présentation |
| `ADR-LED-024` | `ACCEPTED_BASELINE` | Le drill-down jusqu'à `JournalEntryLine` est une capacité architecturale |
| `ADR-LED-025` | `ACCEPTED_BASELINE` | Les projections matérialisées restent reconstructibles |
| `ADR-LED-026` | `ACCEPTED_BASELINE` | Toutes les queries sont scopées par `AccountingEntityId` |
| `ADR-LED-027` | `ACCEPTED_BASELINE` | L'import direct POSTED exige une policy explicite de source déjà validée |
| `ADR-LED-028` | `ACCEPTED_BASELINE` | `EntryType` est distinct de `JournalType` |
| `ADR-LED-029` | `ACCEPTED_BASELINE` | `AccountRole`/policy détermine les catégories métier, pas un préfixe universel |
| `ADR-LED-030` | `ACCEPTED_BASELINE` | Le Ledger ne connaît pas Django, SQLAlchemy ou PostgreSQL |

## 13.8 `CLOSE` - Closing, Accruals, Provisions & Adjustments

**Phase** : `P0.9`  
**Source** : `08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`  
**Nombre d'ADR** : 30

| ADR | Statut | Décision |
|---|---|---|
| `ADR-CLOSE-001` | `ACCEPTED_BASELINE` | La clôture est un workflow, pas un simple changement de statut |
| `ADR-CLOSE-002` | `ACCEPTED_BASELINE` | `ClosingRun` orchestre les étapes de clôture |
| `ADR-CLOSE-003` | `ACCEPTED_BASELINE` | Accounting inventory et Inventory bounded context sont distincts |
| `ADR-CLOSE-004` | `ACCEPTED_BASELINE` | Les cut-off adjustments utilisent `Accounting Policies & Measurement` |
| `ADR-CLOSE-005` | `ACCEPTED_BASELINE` | Accrued expense, accrued income, prepaid expense et deferred income sont des concepts génériques |
| `ADR-CLOSE-006` | `ACCEPTED_BASELINE` | Les numéros de comptes nationaux ne sont pas codés dans le core |
| `ADR-CLOSE-007` | `ACCEPTED_BASELINE` | Les écritures de régularisation passent par JournalEntryProposal -> Validation -> Posting |
| `ADR-CLOSE-008` | `ACCEPTED_BASELINE` | Une policy détermine si une régularisation est automatiquement extournée |
| `ADR-CLOSE-009` | `ACCEPTED_BASELINE` | Inventory calcule les valeurs de stocks ; Closing ne calcule pas FIFO/WAC |
| `ADR-CLOSE-010` | `ACCEPTED_BASELINE` | Fixed Assets calcule l'amortissement ; Closing orchestre son posting |
| `ADR-CLOSE-011` | `ACCEPTED_BASELINE` | Impairment est distinct de Provision |
| `ADR-CLOSE-012` | `ACCEPTED_BASELINE` | Provision recognition et provision measurement sont distincts |
| `ADR-CLOSE-013` | `ACCEPTED_BASELINE` | Les règles réglementaires historiques de l'ouvrage ne sont pas supposées actuelles |
| `ADR-CLOSE-014` | `ACCEPTED_BASELINE` | BEFORE_ADJUSTMENTS est le point de départ du close |
| `ADR-CLOSE-015` | `ACCEPTED_BASELINE` | ADJUSTED est reconstruit après les ajustements |
| `ADR-CLOSE-016` | `ACCEPTED_BASELINE` | POST_CLOSING est reconstruit après les closing entries |
| `ADR-CLOSE-017` | `ACCEPTED_BASELINE` | La classification des comptes temporaires est policy-driven |
| `ADR-CLOSE-018` | `ACCEPTED_BASELINE` | Les closing controls ont une sévérité et un caractère bloquant configurables |
| `ADR-CLOSE-019` | `ACCEPTED_BASELINE` | `CLOSED` interdit le posting normal |
| `ADR-CLOSE-020` | `ACCEPTED_BASELINE` | La réouverture est explicite, auditée et non destructive |
| `ADR-CLOSE-021` | `ACCEPTED_BASELINE` | Une réouverture crée une nouvelle close revision |
| `ADR-CLOSE-022` | `ACCEPTED_BASELINE` | Les snapshots historiques ne sont jamais supprimés par reopen |
| `ADR-CLOSE-023` | `ACCEPTED_BASELINE` | Les à-nouveaux dérivent d'une source post-closing validée |
| `ADR-CLOSE-024` | `ACCEPTED_BASELINE` | Les à-nouveaux postés sont corrigés par reversal, jamais par mutation |
| `ADR-CLOSE-025` | `ACCEPTED_BASELINE` | PolicySet et ReferenceSnapshot sont figés pour un ClosingRun |
| `ADR-CLOSE-026` | `ACCEPTED_BASELINE` | Les stages de closing sont checkpointables |
| `ADR-CLOSE-027` | `ACCEPTED_BASELINE` | Closing est multi-entity scoped |
| `ADR-CLOSE-028` | `ACCEPTED_BASELINE` | Consolidation close est distinct du statutory close |
| `ADR-CLOSE-029` | `ACCEPTED_BASELINE` | Le process peut inclure des `PROCESS_REQUIREMENT` distincts des règles comptables |
| `ADR-CLOSE-030` | `ACCEPTED_BASELINE` | Toute correction d'un ajustement déjà posté suit reversal + replacement |

## 13.9 `CTRL` - Controls

**Phase** : `P0.10`  
**Source** : `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`  
**Nombre d'ADR** : 10

| ADR | Statut | Décision |
|---|---|---|
| `ADR-CTRL-001` | `ACCEPTED_BASELINE` | `CONTROL` reste distinct de `UNIVERSAL_ACCOUNTING_INVARIANT` |
| `ADR-CTRL-002` | `ACCEPTED_BASELINE` | `ControlDefinition` est versionnée |
| `ADR-CTRL-003` | `ACCEPTED_BASELINE` | Severity et Blocking sont deux dimensions distinctes |
| `ADR-CTRL-004` | `ACCEPTED_BASELINE` | `ControlRun` est un Aggregate Root |
| `ADR-CTRL-005` | `ACCEPTED_BASELINE` | Un `ControlResult` finalisé est immutable |
| `ADR-CTRL-006` | `ACCEPTED_BASELINE` | Une réévaluation crée un nouveau `ControlRun` |
| `ADR-CTRL-007` | `ACCEPTED_BASELINE` | `INDETERMINATE` est un statut explicite |
| `ADR-CTRL-008` | `ACCEPTED_BASELINE` | Un gate décide du workflow à partir des controls |
| `ADR-CTRL-009` | `ACCEPTED_BASELINE` | Un override de control ne peut pas contourner un invariant universel |
| `ADR-CTRL-010` | `ACCEPTED_BASELINE` | Les FEC controls restent adapter-specific |

## 13.10 `AUD` - Audit

**Phase** : `P0.10`  
**Source** : `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`  
**Nombre d'ADR** : 6

| ADR | Statut | Décision |
|---|---|---|
| `ADR-AUD-001` | `ACCEPTED_BASELINE` | `AuditEvent` est append-only |
| `ADR-AUD-002` | `ACCEPTED_BASELINE` | DomainEvent, AuditEvent et log technique sont distincts |
| `ADR-AUD-003` | `ACCEPTED_BASELINE` | Les mutations critiques doivent produire un audit durable |
| `ADR-AUD-004` | `ACCEPTED_BASELINE` | L'audit conserve ActorContext et TraceContext |
| `ADR-AUD-005` | `ACCEPTED_BASELINE` | Before/After doit respecter la minimisation des données |
| `ADR-AUD-006` | `ACCEPTED_BASELINE` | Le port Audit métier n'expose ni update ni delete |

## 13.11 `TRACE` - Traceability, Provenance & Reproducibility

**Phase** : `P0.10`  
**Source** : `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`  
**Nombre d'ADR** : 16

| ADR | Statut | Décision |
|---|---|---|
| `ADR-TRACE-001` | `ACCEPTED_BASELINE` | Provenance, Audit, Lineage et Reproducibility sont quatre concepts distincts |
| `ADR-TRACE-002` | `ACCEPTED_BASELINE` | Les source refs sont conservées jusqu'au niveau JournalLine lorsqu'un adapter le permet |
| `ADR-TRACE-003` | `ACCEPTED_BASELINE` | Les reference snapshots sont pinés pour les calculs réglementaires |
| `ADR-TRACE-004` | `ACCEPTED_BASELINE` | Les policy versions sont pinées pour les calculs métier |
| `ADR-TRACE-005` | `ACCEPTED_BASELINE` | SHA-256 est le checksum initial recommandé |
| `ADR-TRACE-006` | `ACCEPTED_BASELINE` | Un checksum ne constitue pas une validation sémantique |
| `ADR-TRACE-007` | `ACCEPTED_BASELINE` | Le canonicalization schema des hashes est versionné |
| `ADR-TRACE-008` | `ACCEPTED_BASELINE` | Les outputs publiables peuvent porter un `ReproducibilityEnvelope` |
| `ADR-TRACE-009` | `ACCEPTED_BASELINE` | Les external observations sont capturées lorsque FULL_REPLAY est requis |
| `ADR-TRACE-010` | `ACCEPTED_BASELINE` | P0 ne nécessite pas de graph database |
| `ADR-TRACE-011` | `ACCEPTED_BASELINE` | Les evidence artifacts immutables sont adressés par refs/version/checksum |
| `ADR-TRACE-012` | `ACCEPTED_BASELINE` | Les snapshots historiques restent immutables |
| `ADR-TRACE-013` | `ACCEPTED_BASELINE` | Les golden datasets CFA FRA servent d'oracle de non-régression |
| `ADR-TRACE-014` | `ACCEPTED_BASELINE` | Les ouvrages doctrinaux ne deviennent pas des sources réglementaires runtime |
| `ADR-TRACE-015` | `ACCEPTED_BASELINE` | L'audit est multi-entity scoped |
| `ADR-TRACE-016` | `ACCEPTED_BASELINE` | Le hash chaining est un hardening P1, pas un prérequis P0 |

## 13.12 `PERS` - Persistence, Concurrency & Adapters

**Phase** : `P0.11`  
**Source** : `10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-PERS-001` | `ACCEPTED_BASELINE` | Le domaine ne dépend d'aucun ORM |
| `ADR-PERS-002` | `ACCEPTED_BASELINE` | Les repositories sont des ports hexagonaux |
| `ADR-PERS-003` | `ACCEPTED_BASELINE` | Les repositories write-side persistent des aggregates, pas des reporting queries |
| `ADR-PERS-004` | `ACCEPTED_BASELINE` | Les queries complexes utilisent des query ports dédiés |
| `ADR-PERS-005` | `ACCEPTED_BASELINE` | `UnitOfWork` constitue la frontière de transaction applicative |
| `ADR-PERS-006` | `ACCEPTED_BASELINE` | Les repositories ne commitent jamais individuellement |
| `ADR-PERS-007` | `ACCEPTED_BASELINE` | Les transactions longues sont remplacées par des workflows durables multi-étapes |
| `ADR-PERS-008` | `ACCEPTED_BASELINE` | Posting et reversal sont atomiques |
| `ADR-PERS-009` | `ACCEPTED_BASELINE` | Le close final est une transaction courte et atomique |
| `ADR-PERS-010` | `ACCEPTED_BASELINE` | Optimistic locking utilise une `revision` explicite |
| `ADR-PERS-011` | `ACCEPTED_BASELINE` | Pessimistic locking est une capability d'adapter |
| `ADR-PERS-012` | `ACCEPTED_BASELINE` | Posting et Close doivent se sérialiser sur la période |
| `ADR-PERS-013` | `ACCEPTED_BASELINE` | La base de données reste la dernière ligne de défense pour l'unicité |
| `ADR-PERS-014` | `ACCEPTED_BASELINE` | L'idempotence utilise key + payload fingerprint |
| `ADR-PERS-015` | `ACCEPTED_BASELINE` | Same idempotency key + different payload = conflict |
| `ADR-PERS-016` | `ACCEPTED_BASELINE` | Les événements externes utilisent une Transactional Outbox |
| `ADR-PERS-017` | `ACCEPTED_BASELINE` | P0 ne requiert pas de distributed transaction manager |
| `ADR-PERS-018` | `ACCEPTED_BASELINE` | Audit critique et mutation métier doivent être transactionnellement coordonnés |
| `ADR-PERS-019` | `ACCEPTED_BASELINE` | `AuditEvent` persistence est append-only |
| `ADR-PERS-020` | `ACCEPTED_BASELINE` | Les montants comptables sont persistés en DECIMAL/NUMERIC, jamais FLOAT |
| `ADR-PERS-021` | `ACCEPTED_BASELINE` | Les timestamps techniques sont timezone-aware |
| `ADR-PERS-022` | `ACCEPTED_BASELINE` | ORM models et domain models restent distincts |
| `ADR-PERS-023` | `ACCEPTED_BASELINE` | Django model signals ne portent pas la logique comptable centrale |
| `ADR-PERS-024` | `ACCEPTED_BASELINE` | `Model.save()` ne porte pas Posting/Reversal |
| `ADR-PERS-025` | `ACCEPTED_BASELINE` | Django adapter encapsule `transaction.atomic` et `select_for_update` |
| `ADR-PERS-026` | `ACCEPTED_BASELINE` | SQLAlchemy adapter encapsule `Session` et `with_for_update` |
| `ADR-PERS-027` | `ACCEPTED_BASELINE` | InMemory adapter doit simuler rollback et revision conflicts |
| `ADR-PERS-028` | `ACCEPTED_BASELINE` | Les vraies races sont testées contre une DB transactionnelle réelle |
| `ADR-PERS-029` | `ACCEPTED_BASELINE` | PostgreSQL est la DB de qualification de référence des adapters SQL P0 |
| `ADR-PERS-030` | `ACCEPTED_BASELINE` | SQLite seul ne suffit pas pour certifier un adapter production |
| `ADR-PERS-031` | `ACCEPTED_BASELINE` | Tous les adapters partagent une contract test suite |
| `ADR-PERS-032` | `ACCEPTED_BASELINE` | Un adapter Production doit passer les suites de concurrence et rollback |
| `ADR-PERS-033` | `ACCEPTED_BASELINE` | Les exceptions ORM/DB sont traduites vers des erreurs PyAccountingKit stables |
| `ADR-PERS-034` | `ACCEPTED_BASELINE` | Les locks sont acquis dans un ordre déterministe lorsqu'il y en a plusieurs |
| `ADR-PERS-035` | `ACCEPTED_BASELINE` | La numérotation n'est pas implémentée par `MAX()+1` non verrouillé |
| `ADR-PERS-036` | `ACCEPTED_BASELINE` | Gapless numbering n'est pas promis sans policy explicite |
| `ADR-PERS-037` | `ACCEPTED_BASELINE` | Les read models peuvent être eventually consistent si le contract l'annonce |
| `ADR-PERS-038` | `ACCEPTED_BASELINE` | Les projections publiées doivent pouvoir être snapshotées / watermarked |
| `ADR-PERS-039` | `ACCEPTED_BASELINE` | Les adapters sont configurés via un composition root |
| `ADR-PERS-040` | `ACCEPTED_BASELINE` | Les dépendances Django/SQLAlchemy restent optionnelles au core |

## 13.13 `TEST` - Testing & Quality

**Phase** : `P0.12`  
**Source** : `11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`  
**Nombre d'ADR** : 30

| ADR | Statut | Décision |
|---|---|---|
| `ADR-TEST-001` | `ACCEPTED_BASELINE` | Les invariants critiques sont couverts par unit + property + integration |
| `ADR-TEST-002` | `ACCEPTED_BASELINE` | Hypothesis est recommandé pour les property-based tests |
| `ADR-TEST-003` | `ACCEPTED_BASELINE` | Les adapters partagent une contract suite commune |
| `ADR-TEST-004` | `ACCEPTED_BASELINE` | Les races critiques sont testées contre PostgreSQL réel |
| `ADR-TEST-005` | `ACCEPTED_BASELINE` | SQLite seul ne qualifie pas un adapter Production |
| `ADR-TEST-006` | `ACCEPTED_BASELINE` | CFA FRA est un golden oracle, pas une dépendance runtime |
| `ADR-TEST-007` | `ACCEPTED_BASELINE` | Les golden fixtures sont versionnées et immutables |
| `ADR-TEST-008` | `ACCEPTED_BASELINE` | Toute modification golden nécessite une revue explicite |
| `ADR-TEST-009` | `ACCEPTED_BASELINE` | Les tests réglementaires pinent standard/edition/dataset |
| `ADR-TEST-010` | `ACCEPTED_BASELINE` | Les policy tests pinent leur version |
| `ADR-TEST-011` | `ACCEPTED_BASELINE` | Les replay tests pinent runtime/reference/policy/source snapshots |
| `ADR-TEST-012` | `ACCEPTED_BASELINE` | Les migrations exécutent des controls post-migration |
| `ADR-TEST-013` | `ACCEPTED_BASELINE` | Coverage n'est pas une preuve suffisante |
| `ADR-TEST-014` | `ACCEPTED_BASELINE` | La cible de couverture du domain est >= 95 % |
| `ADR-TEST-015` | `ACCEPTED_BASELINE` | Tout bug comptable critique corrigé ajoute un regression test |
| `ADR-TEST-016` | `ACCEPTED_BASELINE` | Les exemples publics sont testés |
| `ADR-TEST-017` | `ACCEPTED_BASELINE` | Les dépendances optionnelles sont testées séparément |
| `ADR-TEST-018` | `ACCEPTED_BASELINE` | Les RC exécutent la full concurrency suite |
| `ADR-TEST-019` | `ACCEPTED_BASELINE` | Un adapter Production doit passer rollback + concurrency + migration |
| `ADR-TEST-020` | `ACCEPTED_BASELINE` | Les flakes critiques sont interdits en stable |
| `ADR-TEST-021` | `ACCEPTED_BASELINE` | Les tests temporels utilisent un Clock injecté |
| `ADR-TEST-022` | `ACCEPTED_BASELINE` | Decimal est obligatoire dans les tests monétaires |
| `ADR-TEST-023` | `ACCEPTED_BASELINE` | Les ouvrages doctrinaux ne remplacent pas la réglementation courante |
| `ADR-TEST-024` | `ACCEPTED_BASELINE` | Chaque release génère un qualification manifest |
| `ADR-TEST-025` | `ACCEPTED_BASELINE` | Toute divergence de golden output doit être expliquée |
| `ADR-TEST-026` | `ACCEPTED_BASELINE` | Les query semantics doivent être identiques entre adapters |
| `ADR-TEST-027` | `ACCEPTED_BASELINE` | La fault injection fait partie de la qualification Production |
| `ADR-TEST-028` | `ACCEPTED_BASELINE` | L'API publique est surveillée par manifest à partir de RC |
| `ADR-TEST-029` | `ACCEPTED_BASELINE` | Les snapshots historiques ne sont pas recalculés silencieusement en migration |
| `ADR-TEST-030` | `ACCEPTED_BASELINE` | La stratégie de tests fait partie du contrat produit de PyAccountingKit |

## 13.14 `IMP` - Accounting Imports & FEC

**Phase** : `P1.1`  
**Source** : `12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-IMP-001` | `ACCEPTED_BASELINE` | Le FEC est un adapter spécialisé, pas le modèle universel d'import |
| `ADR-IMP-002` | `ACCEPTED_BASELINE` | `AccountingImportBatch` est l'Aggregate Root du processus d'import |
| `ADR-IMP-003` | `ACCEPTED_BASELINE` | L'artefact source est conservé avec checksum |
| `ADR-IMP-004` | `ACCEPTED_BASELINE` | Les raw records sont conservés lorsque la capability/policy l'exige |
| `ADR-IMP-005` | `ACCEPTED_BASELINE` | Parsing, normalization, mapping et posting sont des étapes distinctes |
| `ADR-IMP-006` | `ACCEPTED_BASELINE` | Les normalized records utilisent le vocabulaire générique PyAccountingKit |
| `ADR-IMP-007` | `ACCEPTED_BASELINE` | Les codes sources restent des strings |
| `ADR-IMP-008` | `ACCEPTED_BASELINE` | Les montants normalisés utilisent Decimal |
| `ADR-IMP-009` | `ACCEPTED_BASELINE` | Les lignes sont regroupées par `SourceEntryKey` déterministe |
| `ADR-IMP-010` | `ACCEPTED_BASELINE` | Source account mapping et RegulatoryAccountBinding sont distincts |
| `ADR-IMP-011` | `ACCEPTED_BASELINE` | Une candidate mapping n'est pas exécutable sans validation |
| `ADR-IMP-012` | `ACCEPTED_BASELINE` | Les journaux sources sont mappés explicitement |
| `ADR-IMP-013` | `ACCEPTED_BASELINE` | Import ne crée pas silencieusement comptes ou journaux inconnus |
| `ADR-IMP-014` | `ACCEPTED_BASELINE` | `ImportPlan` est construit avant mutation comptable |
| `ADR-IMP-015` | `ACCEPTED_BASELINE` | Dry-run ne mute jamais le core |
| `ADR-IMP-016` | `ACCEPTED_BASELINE` | L'exécution revalide les états critiques |
| `ADR-IMP-017` | `ACCEPTED_BASELINE` | Le mode normal suit Create -> Validate -> Post |
| `ADR-IMP-018` | `ACCEPTED_BASELINE` | `TRUSTED_POSTED_HISTORY_IMPORT` est une exception explicite |
| `ADR-IMP-019` | `ACCEPTED_BASELINE` | Trusted history ne contourne pas la partie double |
| `ADR-IMP-020` | `ACCEPTED_BASELINE` | L'idempotence existe au niveau batch et entry |
| `ADR-IMP-021` | `ACCEPTED_BASELINE` | Duplicate heuristic != duplicate confirmed |
| `ADR-IMP-022` | `ACCEPTED_BASELINE` | Les imports postés ne sont jamais annulés par DELETE |
| `ADR-IMP-023` | `ACCEPTED_BASELINE` | Un undo métier utilise reversal |
| `ADR-IMP-024` | `ACCEPTED_BASELINE` | Les source refs sont préservées jusqu'à JournalEntryLine |
| `ADR-IMP-025` | `ACCEPTED_BASELINE` | Reprocessing crée un nouveau run, jamais une mutation de l'ancien |
| `ADR-IMP-026` | `ACCEPTED_BASELINE` | Mapping snapshot et adapter version sont pinés |
| `ADR-IMP-027` | `ACCEPTED_BASELINE` | FEC field names restent dans `adapters/imports/fec` |
| `ADR-IMP-028` | `ACCEPTED_BASELINE` | `CompAuxNum` n'est jamais concaténé automatiquement au compte général dans le core |
| `ADR-IMP-029` | `ACCEPTED_BASELINE` | FEC duplicate candidates sont warnings par défaut lorsqu'heuristiques |
| `ADR-IMP-030` | `ACCEPTED_BASELINE` | `FEC_*` controls restent adapter-specific |
| `ADR-IMP-031` | `ACCEPTED_BASELINE` | ALL_OR_NOTHING est la référence pour migrations FEC raisonnables |
| `ADR-IMP-032` | `ACCEPTED_BASELINE` | CHUNKED_ATOMIC doit exposer ses semantics de reprise |
| `ADR-IMP-033` | `ACCEPTED_BASELINE` | Aucun record source ne peut être silently dropped |
| `ADR-IMP-034` | `ACCEPTED_BASELINE` | Toute correction/coercion explicite produit une trace |
| `ADR-IMP-035` | `ACCEPTED_BASELINE` | Stale ImportPlan ne peut pas être exécuté |
| `ADR-IMP-036` | `ACCEPTED_BASELINE` | Import et period close partagent les mêmes garanties de concurrence |
| `ADR-IMP-037` | `ACCEPTED_BASELINE` | Le plan d'import final peut être approuvé par checksum |
| `ADR-IMP-038` | `ACCEPTED_BASELINE` | Les post-import controls participent à la finalisation |
| `ADR-IMP-039` | `ACCEPTED_BASELINE` | Le FEC n'est jamais mappé directement vers les états financiers |
| `ADR-IMP-040` | `ACCEPTED_BASELINE` | Un adapter Production passe contract, golden, rollback et concurrency suites |

## 13.15 `REP` - Financial Statements & Regulatory Reporting

**Phase** : `P1.2`  
**Source** : `13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-REP-001` | `ACCEPTED_BASELINE` | Les états financiers sont des projections, pas une source comptable |
| `ADR-REP-002` | `ACCEPTED_BASELINE` | `TrialBalanceSnapshot` est la source recommandée pour publication |
| `ADR-REP-003` | `ACCEPTED_BASELINE` | `FinancialStatementDefinition` est versionnée |
| `ADR-REP-004` | `ACCEPTED_BASELINE` | La hiérarchie des lignes est explicite |
| `ADR-REP-005` | `ACCEPTED_BASELINE` | Les formules utilisent une DSL limitée et déterministe |
| `ADR-REP-006` | `ACCEPTED_BASELINE` | `StatementAccountMapping` est distinct du `RegulatoryAccountBinding` |
| `ADR-REP-007` | `ACCEPTED_BASELINE` | `StatementMappingSet` est versionné |
| `ADR-REP-008` | `ACCEPTED_BASELINE` | Les candidate account hints réglementaires ne sont pas exécutables par défaut |
| `ADR-REP-009` | `ACCEPTED_BASELINE` | Les human-review flags du provider sont respectés |
| `ADR-REP-010` | `ACCEPTED_BASELINE` | Aucune taxonomy réglementaire n'est hardcodée dans le core |
| `ADR-REP-011` | `ACCEPTED_BASELINE` | Le provider peut fournir la structure sans mapping exécutable |
| `ADR-REP-012` | `ACCEPTED_BASELINE` | Les mappings ambiguës échouent en fail-closed |
| `ADR-REP-013` | `ACCEPTED_BASELINE` | Les mappings one-to-many exigent une allocation explicite |
| `ADR-REP-014` | `ACCEPTED_BASELINE` | Le calcul utilise Decimal avant tout rounding de présentation |
| `ADR-REP-015` | `ACCEPTED_BASELINE` | `ReportSnapshot` publié est immutable |
| `ADR-REP-016` | `ACCEPTED_BASELINE` | Un reopen ne modifie ni ne supprime un snapshot publié |
| `ADR-REP-017` | `ACCEPTED_BASELINE` | Les snapshots sont reproductibles par versions/sources pinées |
| `ADR-REP-018` | `ACCEPTED_BASELINE` | Balance Sheet / Income Statement / Cash Flow sont des StatementDefinitions spécialisées |
| `ADR-REP-019` | `ACCEPTED_BASELINE` | `CASHFLOW_RECONCILED` reste un control, pas une mutation |
| `ADR-REP-020` | `ACCEPTED_BASELINE` | La définition exacte d'un TrialBalance variant source est policy-driven |
| `ADR-REP-021` | `ACCEPTED_BASELINE` | Le reporting réglementaire utilise un `RegulatoryReportingProfile` versionné |
| `ADR-REP-022` | `ACCEPTED_BASELINE` | Un nouveau ReferenceSnapshot ne modifie jamais un profil actif silencieusement |
| `ADR-REP-023` | `ACCEPTED_BASELINE` | Les upgrades réglementaires passent par impact analysis + nouvelle version |
| `ADR-REP-024` | `ACCEPTED_BASELINE` | Les exports réglementaires sont dérivés d'un ReportSnapshot |
| `ADR-REP-025` | `ACCEPTED_BASELINE` | Tout export réglementaire final possède un checksum |
| `ADR-REP-026` | `ACCEPTED_BASELINE` | `ReportRenderer` et `RegulatoryExporter` sont distincts |
| `ADR-REP-027` | `ACCEPTED_BASELINE` | Le reporting est read-only vis-à-vis du Journal/Ledger |
| `ADR-REP-028` | `ACCEPTED_BASELINE` | Les reporting adjustments éventuels ne modifient pas le ledger statutaire |
| `ADR-REP-029` | `ACCEPTED_BASELINE` | Le drill-down StatementLine -> TrialBalance -> Ledger -> Entry est requis |
| `ADR-REP-030` | `ACCEPTED_BASELINE` | Les comparatifs pinent leurs propres mapping/definition versions |
| `ADR-REP-031` | `ACCEPTED_BASELINE` | Les line-code equalities ne prouvent pas l'équivalence sémantique |
| `ADR-REP-032` | `ACCEPTED_BASELINE` | Les report snapshots conservent les control run refs |
| `ADR-REP-033` | `ACCEPTED_BASELINE` | Le moteur distingue semantic result et rendered view |
| `ADR-REP-034` | `ACCEPTED_BASELINE` | Les labels ne sont jamais utilisés comme clés logiques |
| `ADR-REP-035` | `ACCEPTED_BASELINE` | La publication réglementaire échoue si un required mapping est non résolu |
| `ADR-REP-036` | `ACCEPTED_BASELINE` | Les source/reporting capabilities manquantes sont exposées explicitement |
| `ADR-REP-037` | `ACCEPTED_BASELINE` | Les management statements réutilisent le même engine sans autorité réglementaire implicite |
| `ADR-REP-038` | `ACCEPTED_BASELINE` | Financial Analysis consomme les snapshots et reste downstream |
| `ADR-REP-039` | `ACCEPTED_BASELINE` | Consolidation reste un bounded context futur distinct |
| `ADR-REP-040` | `ACCEPTED_BASELINE` | Les datasets doctrinaux ne remplacent jamais le reporting réglementaire versionné |

## 13.16 `ANA` - Financial Analysis & Indicators

**Phase** : `P1.3`  
**Source** : `14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-ANA-001` | `ACCEPTED_BASELINE` | `Financial Analysis` est un bounded context read-only |
| `ADR-ANA-002` | `ACCEPTED_BASELINE` | Le bounded context consomme `ReportSnapshot` et `TrialBalanceSnapshot` |
| `ADR-ANA-003` | `ACCEPTED_BASELINE` | Les indicateurs analytiques ne deviennent jamais source comptable |
| `ADR-ANA-004` | `ACCEPTED_BASELINE` | `FinancialIndicatorDefinition` est versionnée |
| `ADR-ANA-005` | `ACCEPTED_BASELINE` | `FinancialRatioDefinition` est versionnée |
| `ADR-ANA-006` | `ACCEPTED_BASELINE` | `FinancialScoreDefinition` est versionnée |
| `ADR-ANA-007` | `ACCEPTED_BASELINE` | Les formules utilisent une DSL déterministe et sûre |
| `ADR-ANA-008` | `ACCEPTED_BASELINE` | Les dépendances d'indicateurs forment un DAG |
| `ADR-ANA-009` | `ACCEPTED_BASELINE` | Une division par zéro produit `UNDEFINED` par défaut |
| `ADR-ANA-010` | `ACCEPTED_BASELINE` | Une donnée requise manquante produit `INDETERMINATE` |
| `ADR-ANA-011` | `ACCEPTED_BASELINE` | Les SIG sont definition-driven |
| `ADR-ANA-012` | `ACCEPTED_BASELINE` | EBE et EBITDA ne sont pas fusionnés comme concepts universellement équivalents |
| `ADR-ANA-013` | `ACCEPTED_BASELINE` | La CAF peut supporter plusieurs méthodes versionnées |
| `ADR-ANA-014` | `ACCEPTED_BASELINE` | Le bilan fonctionnel est une définition analytique, pas un état comptable canonique |
| `ADR-ANA-015` | `ACCEPTED_BASELINE` | FRNG, BFR et trésorerie nette sont des indicateurs analytiques |
| `ADR-ANA-016` | `ACCEPTED_BASELINE` | Les ratios CFA FRA sont analytiques, pas réglementaires |
| `ADR-ANA-017` | `ACCEPTED_BASELINE` | Les seuils d'interprétation sont policy-driven |
| `ADR-ANA-018` | `ACCEPTED_BASELINE` | Un score n'est pas livré Production sans définition validée |
| `ADR-ANA-019` | `ACCEPTED_BASELINE` | `Control` et `Diagnostic` sont distincts |
| `ADR-ANA-020` | `ACCEPTED_BASELINE` | `AnalysisDefinitionSet` fige une méthodologie analytique complète |
| `ADR-ANA-021` | `ACCEPTED_BASELINE` | `AnalysisSnapshot` publié est immutable |
| `ADR-ANA-022` | `ACCEPTED_BASELINE` | Un AnalysisSnapshot pinne ses sources et définitions |
| `ADR-ANA-023` | `ACCEPTED_BASELINE` | Un reopen n'altère jamais un AnalysisSnapshot historique |
| `ADR-ANA-024` | `ACCEPTED_BASELINE` | Le drill-down Metric -> Statement -> TrialBalance -> Ledger est requis |
| `ADR-ANA-025` | `ACCEPTED_BASELINE` | Toute valeur publiée doit disposer d'un CalculationTrace ou équivalent |
| `ADR-ANA-026` | `ACCEPTED_BASELINE` | Les benchmarks utilisés en publication sont snapshotés |
| `ADR-ANA-027` | `ACCEPTED_BASELINE` | Une approximation analytique doit être explicitement configurée et tracée |
| `ADR-ANA-028` | `ACCEPTED_BASELINE` | Les concept bindings non validés ne sont pas inventés |
| `ADR-ANA-029` | `ACCEPTED_BASELINE` | Les mappings analytiques ne reposent pas sur des préfixes universels |
| `ADR-ANA-030` | `ACCEPTED_BASELINE` | Les tendances pinent chaque source historique |
| `ADR-ANA-031` | `ACCEPTED_BASELINE` | Same metric code ne prouve pas l'équivalence sémantique entre versions |
| `ADR-ANA-032` | `ACCEPTED_BASELINE` | Les changements sémantiques breaking créent une nouvelle version |
| `ADR-ANA-033` | `ACCEPTED_BASELINE` | Le Corporate Finance reste hors du core P1.3 |
| `ADR-ANA-034` | `ACCEPTED_BASELINE` | VAN/NPV, TRI/IRR, WACC et valuation sont hors du bounded context |
| `ADR-ANA-035` | `ACCEPTED_BASELINE` | Les analyses historiques, ratios, SIG, BFR et diagnostics restent dans le core |
| `ADR-ANA-036` | `ACCEPTED_BASELINE` | Les narrations IA éventuelles ne peuvent pas modifier les résultats numériques |
| `ADR-ANA-037` | `ACCEPTED_BASELINE` | Les définitions doctrinales n'ont aucune autorité réglementaire implicite |
| `ADR-ANA-038` | `ACCEPTED_BASELINE` | Les définitions Production doivent être qualifiées par golden/replay tests |
| `ADR-ANA-039` | `ACCEPTED_BASELINE` | Les AnalysisSnapshot published sont append-oriented |
| `ADR-ANA-040` | `ACCEPTED_BASELINE` | Le moteur analytique utilise Decimal de bout en bout |

## 13.17 `SUB` - Subledgers & Operational Accounting

**Phase** : `P1.4`  
**Source** : `15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md`  
**Nombre d'ADR** : 32

| ADR | Statut | Décision |
|---|---|---|
| `ADR-SUB-001` | `ACCEPTED_BASELINE` | Les sous-livres restent distincts du General Ledger |
| `ADR-SUB-002` | `ACCEPTED_BASELINE` | `BusinessPartner` est distinct de `CompanyAccount` |
| `ADR-SUB-003` | `ACCEPTED_BASELINE` | Les modes auxiliaires sont `SUBLEDGER`, `EXTENDED_ACCOUNT_CODE`, `HYBRID` |
| `ADR-SUB-004` | `ACCEPTED_BASELINE` | `CompAuxNum` n'est jamais concaténé implicitement à `CompteNum` |
| `ADR-SUB-005` | `ACCEPTED_BASELINE` | `OperationalDocument` et `AccountingEvent` sont distincts de `JournalEntry` |
| `ADR-SUB-006` | `ACCEPTED_BASELINE` | Toute comptabilisation opérationnelle passe par le Posting Engine normal |
| `ADR-SUB-007` | `ACCEPTED_BASELINE` | Les comptes collectifs sont résolus par binding/policy |
| `ADR-SUB-008` | `ACCEPTED_BASELINE` | Receivables/Payables portent des `DueItem` |
| `ADR-SUB-009` | `ACCEPTED_BASELINE` | Settlement et Allocation sont distincts |
| `ADR-SUB-010` | `ACCEPTED_BASELINE` | Allocation n'implique pas un nouveau posting GL |
| `ADR-SUB-011` | `ACCEPTED_BASELINE` | Settlement, Matching et Reconciliation sont trois concepts distincts |
| `ADR-SUB-012` | `ACCEPTED_BASELINE` | Les surpaiements sont traités explicitement |
| `ADR-SUB-013` | `ACCEPTED_BASELINE` | Aucune allocation ne dépasse le montant ouvert |
| `ADR-SUB-014` | `ACCEPTED_BASELINE` | Les races d'allocation sont transactionnellement protégées |
| `ADR-SUB-015` | `ACCEPTED_BASELINE` | Le lettrage complet et partiel sont supportés |
| `ADR-SUB-016` | `ACCEPTED_BASELINE` | Un write-off est explicite et audité |
| `ADR-SUB-017` | `ACCEPTED_BASELINE` | `SUBLEDGER_GL_RECONCILED` est un control |
| `ADR-SUB-018` | `ACCEPTED_BASELINE` | Les codes nationaux de comptes collectifs ne sont jamais hardcodés |
| `ADR-SUB-019` | `ACCEPTED_BASELINE` | L'aging ne définit aucune dépréciation universelle |
| `ADR-SUB-020` | `ACCEPTED_BASELINE` | Les historiques importés conservent un niveau de complétude explicite |
| `ADR-SUB-021` | `ACCEPTED_BASELINE` | Le lettrage FEC importé peut nécessiter revalidation |
| `ADR-SUB-022` | `ACCEPTED_BASELINE` | Les événements opérationnels sont idempotents |
| `ADR-SUB-023` | `ACCEPTED_BASELINE` | Une annulation postée produit reversal/credit note, jamais delete |
| `ADR-SUB-024` | `ACCEPTED_BASELINE` | Le settlement reversal restaure aussi les allocations |
| `ADR-SUB-025` | `ACCEPTED_BASELINE` | Les FX historiques utilisent des rates snapshotés |
| `ADR-SUB-026` | `ACCEPTED_BASELINE` | Les résiduels ne sont jamais absorbés silencieusement |
| `ADR-SUB-027` | `ACCEPTED_BASELINE` | Les adapters métier normalisent vers des primitives génériques |
| `ADR-SUB-028` | `ACCEPTED_BASELINE` | PyAccountingKit n'est pas le master CRM/fournisseur |
| `ADR-SUB-029` | `ACCEPTED_BASELINE` | Les PSP restent hors du core comptable |
| `ADR-SUB-030` | `ACCEPTED_BASELINE` | Les snapshots de sous-livre publiés sont immuables |
| `ADR-SUB-031` | `ACCEPTED_BASELINE` | DSO/DPO appartiennent à Financial Analysis |
| `ADR-SUB-032` | `ACCEPTED_BASELINE` | Le futur bounded context Reconciliation généralisera ces rapprochements |

## 13.18 `API` - Public API

**Phase** : `P1.5`  
**Source** : `16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-API-001` | `ACCEPTED_BASELINE` | `AccountingApplication` est la façade publique principale |
| `ADR-API-002` | `ACCEPTED_BASELINE` | Les bounded contexts sont exposés via sous-façades |
| `ADR-API-003` | `ACCEPTED_BASELINE` | L'API publique n'expose ni ORM ni SQL |
| `ADR-API-004` | `ACCEPTED_BASELINE` | L'utilisateur ordinaire ne manipule pas directement `UnitOfWork` |
| `ADR-API-005` | `ACCEPTED_BASELINE` | Les mutations critiques passent par des commandes applicatives |
| `ADR-API-006` | `ACCEPTED_BASELINE` | Les queries retournent des objets framework-neutral |
| `ADR-API-007` | `ACCEPTED_BASELINE` | Les erreurs ORM sont traduites vers des erreurs publiques stables |
| `ADR-API-008` | `ACCEPTED_BASELINE` | Les codes d'erreur publics sont stables |
| `ADR-API-009` | `ACCEPTED_BASELINE` | `Money` rejette le float |
| `ADR-API-010` | `ACCEPTED_BASELINE` | Les DTOs publics sont immuables par défaut |
| `ADR-API-011` | `ACCEPTED_BASELINE` | Pydantic n'est pas une dépendance obligatoire du core |
| `ADR-API-012` | `ACCEPTED_BASELINE` | Les ports destinés aux adapter authors sont exposés séparément |
| `ADR-API-013` | `ACCEPTED_BASELINE` | L'API utilisateur et l'extension API ont des niveaux de stabilité distincts |
| `ADR-API-014` | `ACCEPTED_BASELINE` | Le sync API est la cible P1 |
| `ADR-API-015` | `ACCEPTED_BASELINE` | Une future API async sera distincte et non une mutation silencieuse du sync API |
| `ADR-API-016` | `ACCEPTED_BASELINE` | Les dépendances Django/SQLAlchemy restent optionnelles |
| `ADR-API-017` | `ACCEPTED_BASELINE` | Les convenience constructors ORM vivent dans les packages adapters |
| `ADR-API-018` | `ACCEPTED_BASELINE` | Les public methods sont typées et documentées |
| `ADR-API-019` | `ACCEPTED_BASELINE` | Les retours de commande sont des objets nommés, pas des booléens génériques |
| `ADR-API-020` | `ACCEPTED_BASELINE` | Les queries volumineuses supportent pagination/cursors |
| `ADR-API-021` | `ACCEPTED_BASELINE` | Les defaults ambiguës sont interdits |
| `ADR-API-022` | `ACCEPTED_BASELINE` | L'API publique ne choisit pas les stratégies de locking SQL |
| `ADR-API-023` | `ACCEPTED_BASELINE` | L'idempotence peut être fournie explicitement par command |
| `ADR-API-024` | `ACCEPTED_BASELINE` | `expected_revision` peut être exposé pour optimistic concurrency |
| `ADR-API-025` | `ACCEPTED_BASELINE` | La sérialisation publique et la sérialisation canonique de snapshot sont distinctes |
| `ADR-API-026` | `ACCEPTED_BASELINE` | Les schemas persistés/exportés sont versionnés |
| `ADR-API-027` | `ACCEPTED_BASELINE` | `PUBLIC_API_MANIFEST.json` est généré à partir de RC |
| `ADR-API-028` | `ACCEPTED_BASELINE` | Les breaking API changes suivent SemVer |
| `ADR-API-029` | `ACCEPTED_BASELINE` | Les exemples README utilisent exclusivement la public API |
| `ADR-API-030` | `ACCEPTED_BASELINE` | Le package racine ne réexporte qu'une surface explicitement choisie |
| `ADR-API-031` | `ACCEPTED_BASELINE` | `py.typed` est livré pour le typage utilisateur |
| `ADR-API-032` | `ACCEPTED_BASELINE` | Les registries de plugins sont instance-scoped |
| `ADR-API-033` | `ACCEPTED_BASELINE` | Les métadonnées ne remplacent pas les champs structurants |
| `ADR-API-034` | `ACCEPTED_BASELINE` | Les snapshots publics publiés restent immuables |
| `ADR-API-035` | `ACCEPTED_BASELINE` | Aucun framework web n'est requis pour utiliser PyAccountingKit |
| `ADR-API-036` | `ACCEPTED_BASELINE` | La public API est utilisable en CLI, notebook, web et workers |
| `ADR-API-037` | `ACCEPTED_BASELINE` | Les event schemas externes sont versionnés séparément si exposés |
| `ADR-API-038` | `ACCEPTED_BASELINE` | Les messages d'erreur textuels ne sont pas un contrat stable, les codes le sont |
| `ADR-API-039` | `ACCEPTED_BASELINE` | Les adapters ne dictent jamais la forme de la façade utilisateur |
| `ADR-API-040` | `ACCEPTED_BASELINE` | Le gel de l'API publique précède la release stable |

## 13.19 `REL` - Release & Versioning

**Phase** : `P1.6`  
**Source** : `17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-REL-001` | `ACCEPTED_BASELINE` | PyAccountingKit utilise Semantic Versioning |
| `ADR-REL-002` | `ACCEPTED_BASELINE` | Les pré-releases utilisent PEP 440 `a`, `b`, `rc` |
| `ADR-REL-003` | `ACCEPTED_BASELINE` | Framework version et standard edition sont découplés |
| `ADR-REL-004` | `ACCEPTED_BASELINE` | Regulatory dataset release est une dimension distincte |
| `ADR-REL-005` | `ACCEPTED_BASELINE` | Public API contract possède un manifest versionné |
| `ADR-REL-006` | `ACCEPTED_BASELINE` | Adapter contract possède sa propre version |
| `ADR-REL-007` | `ACCEPTED_BASELINE` | Persistence schema version reste propre à l'adapter |
| `ADR-REL-008` | `ACCEPTED_BASELINE` | Snapshot schema version est explicitement stockée |
| `ADR-REL-009` | `ACCEPTED_BASELINE` | Les reference snapshots actifs ne changent jamais silencieusement |
| `ADR-REL-010` | `ACCEPTED_BASELINE` | Une nouvelle policy version ne réécrit pas l'historique |
| `ADR-REL-011` | `ACCEPTED_BASELINE` | Une nouvelle StatementDefinition version ne réécrit pas les reports historiques |
| `ADR-REL-012` | `ACCEPTED_BASELINE` | Les import adapter versions sont pinées dans les batches |
| `ADR-REL-013` | `ACCEPTED_BASELINE` | Le gel de l'API publique intervient avant `1.0.0` |
| `ADR-REL-014` | `ACCEPTED_BASELINE` | Une RC est feature-frozen |
| `ADR-REL-015` | `ACCEPTED_BASELINE` | Aucun BLOCKER/CRITICAL n'est accepté en stable |
| `ADR-REL-016` | `ACCEPTED_BASELINE` | Les adapters Production sont qualifiés backend par backend |
| `ADR-REL-017` | `ACCEPTED_BASELINE` | SQLite ne qualifie pas une persistence Production |
| `ADR-REL-018` | `ACCEPTED_BASELINE` | Toute release stable publie une compatibility matrix |
| `ADR-REL-019` | `ACCEPTED_BASELINE` | Toute release stable publie un qualification manifest |
| `ADR-REL-020` | `ACCEPTED_BASELINE` | Toute release stable est taggée immuablement |
| `ADR-REL-021` | `ACCEPTED_BASELINE` | Une release PyPI n'est jamais remplacée ; elle est yanked si nécessaire |
| `ADR-REL-022` | `ACCEPTED_BASELINE` | Les corrections de code utilisent PATCH plutôt que `.postN` |
| `ADR-REL-023` | `ACCEPTED_BASELINE` | Les migrations sont testées depuis la stable précédente |
| `ADR-REL-024` | `ACCEPTED_BASELINE` | Les migrations destructives exigent une gouvernance renforcée |
| `ADR-REL-025` | `ACCEPTED_BASELINE` | Les published snapshots ne sont jamais migrés destructivement |
| `ADR-REL-026` | `ACCEPTED_BASELINE` | Les dépréciations stable précèdent toute suppression |
| `ADR-REL-027` | `ACCEPTED_BASELINE` | Les error codes publics suivent la même discipline que l'API |
| `ADR-REL-028` | `ACCEPTED_BASELINE` | Les golden fixture updates exigent une revue |
| `ADR-REL-029` | `ACCEPTED_BASELINE` | Les high-impact accounting fixes documentent l'impact historique |
| `ADR-REL-030` | `ACCEPTED_BASELINE` | Les dependency extras sont qualifiés séparément |
| `ADR-REL-031` | `ACCEPTED_BASELINE` | Le core install reste indépendant des ORMs optionnels |
| `ADR-REL-032` | `ACCEPTED_BASELINE` | `py.typed` fait partie de l'artefact stable si typing annoncé |
| `ADR-REL-033` | `ACCEPTED_BASELINE` | Les RC et stable construisent wheel + sdist |
| `ADR-REL-034` | `ACCEPTED_BASELINE` | Les artefacts publiés reçoivent des checksums SHA-256 |
| `ADR-REL-035` | `ACCEPTED_BASELINE` | La publication utilise un environnement de build propre |
| `ADR-REL-036` | `ACCEPTED_BASELINE` | Les changes réglementaires sont distingués des changes framework dans le changelog |
| `ADR-REL-037` | `ACCEPTED_BASELINE` | Les breaking behavioral semantics sont traitées comme breaking API après 1.0 |
| `ADR-REL-038` | `ACCEPTED_BASELINE` | Une correction réglementaire ne modifie pas silencieusement les snapshots historiques |
| `ADR-REL-039` | `ACCEPTED_BASELINE` | `1.0.0` stabilise le core, pas nécessairement tous les modules futurs |
| `ADR-REL-040` | `ACCEPTED_BASELINE` | Toute montée MAJOR dispose d'un migration guide |

## 13.20 `CFA` - CFA FRA Extraction & Migration

**Phase** : `P1.7`  
**Source** : `18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-CFA-001` | `ACCEPTED_BASELINE` | CFA FRA est une référence fonctionnelle, pas une dépendance runtime |
| `ADR-CFA-002` | `ACCEPTED_BASELINE` | Les comportements critiques CFA FRA deviennent golden fixtures |
| `ADR-CFA-003` | `ACCEPTED_BASELINE` | Les modèles Django ne sont pas copiés dans le domain |
| `ADR-CFA-004` | `ACCEPTED_BASELINE` | `Organization` est généralisé en `AccountingEntity` |
| `ADR-CFA-005` | `ACCEPTED_BASELINE` | `Account.framework_account` est remplacé par un binding explicite |
| `ADR-CFA-006` | `ACCEPTED_BASELINE` | Le workflow DRAFT -> VALIDATED -> POSTED -> REVERSED est conservé |
| `ADR-CFA-007` | `ACCEPTED_BASELINE` | Les invariants de validation CFA FRA sont extraits dans le domain |
| `ADR-CFA-008` | `ACCEPTED_BASELINE` | `transaction.atomic` reste un détail du Django adapter |
| `ADR-CFA-009` | `ACCEPTED_BASELINE` | `select_for_update` reste un détail du locking adapter |
| `ADR-CFA-010` | `ACCEPTED_BASELINE` | Le Reversal comportemental est conservé, la convention de numéro est policy-driven |
| `ADR-CFA-011` | `ACCEPTED_BASELINE` | `signed_balance = debit-credit` reste une convention de projection |
| `ADR-CFA-012` | `ACCEPTED_BASELINE` | Les variantes de Trial Balance CFA FRA sont conservées |
| `ADR-CFA-013` | `ACCEPTED_BASELINE` | `JOD -> ADJUSTING` n'est pas un invariant universel |
| `ADR-CFA-014` | `ACCEPTED_BASELINE` | Le pipeline FEC est généralisé en Accounting Imports |
| `ADR-CFA-015` | `ACCEPTED_BASELINE` | Les 18 colonnes FEC restent dans l'adapter FEC |
| `ADR-CFA-016` | `ACCEPTED_BASELINE` | Les raw FEC lines restent auditables et reprocessables |
| `ADR-CFA-017` | `ACCEPTED_BASELINE` | Le duplicate hash FEC reste un signal, pas une preuve économique |
| `ADR-CFA-018` | `ACCEPTED_BASELINE` | Le direct POSTED FEC est remplacé par `TRUSTED_POSTED_HISTORY_IMPORT` |
| `ADR-CFA-019` | `ACCEPTED_BASELINE` | Le rollback complet FEC est un comportement à préserver |
| `ADR-CFA-020` | `ACCEPTED_BASELINE` | Le Ledger SQL est réimplémenté derrière des query ports |
| `ADR-CFA-021` | `ACCEPTED_BASELINE` | Le Statement Engine CFA FRA est réécrit framework-neutral |
| `ADR-CFA-022` | `ACCEPTED_BASELINE` | Statement mapping et Regulatory binding restent séparés |
| `ADR-CFA-023` | `ACCEPTED_BASELINE` | Les diagnostics de mapping CFA FRA deviennent des controls/coverage metrics |
| `ADR-CFA-024` | `ACCEPTED_BASELINE` | Le drill-down financier est conservé de bout en bout |
| `ADR-CFA-025` | `ACCEPTED_BASELINE` | Les ratios Sprint 6 alimentent les golden Financial Analysis |
| `ADR-CFA-026` | `ACCEPTED_BASELINE` | Le reporting réglementaire reste distinct des états financiers génériques |
| `ADR-CFA-027` | `ACCEPTED_BASELINE` | Les controls CFA FRA deviennent des ControlDefinitions versionnées |
| `ADR-CFA-028` | `ACCEPTED_BASELINE` | L'AuditEvent est extrait mais les champs HTTP restent contextuels |
| `ADR-CFA-029` | `ACCEPTED_BASELINE` | Le workflow Closing CFA FRA est conservé et généralisé |
| `ADR-CFA-030` | `ACCEPTED_BASELINE` | Les référentiels locaux CFA FRA cessent d'être source de vérité |
| `ADR-CFA-031` | `ACCEPTED_BASELINE` | `regulatory-accounting-data-framework` devient la source réglementaire |
| `ADR-CFA-032` | `ACCEPTED_BASELINE` | HTMX/templates/forms restent dans CFA FRA consumer |
| `ADR-CFA-033` | `ACCEPTED_BASELINE` | RBAC reste une responsabilité de l'application consommatrice |
| `ADR-CFA-034` | `ACCEPTED_BASELINE` | PostgreSQL reste un backend de référence, pas une dépendance du domain |
| `ADR-CFA-035` | `ACCEPTED_BASELINE` | Celery/Redis restent optionnels |
| `ADR-CFA-036` | `ACCEPTED_BASELINE` | La migration suit un strangler pattern |
| `ADR-CFA-037` | `ACCEPTED_BASELINE` | Les mutations comptables ne sont jamais dual-written |
| `ADR-CFA-038` | `ACCEPTED_BASELINE` | Toute divergence intentionnelle est documentée |
| `ADR-CFA-039` | `ACCEPTED_BASELINE` | Les identités historiques restent traçables |
| `ADR-CFA-040` | `ACCEPTED_BASELINE` | La suppression du moteur legacy n'intervient qu'après parity qualification |

## 13.21 `RFM` - Regulatory Framework Integration

**Phase** : `P1.8`  
**Source** : `19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md`  
**Nombre d'ADR** : 40

| ADR | Statut | Décision |
|---|---|---|
| `ADR-RFM-001` | `ACCEPTED_BASELINE` | L'intégration réglementaire est capability-based, pas un booléen global |
| `ADR-RFM-002` | `ACCEPTED_BASELINE` | `regulatory-accounting-data-framework` reste la source réglementaire |
| `ADR-RFM-003` | `ACCEPTED_BASELINE` | Les IDs réglementaires externes sont préservés |
| `ADR-RFM-004` | `ACCEPTED_BASELINE` | Les hiérarchies explicites sont consommées sans reconstruction dans le domain |
| `ADR-RFM-005` | `ACCEPTED_BASELINE` | `fr-nonprofit:2026` consomme un effective plan déjà résolu |
| `ADR-RFM-006` | `ACCEPTED_BASELINE` | Les overlays Non-Profit servent à provenance/impact, pas à re-résolution arbitraire |
| `ADR-RFM-007` | `ACCEPTED_BASELINE` | `member_of_family` n'implique pas `inherits` |
| `ADR-RFM-008` | `ACCEPTED_BASELINE` | `specialized_standard_within_family` n'implique pas `inherits` |
| `ADR-RFM-009` | `ACCEPTED_BASELINE` | `sector_specialization_within_family` n'implique pas `inherits` |
| `ADR-RFM-010` | `ACCEPTED_BASELINE` | Les negative constraints sont first-class |
| `ADR-RFM-011` | `ACCEPTED_BASELINE` | EBNL n'hérite pas automatiquement de SYSCOHADA dans le corpus courant |
| `ADR-RFM-012` | `ACCEPTED_BASELINE` | PCEMF 2010 n'hérite pas de SYSCOHADA 2017 |
| `ADR-RFM-013` | `ACCEPTED_BASELINE` | Un crosswalk structurel n'est pas une équivalence sémantique |
| `ADR-RFM-014` | `ACCEPTED_BASELINE` | L'égalité de code n'est jamais une preuve sémantique |
| `ADR-RFM-015` | `ACCEPTED_BASELINE` | Les concepts neutres ne sont pas des règles comptables |
| `ADR-RFM-016` | `ACCEPTED_BASELINE` | Les concept bindings absents/différés ne sont pas inventés |
| `ADR-RFM-017` | `ACCEPTED_BASELINE` | La structure officielle de reporting est distincte de ses account hints |
| `ADR-RFM-018` | `ACCEPTED_BASELINE` | Un account hint marqué non exécutable reste un candidat |
| `ADR-RFM-019` | `ACCEPTED_BASELINE` | Une confidence élevée ne contourne jamais `human_review_required` |
| `ADR-RFM-020` | `ACCEPTED_BASELINE` | RegulatoryAccountBinding, StatementAccountMapping et ReferenceCrosswalk restent trois graphes distincts |
| `ADR-RFM-021` | `ACCEPTED_BASELINE` | Le posting utilise CompanyAccount, jamais ReferenceAccount directement |
| `ADR-RFM-022` | `ACCEPTED_BASELINE` | Les active charts/reporting profiles pinnent un ReferenceSnapshot |
| `ADR-RFM-023` | `ACCEPTED_BASELINE` | Les upgrades réglementaires sont explicitement planifiés |
| `ADR-RFM-024` | `ACCEPTED_BASELINE` | Le latest provider dataset n'est jamais utilisé implicitement en replay |
| `ADR-RFM-025` | `ACCEPTED_BASELINE` | Les qualifications réglementaires sont par capacité |
| `ADR-RFM-026` | `ACCEPTED_BASELINE` | Présence d'un dataset ne signifie pas exécution qualifiée |
| `ADR-RFM-027` | `ACCEPTED_BASELINE` | Les adapters de stockage produisent un domain model identique |
| `ADR-RFM-028` | `ACCEPTED_BASELINE` | Aucun chemin du repository réglementaire n'entre dans le domain |
| `ADR-RFM-029` | `ACCEPTED_BASELINE` | IFRS reste `NOT_ASSERTED` sans source réglementaire versionnée qualifiée |
| `ADR-RFM-030` | `ACCEPTED_BASELINE` | Les packages par standard ne dupliquent pas les datasets réglementaires |
| `ADR-RFM-031` | `ACCEPTED_BASELINE` | Les candidate mappings peuvent être utilisés en preview, jamais comme mappings actifs sans validation |
| `ADR-RFM-032` | `ACCEPTED_BASELINE` | Les official statement structures peuvent être exécutées comme structure sans rendre leurs hints exécutables |
| `ADR-RFM-033` | `ACCEPTED_BASELINE` | Le snapshot capture les capacités réellement utilisées |
| `ADR-RFM-034` | `ACCEPTED_BASELINE` | Le provider expose idéalement un `ReferenceCapabilitySet` |
| `ADR-RFM-035` | `ACCEPTED_BASELINE` | Les erreurs d'ambiguïté réglementaire sont fail-closed |
| `ADR-RFM-036` | `ACCEPTED_BASELINE` | Les cross-standard analyses exigent des mappings/crosswalks explicitement qualifiés |
| `ADR-RFM-037` | `ACCEPTED_BASELINE` | Les concepts neutres servent à la navigation/candidate generation tant que leurs bindings sont différés |
| `ADR-RFM-038` | `ACCEPTED_BASELINE` | Les tests golden incluent les contraintes négatives et non seulement les cas positifs |
| `ADR-RFM-039` | `ACCEPTED_BASELINE` | `REGULATORY_COMPATIBILITY_MATRIX` est un artefact de release |
| `ADR-RFM-040` | `ACCEPTED_BASELINE` | La qualification Production ne s'applique jamais automatiquement à toutes les capacités d'un standard |

## 13.22 `CON` - Consolidation

**Phase** : `P2.1`  
**Source** : `21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md`  
**Nombre d'ADR** : 70

| ADR | Statut | Décision |
|---|---|---|
| `ADR-CON-001` | `ACCEPTED_BASELINE` | `Consolidation` est un bounded context distinct de la comptabilité individuelle |
| `ADR-CON-002` | `ACCEPTED_BASELINE` | La consolidation ne modifie jamais les ledgers individuels |
| `ADR-CON-003` | `ACCEPTED_BASELINE` | `TrialBalanceSnapshot` est la source privilégiée pour la consolidation comptable |
| `ADR-CON-004` | `ACCEPTED_BASELINE` | `Group` est distinct de `AccountingEntity` |
| `ADR-CON-005` | `ACCEPTED_BASELINE` | Le périmètre de consolidation est versionné |
| `ADR-CON-006` | `ACCEPTED_BASELINE` | Ownership et Control sont des concepts distincts |
| `ADR-CON-007` | `ACCEPTED_BASELINE` | Le contrôle est policy-driven, pas déduit universellement d'un pourcentage |
| `ADR-CON-008` | `ACCEPTED_BASELINE` | Les méthodes FULL/PROPORTIONATE/EQUITY sont configurables par policy |
| `ADR-CON-009` | `ACCEPTED_BASELINE` | Le choix de méthode n'est pas un invariant réglementaire universel du core |
| `ADR-CON-010` | `ACCEPTED_BASELINE` | Les dates d'entrée/sortie de périmètre sont effectives et historisées |
| `ADR-CON-011` | `ACCEPTED_BASELINE` | `EntityReportingPackage` fige la source individuelle acceptée |
| `ADR-CON-012` | `ACCEPTED_BASELINE` | Un package accepté est immutable |
| `ADR-CON-013` | `ACCEPTED_BASELINE` | `GroupChartOfAccounts` est distinct des Company Charts |
| `ADR-CON-014` | `ACCEPTED_BASELINE` | Les mappings local->groupe sont explicites et versionnés |
| `ADR-CON-015` | `ACCEPTED_BASELINE` | Aucun prefix mapping universel n'est autorisé |
| `ADR-CON-016` | `ACCEPTED_BASELINE` | Les split mappings exigent une règle d'allocation explicite |
| `ADR-CON-017` | `ACCEPTED_BASELINE` | La devise fonctionnelle d'une entité est distincte de la devise de présentation groupe |
| `ADR-CON-018` | `ACCEPTED_BASELINE` | Currency Translation est distincte de la comptabilisation FX transactionnelle |
| `ADR-CON-019` | `ACCEPTED_BASELINE` | Les règles de taux de conversion sont policy-driven |
| `ADR-CON-020` | `ACCEPTED_BASELINE` | Les taux utilisés par un snapshot publié sont pinés |
| `ADR-CON-021` | `ACCEPTED_BASELINE` | Les différences de conversion utilisent des rôles groupe, pas des codes hardcodés |
| `ADR-CON-022` | `ACCEPTED_BASELINE` | L'homogénéisation des policies utilise des ConsolidationAdjustments |
| `ADR-CON-023` | `ACCEPTED_BASELINE` | Un retraitement groupe ne modifie pas la comptabilité individuelle |
| `ADR-CON-024` | `ACCEPTED_BASELINE` | `ConsolidationEntry` possède son propre ledger |
| `ADR-CON-025` | `ACCEPTED_BASELINE` | Les ConsolidationEntries respectent la partie double |
| `ADR-CON-026` | `ACCEPTED_BASELINE` | Matching intercompany et élimination sont distincts |
| `ADR-CON-027` | `ACCEPTED_BASELINE` | Les différences intercompany sont explicites et reviewables |
| `ADR-CON-028` | `ACCEPTED_BASELINE` | Une tolerance de matching ne déclenche jamais un write-off implicite |
| `ADR-CON-029` | `ACCEPTED_BASELINE` | Les éliminations sont générées depuis des candidats validés ou policies explicites |
| `ADR-CON-030` | `ACCEPTED_BASELINE` | Les profits internes non réalisés sont policy-driven |
| `ADR-CON-031` | `ACCEPTED_BASELINE` | Investment elimination est distincte des écritures individuelles d'investissement |
| `ADR-CON-032` | `ACCEPTED_BASELINE` | Goodwill est un résultat de mesure policy-driven |
| `ADR-CON-033` | `ACCEPTED_BASELINE` | NCI est un résultat de consolidation, distinct de l'ownership graph |
| `ADR-CON-034` | `ACCEPTED_BASELINE` | La méthode de mesure NCI n'est pas hardcodée dans le core |
| `ADR-CON-035` | `ACCEPTED_BASELINE` | Les Group Result Attributions doivent se réconcilier |
| `ADR-CON-036` | `ACCEPTED_BASELINE` | Les ajustements groupe sont typés et tracés |
| `ADR-CON-037` | `ACCEPTED_BASELINE` | Une erreur de comptabilité individuelle n'est pas silencieusement absorbée par une adjustment permanente |
| `ADR-CON-038` | `ACCEPTED_BASELINE` | Le workflow de consolidation est staged et durable |
| `ADR-CON-039` | `ACCEPTED_BASELINE` | Les stages n'utilisent pas une transaction DB unique longue |
| `ADR-CON-040` | `ACCEPTED_BASELINE` | La fermeture finale du run est atomique |
| `ADR-CON-041` | `ACCEPTED_BASELINE` | Les versions de packages sont pinées dans le run |
| `ADR-CON-042` | `ACCEPTED_BASELINE` | Un changement de source/policy/scope peut rendre le run stale |
| `ADR-CON-043` | `ACCEPTED_BASELINE` | Un ConsolidationSnapshot publié est immutable |
| `ADR-CON-044` | `ACCEPTED_BASELINE` | Un reopen crée une nouvelle révision/snapshot |
| `ADR-CON-045` | `ACCEPTED_BASELINE` | Un reopen source rend les consolidations downstream stale |
| `ADR-CON-046` | `ACCEPTED_BASELINE` | Le drill-down consolidé doit atteindre les JournalEntryLines individuelles |
| `ADR-CON-047` | `ACCEPTED_BASELINE` | Les contributions source, adjustment et elimination sont distinguées dans la lineage |
| `ADR-CON-048` | `ACCEPTED_BASELINE` | Les controls de consolidation sont distincts des adjustments |
| `ADR-CON-049` | `ACCEPTED_BASELINE` | `CONSOLIDATION_CLOSE_GATE` est policy-driven |
| `ADR-CON-050` | `ACCEPTED_BASELINE` | La reproductibilité pinne scope, ownership, mappings, policies, FX et sources |
| `ADR-CON-051` | `ACCEPTED_BASELINE` | Le replay historique ne modifie jamais un snapshot publié |
| `ADR-CON-052` | `ACCEPTED_BASELINE` | Les counterparty dimensions sont conservées lorsque disponibles |
| `ADR-CON-053` | `ACCEPTED_BASELINE` | La réconciliation avancée intercompany peut être déléguée au bounded context Reconciliation |
| `ADR-CON-054` | `ACCEPTED_BASELINE` | Le moteur d'états financiers générique est réutilisé pour les comptes consolidés |
| `ADR-CON-055` | `ACCEPTED_BASELINE` | Financial Analysis reste downstream de la consolidation |
| `ADR-CON-056` | `ACCEPTED_BASELINE` | Les changements de périmètre affectent la comparabilité |
| `ADR-CON-057` | `ACCEPTED_BASELINE` | Les manual adjustments nécessitent raison, provenance et audit |
| `ADR-CON-058` | `ACCEPTED_BASELINE` | Les sign-offs réutilisent l'architecture Controls/Audit |
| `ADR-CON-059` | `ACCEPTED_BASELINE` | Les snapshots de consolidation disposent d'un EvidenceBundle |
| `ADR-CON-060` | `ACCEPTED_BASELINE` | Les finalizations peuvent utiliser Transactional Outbox |
| `ADR-CON-061` | `ACCEPTED_BASELINE` | Les ConsolidationEntries ont une séquence distincte des journaux individuels |
| `ADR-CON-062` | `ACCEPTED_BASELINE` | Les opérations critiques de consolidation sont idempotentes |
| `ADR-CON-063` | `ACCEPTED_BASELINE` | Les éliminations ne peuvent pas être postées deux fois |
| `ADR-CON-064` | `ACCEPTED_BASELINE` | Le matching peut exister à plusieurs granularités |
| `ADR-CON-065` | `ACCEPTED_BASELINE` | Le mode ACCOUNT constitue le minimum viable P2.1 |
| `ADR-CON-066` | `ACCEPTED_BASELINE` | Les crosswalks réglementaires ne sont jamais utilisés comme conversions sémantiques automatiques |
| `ADR-CON-067` | `ACCEPTED_BASELINE` | Un ConsolidationPolicySnapshot est pinner par run |
| `ADR-CON-068` | `ACCEPTED_BASELINE` | Le Consolidation Engine demeure framework-neutral |
| `ADR-CON-069` | `ACCEPTED_BASELINE` | Le mode publication fail-closed |
| `ADR-CON-070` | `ACCEPTED_BASELINE` | Les anciennes consolidations restent conservées avec leur provenance même partielle |

## 13.23 `REC` - Reconciliation

**Phase** : `P2.2`  
**Source** : `22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md`  
**Nombre d'ADR** : 60

| ADR | Statut | Décision |
|---|---|---|
| `ADR-REC-001` | `ACCEPTED_BASELINE` | `Reconciliation` est un bounded context distinct du Posting |
| `ADR-REC-002` | `ACCEPTED_BASELINE` | Le moteur rapproche des snapshots/read models, pas des agrégats live |
| `ADR-REC-003` | `ACCEPTED_BASELINE` | Les sources d'un run publié sont pinées et checksummées |
| `ADR-REC-004` | `ACCEPTED_BASELINE` | Une source partielle reste explicitement `PARTIAL` |
| `ADR-REC-005` | `ACCEPTED_BASELINE` | `ReconciliationItem` normalise les sources sans perdre la provenance |
| `ADR-REC-006` | `ACCEPTED_BASELINE` | Aucune convention de signe n'est universelle dans le core |
| `ADR-REC-007` | `ACCEPTED_BASELINE` | Les mappings de signe/date/devise sont gérés par policies/adapters |
| `ADR-REC-008` | `ACCEPTED_BASELINE` | Les définitions de rapprochement sont versionnées |
| `ADR-REC-009` | `ACCEPTED_BASELINE` | Le matching déterministe précède les heuristiques |
| `ADR-REC-010` | `ACCEPTED_BASELINE` | Les stratégies ne postent ni ne mutent les sources |
| `ADR-REC-011` | `ACCEPTED_BASELINE` | `MatchCandidate` est distinct de `ReconciliationMatch` |
| `ADR-REC-012` | `ACCEPTED_BASELINE` | Un score de confiance n'autorise pas à lui seul un auto-match |
| `ADR-REC-013` | `ACCEPTED_BASELINE` | Toute ambiguïté de match critique est fail-closed |
| `ADR-REC-014` | `ACCEPTED_BASELINE` | Les matches one-to-one, one-to-many, many-to-one et many-to-many sont supportés |
| `ADR-REC-015` | `ACCEPTED_BASELINE` | Les allocations ne dépassent jamais le montant unmatched disponible |
| `ADR-REC-016` | `ACCEPTED_BASELINE` | Une tolerance est une règle de rapprochement, pas un write-off |
| `ADR-REC-017` | `ACCEPTED_BASELINE` | Les différences restent visibles même sous le seuil de matérialité |
| `ADR-REC-018` | `ACCEPTED_BASELINE` | `DifferenceType`, `Cause` et `Status` sont des concepts distincts |
| `ADR-REC-019` | `ACCEPTED_BASELINE` | `EXPLAINED` ne signifie pas `RESOLVED` |
| `ADR-REC-020` | `ACCEPTED_BASELINE` | Toute écriture corrective passe par `JournalEntryProposal` puis Posting normal |
| `ADR-REC-021` | `ACCEPTED_BASELINE` | Le moteur ne modifie jamais silencieusement une source externe |
| `ADR-REC-022` | `ACCEPTED_BASELINE` | Le rapprochement bancaire est une spécialisation du moteur générique |
| `ADR-REC-023` | `ACCEPTED_BASELINE` | Les formats bancaires restent dans les adapters |
| `ADR-REC-024` | `ACCEPTED_BASELINE` | Le rapprochement sous-livre/GL réutilise les snapshots P1.4 |
| `ADR-REC-025` | `ACCEPTED_BASELINE` | Settlement/AccountingMatch et Reconciliation restent distincts |
| `ADR-REC-026` | `ACCEPTED_BASELINE` | L'intercompany matching peut être délégué à Reconciliation |
| `ADR-REC-027` | `ACCEPTED_BASELINE` | Consolidation reste propriétaire des éliminations |
| `ADR-REC-028` | `ACCEPTED_BASELINE` | Les confirmations externes nécessitent provenance et checksum |
| `ADR-REC-029` | `ACCEPTED_BASELINE` | Les parsers de confirmations sont des adapters |
| `ADR-REC-030` | `ACCEPTED_BASELINE` | Les contrôles d'import peuvent réutiliser le moteur générique |
| `ADR-REC-031` | `ACCEPTED_BASELINE` | Le core cible A/B mais prépare le multi-source |
| `ADR-REC-032` | `ACCEPTED_BASELINE` | Les normalisations de référence préservent la valeur brute |
| `ADR-REC-033` | `ACCEPTED_BASELINE` | Les FX de rapprochement utilisent des observations pinées |
| `ADR-REC-034` | `ACCEPTED_BASELINE` | Matérialité, tolerance et blocking sont trois concepts distincts |
| `ADR-REC-035` | `ACCEPTED_BASELINE` | Les controls consomment les faits du moteur de réconciliation |
| `ADR-REC-036` | `ACCEPTED_BASELINE` | Closing dépend de résultats de controls, pas de l'implémentation du matching |
| `ADR-REC-037` | `ACCEPTED_BASELINE` | Le sign-off réutilise Controls/Audit |
| `ADR-REC-038` | `ACCEPTED_BASELINE` | Un `ReconciliationSnapshot` publié est immutable |
| `ADR-REC-039` | `ACCEPTED_BASELINE` | Un rerun crée un nouveau run/snapshot |
| `ADR-REC-040` | `ACCEPTED_BASELINE` | Un changement de source rend les résultats downstream stale sans réécriture |
| `ADR-REC-041` | `ACCEPTED_BASELINE` | Le drill-down doit atteindre les éléments sources |
| `ADR-REC-042` | `ACCEPTED_BASELINE` | Match, difference, resolution et adjustment conservent leur lineage |
| `ADR-REC-043` | `ACCEPTED_BASELINE` | Le replay pinne toutes les versions de policies/strategies |
| `ADR-REC-044` | `ACCEPTED_BASELINE` | Les modèles fuzzy/ML éventuels restent optionnels et versionnés |
| `ADR-REC-045` | `ACCEPTED_BASELINE` | Une fuzzy match produit d'abord un candidat |
| `ADR-REC-046` | `ACCEPTED_BASELINE` | Les décisions humaines de matching sont auditées |
| `ADR-REC-047` | `ACCEPTED_BASELINE` | Un match validé est réversible sans suppression historique |
| `ADR-REC-048` | `ACCEPTED_BASELINE` | Les commandes critiques sont idempotentes |
| `ADR-REC-049` | `ACCEPTED_BASELINE` | Les acceptations concurrentes protègent les montants unmatched |
| `ADR-REC-050` | `ACCEPTED_BASELINE` | Une difference ne peut générer deux ajustements comptables non intentionnels |
| `ADR-REC-051` | `ACCEPTED_BASELINE` | Les repositories write et query ports restent séparés |
| `ADR-REC-052` | `ACCEPTED_BASELINE` | Les adapters source implémentent un contrat commun de snapshot |
| `ADR-REC-053` | `ACCEPTED_BASELINE` | Les items volumineux peuvent être materialized, artifact-backed ou hybrides selon adapter |
| `ADR-REC-054` | `ACCEPTED_BASELINE` | Les algorithmes évitent les scans naïfs O(N²) |
| `ADR-REC-055` | `ACCEPTED_BASELINE` | L'ordre de candidate generation est déterministe |
| `ADR-REC-056` | `ACCEPTED_BASELINE` | Les métriques de match documentent leur numérateur/dénominateur |
| `ADR-REC-057` | `ACCEPTED_BASELINE` | Les logs n'exposent pas les payloads bancaires sensibles par défaut |
| `ADR-REC-058` | `ACCEPTED_BASELINE` | Les rules declaratives ne peuvent pas exécuter du code arbitraire |
| `ADR-REC-059` | `ACCEPTED_BASELINE` | `accounting.reconciliation` est la façade publique cible |
| `ADR-REC-060` | `ACCEPTED_BASELINE` | La réconciliation est un consommateur transversal, jamais une seconde source comptable canonique |

## 13.24 `AFA` - Advanced Financial Analysis Boundaries

**Phase** : `P2.3`  
**Source** : `23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md`  
**Nombre d'ADR** : 50

| ADR | Statut | Décision |
|---|---|---|
| `ADR-AFA-001` | `ACCEPTED_BASELINE` | PyAccountingKit reste un framework comptable et d'analyse financière historique, pas un moteur Corporate Finance général |
| `ADR-AFA-002` | `ACCEPTED_BASELINE` | Les capacités nécessitant hypothèses futures, données de marché ou discounting sortent du core |
| `ADR-AFA-003` | `ACCEPTED_BASELINE` | SIG, EBE, EBITDA, CAF, FRNG, BFR et trésorerie restent dans Financial Analysis |
| `ADR-AFA-004` | `ACCEPTED_BASELINE` | Les ratios historiques accounting-based restent dans PyAccountingKit |
| `ADR-AFA-005` | `ACCEPTED_BASELINE` | Les ratios de marché relèvent du Corporate Finance |
| `ADR-AFA-006` | `ACCEPTED_BASELINE` | Les tendances historiques restent dans PyAccountingKit, les forecasts sortent du core |
| `ADR-AFA-007` | `ACCEPTED_BASELINE` | Les diagnostics historiques accounting-based restent dans PyAccountingKit |
| `ADR-AFA-008` | `ACCEPTED_BASELINE` | Les diagnostics prédictifs/probabilistes nécessitent un framework de Risk/Credit/Corporate Finance |
| `ADR-AFA-009` | `ACCEPTED_BASELINE` | Le risque de liquidité/leverage historique peut être analysé dans PyAccountingKit |
| `ADR-AFA-010` | `ACCEPTED_BASELINE` | Market Risk, Project Risk et Valuation Risk restent hors core |
| `ADR-AFA-011` | `ACCEPTED_BASELINE` | VAN/NPV relève du Corporate Finance |
| `ADR-AFA-012` | `ACCEPTED_BASELINE` | TRI/IRR et MIRR relèvent du Corporate Finance |
| `ADR-AFA-013` | `ACCEPTED_BASELINE` | Payback et Profitability Index relèvent de l'Investment Appraisal |
| `ADR-AFA-014` | `ACCEPTED_BASELINE` | Le calcul du coût des fonds propres relève du Corporate Finance |
| `ADR-AFA-015` | `ACCEPTED_BASELINE` | CAPM et Beta restent hors PyAccountingKit |
| `ADR-AFA-016` | `ACCEPTED_BASELINE` | Le coût marginal de la dette relève du Corporate Finance |
| `ADR-AFA-017` | `ACCEPTED_BASELINE` | Un ratio historique d'intérêt/dette ne doit pas être nommé implicitement `CostOfDebt` |
| `ADR-AFA-018` | `ACCEPTED_BASELINE` | WACC relève du Corporate Finance |
| `ADR-AFA-019` | `ACCEPTED_BASELINE` | La structure de capital historique peut être analysée, la structure cible relève du Corporate Finance |
| `ADR-AFA-020` | `ACCEPTED_BASELINE` | DCF, FCFF/FCFE forecast et Terminal Value restent hors core |
| `ADR-AFA-021` | `ACCEPTED_BASELINE` | Enterprise Value et Equity Value relèvent du Corporate Finance |
| `ADR-AFA-022` | `ACCEPTED_BASELINE` | Les multiples de marché relèvent du Corporate Finance |
| `ADR-AFA-023` | `ACCEPTED_BASELINE` | Sensitivity et Scenario Analysis prospectifs restent hors core |
| `ADR-AFA-024` | `ACCEPTED_BASELINE` | Monte Carlo reste hors PyAccountingKit |
| `ADR-AFA-025` | `ACCEPTED_BASELINE` | VaR et Expected Shortfall ne sont pas des capacités core PyAccountingKit |
| `ADR-AFA-026` | `ACCEPTED_BASELINE` | Les covenant tests historiques peuvent rester, le forecast covenant headroom sort du core |
| `ADR-AFA-027` | `ACCEPTED_BASELINE` | Les concentrations historiques issues des subledgers peuvent rester dans Financial Analysis |
| `ADR-AFA-028` | `ACCEPTED_BASELINE` | Les stress simulations de concentration/liquidité sortent du core |
| `ADR-AFA-029` | `ACCEPTED_BASELINE` | Budgeting et Forecasting ne sont pas des responsabilités du core PyAccountingKit |
| `ADR-AFA-030` | `ACCEPTED_BASELINE` | Un futur Corporate Finance framework peut consommer un ForecastSnapshot provenant d'un système FP&A |
| `ADR-AFA-031` | `ACCEPTED_BASELINE` | Les normalisations de valorisation judgmental restent hors accounting analysis historique |
| `ADR-AFA-032` | `ACCEPTED_BASELINE` | `FinancialFactsSnapshot` est le bridge conceptuel recommandé vers Corporate Finance |
| `ADR-AFA-033` | `ACCEPTED_BASELINE` | Corporate Finance ne dépend pas des repositories/ORM internes de PyAccountingKit |
| `ADR-AFA-034` | `ACCEPTED_BASELINE` | Corporate Finance ne modifie jamais les écritures comptables |
| `ADR-AFA-035` | `ACCEPTED_BASELINE` | Les données de marché restent distinctes des données comptables |
| `ADR-AFA-036` | `ACCEPTED_BASELINE` | Les assumptions prospectives restent distinctes des accounting facts |
| `ADR-AFA-037` | `ACCEPTED_BASELINE` | Les résultats de valuation sont des decision-support artifacts, pas des accounting facts |
| `ADR-AFA-038` | `ACCEPTED_BASELINE` | Accounting fair-value measurement et enterprise valuation sont deux domaines différents |
| `ADR-AFA-039` | `ACCEPTED_BASELINE` | PyAccountingKit peut consommer un taux externe pour une measurement policy sans devenir propriétaire du WACC |
| `ADR-AFA-040` | `ACCEPTED_BASELINE` | Discounting comptable et investment discounting doivent rester séparés sémantiquement |
| `ADR-AFA-041` | `ACCEPTED_BASELINE` | L'historical Net Debt peut rester dans Financial Analysis, les valuation adjustments restent Corporate Finance |
| `ADR-AFA-042` | `ACCEPTED_BASELINE` | Historical ROIC peut rester, EVA nécessitant WACC sort du core |
| `ADR-AFA-043` | `ACCEPTED_BASELINE` | Historical DuPont Analysis peut rester, forecast DuPont sort du core |
| `ADR-AFA-044` | `ACCEPTED_BASELINE` | Accounting effects d'une décision de financement restent dans PyAccountingKit, la décision elle-même reste Corporate Finance |
| `ADR-AFA-045` | `ACCEPTED_BASELINE` | Aucun SDK de market data ne devient une dépendance obligatoire de PyAccountingKit core |
| `ADR-AFA-046` | `ACCEPTED_BASELINE` | Les solveurs numériques d'IRR ne doivent pas contaminer les garanties Decimal de Money accounting |
| `ADR-AFA-047` | `ACCEPTED_BASELINE` | Les futures valuations doivent pouvoir se réconcilier à un snapshot comptable via un ValuationBridge |
| `ADR-AFA-048` | `ACCEPTED_BASELINE` | Les tests NPV/IRR/WACC/DCF/Monte Carlo appartiennent au futur framework, pas au test contract PyAccountingKit |
| `ADR-AFA-049` | `ACCEPTED_BASELINE` | Toute proposition d'ajouter Corporate Finance au core doit passer par un nouvel ADR de scope |
| `ADR-AFA-050` | `ACCEPTED_BASELINE` | La frontière est définie par la sémantique et les inputs requis, pas par la taille du code |

---

# 14. Index par phase

| Phase | ADR | Namespaces |
|---|---:|---|
| `P0.2` | 19 | ARCH |
| `P0.3` | 30 | DOM |
| `P0.4` | 18 | RULE |
| `P0.5` | 20 | POL |
| `P0.6` | 20 | REF |
| `P0.7` | 24 | COA |
| `P0.8` | 30 | LED |
| `P0.9` | 30 | CLOSE |
| `P0.10` | 32 | AUD, CTRL, TRACE |
| `P0.11` | 40 | PERS |
| `P0.12` | 30 | TEST |
| `P1.1` | 40 | IMP |
| `P1.2` | 40 | REP |
| `P1.3` | 40 | ANA |
| `P1.4` | 32 | SUB |
| `P1.5` | 40 | API |
| `P1.6` | 40 | REL |
| `P1.7` | 40 | CFA |
| `P1.8` | 40 | RFM |
| `P2.1` | 70 | CON |
| `P2.2` | 60 | REC |
| `P2.3` | 50 | AFA |


---

# 15. Index P2

| Phase | Namespace | ADR | Source |
|---|---|---:|---|
| `P2.1` | `CON` | 70 | Consolidation |
| `P2.2` | `REC` | 60 | Reconciliation |
| `P2.3` | `AFA` | 50 | Advanced Financial Analysis Boundaries |

**P2 ajoute donc 180 ADR.**

---

# 16. Contrôles de cohérence du registre

```text
ADR total: 785
Unique ADR IDs: 785
Duplicate ADR IDs: 0
Namespaces: 24
P2 ADR: 180
```

Checks CI recommandés :

```text
ADR-REG-001 unique identifier check
ADR-REG-002 source document parity
ADR-REG-003 superseded target exists
ADR-REG-004 no supersession cycle
ADR-REG-005 no duplicate ACTIVE decision identifier
ADR-REG-006 architecture docs and register parity
ADR-REG-007 release-impact metadata for breaking ADR
ADR-REG-008 regulatory evidence required for authority changes
ADR-REG-009 bounded-context dependency guard
ADR-REG-010 Corporate Finance scope guard
```

Les `ADR-REG-*` sont des checks de gouvernance, pas des ADR et ne sont pas comptabilisés dans les 785.

---

# 17. Gestion des supersessions

```text
ADR-XYZ-004
status: SUPERSEDED
superseded_by: ADR-XYZ-021

ADR-XYZ-021
status: ACCEPTED_BASELINE
supersedes: [ADR-XYZ-004]
```

L'ancien ADR reste visible pour préserver l'historique.

---

# 18. Registre et releases

À partir du gel de l'API, chaque RC doit vérifier :

```text
no undocumented accepted decision change
no missing register entry
no dangling supersession
no unreviewed breaking ADR
no regulatory authority escalation without evidence
no public API breaking ADR without version impact
no P2 bounded-context violation of P0/P1 invariants
```

---

# 19. Registre et architecture guards

Le registre doit désormais alimenter des tests d'architecture capables de détecter notamment :

```text
domain imports Django/SQLAlchemy
consolidation mutates entity ledger
reconciliation posts directly
candidate regulatory mapping becomes executable implicitly
Corporate Finance capability appears in pyaccountingkit core
```

---

# 20. Critères d'acceptation du refresh

```text
[x] baseline P0/P1 conservée
[x] 605 ADR historiques conservés
[x] ADR-CON-001..070 intégrés
[x] ADR-REC-001..060 intégrés
[x] ADR-AFA-001..050 intégrés
[x] total = 785 ADR
[x] namespaces = 24
[x] index P2 ajouté
[x] convergences P2 ajoutées
[x] règles de cohérence P2 ajoutées
[x] checks ADR-REG étendus
[x] phase index rafraîchi
[x] next-step governance actualisé
```

---

# 21. Prochaine action recommandée

La roadmap documentaire d'architecture `00` à `23` étant désormais couverte, la prochaine étape recommandée n'est plus un nouveau document d'architecture de domaine.

Elle est :

```text
PYACCOUNTINGKIT_IMPLEMENTATION_ROADMAP.md
```

avec :

```text
lots d'implémentation
versions
dépendances
gates
Definition of Done
ordre de livraison
mapping architecture -> code
```

Puis :

```text
PyAccountingKit 0.0.1 - Repository Bootstrap
```

---

# 22. Conclusion

Le registre consolidé reflète maintenant toute l'architecture produite jusqu'au P2.3 :

```text
605 ADR P0/P1
+ 70 Consolidation
+ 60 Reconciliation
+ 50 Advanced Finance Boundaries
=
785 ADR
```

Les trois nouvelles frontières sont désormais intégrées à la gouvernance centrale :

```text
Consolidation
    has its own group ledger
    and never mutates entity accounting.

Reconciliation
    matches and explains
    but never becomes a second posting engine.

Advanced Financial Analysis
    stops where forward-looking Corporate Finance begins.
```

Le registre constitue désormais la baseline décisionnelle complète avant passage à l'implémentation.
