# 09 - PyAccountingKit - Architecture des contrôles, de l'audit et de la traçabilité

> **Projet** : PyAccountingKit  
> **Document** : `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> - `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`
> - `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`
> - `07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`
> - `08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`
> **Statut** : P0.10 - Architecture des contrôles, audit trail, provenance et reproductibilité  
> **Langue** : Français  
> **Objet** : Définir le moteur de contrôles comptables, les contrôles bloquants et non bloquants, l'audit trail append-only, la provenance des données, la chaîne de traçabilité, les preuves, les checksums, les snapshots, la reproductibilité des résultats et les contrats permettant de relier toute décision comptable à ses sources, policies, contrôles, écritures et outputs.

---

# 1. Résumé exécutif

PyAccountingKit doit pouvoir répondre à cinq questions pour toute opération significative :

```text
1. Qu'est-ce qui a été fait ?

2. Pourquoi cela a-t-il été fait ?

3. Avec quelles données / sources ?

4. Selon quelle règle / policy / version ?

5. Peut-on reproduire exactement le résultat ?
```

Le bounded context cible est structuré autour de quatre capacités distinctes :

```text
Accounting Controls

Audit Trail

Provenance & Lineage

Reproducibility & Evidence
```

Architecture conceptuelle :

```text
Source Data
    |
    v
Normalization / Mapping
    |
    v
Accounting Policies
    |
    v
JournalEntry / Ledger / Reporting
    |
    +----------------------+
    |                      |
    v                      v
Controls                Audit Events
    |                      |
    v                      v
ControlRun             Audit Trail
    |                      |
    +-----------+----------+
                |
                v
        Evidence / Provenance
                |
                v
      Reproducible Snapshot
```

Le principe central est :

```text
Control != Invariant

Control != Validation Rule

AuditEvent != DomainEvent

Provenance != Audit

Snapshot != Source of Truth

Checksum != Semantic Validation
```

---

# 2. Référence fonctionnelle CFA FRA

CFA FRA fournit déjà plusieurs comportements importants qui doivent être généralisés.

Son catalogue de contrôles contient notamment :

```text
ENTRY_BALANCED

TRIAL_BALANCE_BALANCED

BALANCE_SHEET_BALANCED

CASHFLOW_RECONCILED

UNKNOWN_ACCOUNT

INVALID_ACCOUNT

CLOSED_PERIOD_ENTRY

DUPLICATE_FEC

INVALID_FEC_LINE

TEMPORARY_ACCOUNT_AFTER_CLOSE
```

Le moteur de clôture y refuse la fermeture lorsqu'il existe :

```text
une balance non équilibrée

un cash-flow non réconcilié

des écritures DRAFT restantes

des contrôles bloquants
```

Le projet possède également un `AuditEvent` pour les mutations importantes :

```text
FEC_UPLOAD

FEC_IMPORT

ENTRY_CREATE

ENTRY_VALIDATE

ENTRY_POST

ENTRY_REVERSE

ACCOUNT_CREATE

ACCOUNT_UPDATE

PERIOD_CLOSE
```

---

# 3. Référence fonctionnelle de provenance CFA FRA

Le pipeline FEC apporte un autre principe structurant :

```text
original file

raw lines

line number

row hash

source reference

SHA-256

normalized entry key
```

Ces éléments permettent :

```text
audit

debug

reprocessing

rapprochement source -> écriture

preuve d'origine
```

PyAccountingKit généralise ce modèle à toutes les sources.

---

# 4. Traçabilité des exports réglementaires

CFA FRA associe également aux exports réglementaires :

```text
snapshot

SHA-256

audit events
```

Ce comportement confirme la nécessité de traiter la traçabilité comme un concept transversal et non comme une simple table de logs.

---

# 5. Objectifs du bounded context

Le moteur doit permettre de :

1. définir des contrôles versionnés ;
2. exécuter des contrôles sur un scope explicite ;
3. distinguer erreur, warning, information et blocage ;
4. stocker le résultat et les preuves ;
5. déterminer si un workflow peut continuer ;
6. expliquer tout résultat de contrôle ;
7. produire un audit trail append-only ;
8. conserver l'acteur et le contexte d'une mutation ;
9. conserver les valeurs avant/après lorsque pertinent ;
10. relier source brute et objet comptable ;
11. relier écriture, ligne, mapping, policy, contrôle et report ;
12. conserver les checksums d'artefacts ;
13. reproduire une computation à partir d'un snapshot ;
14. identifier les dépendances exactes d'un résultat ;
15. permettre des golden tests et replay contrôlés ;
16. éviter que la simple présence d'un hash soit prise pour une preuve de conformité comptable.

---

# 6. Non-objectifs

Ce bounded context ne doit pas :

```text
autoriser un utilisateur

remplacer les validations transactionnelles

modifier une écriture postée

décider seul d'une policy réglementaire

être un système SIEM complet

être un moteur général de GRC

être un data lineage platform universel

être un stockage documentaire complet
```

---

# 7. Classification des règles

Le document `03` a introduit plusieurs catégories.

Pour les contrôles, il faut conserver :

```text
UNIVERSAL_ACCOUNTING_INVARIANT

DOMAIN_POLICY

REGULATORY_RULE

REFERENCE_SPECIFIC_RULE

ACCOUNTING_METHOD

PRESENTATION_RULE

ANALYTICAL_DEFINITION

CONTROL

HEURISTIC

PROCESS_REQUIREMENT
```

---

# 8. Invariant vs Control

Exemple :

```text
ENTRY_BALANCED
```

peut exister sous deux formes :

```text
Invariant:
    une écriture VALIDATED / POSTED doit être équilibrée

Control:
    rechercher dans un dataset des écritures non équilibrées
```

Le premier protège une mutation.

Le second diagnostique un ensemble de données.

---

# 9. Validation Rule vs Control

```text
Validation Rule
    agit avant une transition métier

Control
    produit un résultat observable et historisé
```

Exemple :

```text
post_entry()
    refuses unbalanced entry

vs

ControlRun
    scans all posted entries for balance integrity
```

---

# 10. Control != Policy

Une policy peut dire :

```text
cash flow reconciliation is blocking at year end
```

Le control calcule :

```text
PASS / FAIL
```

La policy détermine :

```text
whether FAIL blocks the workflow
```

---

# 11. Control Catalog

Le moteur possède un catalogue de définitions.

```text
ControlCatalog
|
+-- ControlDefinition
+-- ControlVersion
+-- ControlApplicability
+-- ControlSeverityPolicy
```

---

# 12. `ControlDefinition`

```text
ControlDefinition
|
+-- control_code
+-- name
+-- description
+-- category
+-- default_severity
+-- default_blocking
+-- evaluator_id
+-- version
+-- applicability
+-- evidence_requirements
+-- metadata
```

---

# 13. `ControlCode`

Value Object stable :

```text
ENTRY_BALANCED

TRIAL_BALANCE_BALANCED

CASHFLOW_RECONCILED
```

Un code ne doit pas être recyclé pour une autre sémantique.

---

# 14. Version du contrôle

```text
ControlDefinitionVersion
```

doit changer si la sémantique change.

---

# 15. `ControlCategory`

Proposition :

```text
STRUCTURAL

ACCOUNTING

LEDGER

REPORTING

CLOSING

IMPORT

REFERENCE

MAPPING

RECONCILIATION

PROVENANCE

PROCESS

SECURITY_ADJACENT

CUSTOM
```

---

# 16. `ControlSeverity`

```text
INFO

WARNING

ERROR

CRITICAL
```

---

# 17. Severity != Blocking

Un contrôle peut être :

```text
ERROR
but non-blocking
```

ou :

```text
WARNING
but blocking
```

si une policy le décide explicitement.

Il est préférable de garder les deux dimensions distinctes.

---

# 18. `ControlBlockingPolicy`

```text
NON_BLOCKING

BLOCKING

BLOCKING_AT_STAGE

CONTEXTUAL
```

---

# 19. `ControlApplicability`

```text
ControlApplicability
|
+-- entity?
+-- standard?
+-- edition?
+-- period_type?
+-- closing_type?
+-- journal_type?
+-- entry_type?
+-- source_type?
+-- reporting_profile?
+-- metadata
```

---

# 20. `ControlEvaluator`

Contrat :

```python
class ControlEvaluator(Protocol):
    def evaluate(
        self,
        context: ControlEvaluationContext,
    ) -> "ControlEvaluation":
        ...
```

---

# 21. Pureté de l'évaluateur

Un evaluator doit idéalement être :

```text
read-only
deterministic
side-effect free
```

Il ne doit pas réparer automatiquement les données.

---

# 22. `ControlEvaluationContext`

```text
ControlEvaluationContext
|
+-- accounting_entity_id
+-- scope
+-- control_definition
+-- policy_set_snapshot
+-- reference_snapshot
+-- source_snapshot?
+-- clock
+-- inputs
```

---

# 23. `ControlEvaluation`

```text
ControlEvaluation
|
+-- status
+-- severity
+-- blocking
+-- summary
+-- findings
+-- metrics
+-- evidence
+-- execution_trace
```

---

# 24. `ControlStatus`

```text
PASS

FAIL

WARNING

SKIPPED

NOT_APPLICABLE

INDETERMINATE

ERROR
```

---

# 25. `INDETERMINATE`

Ce statut est important.

Il signifie :

```text
le contrôle n'a pas pu conclure
```

Exemples :

```text
source manquante

mapping ambigu

policy absente

projection stale

dépendance indisponible
```

---

# 26. Fail-closed

Pour un contrôle requis et bloquant :

```text
INDETERMINATE
```

doit généralement bloquer.

La policy peut le confirmer.

---

# 27. `ControlFinding`

```text
ControlFinding
|
+-- finding_id
+-- code
+-- message
+-- severity
+-- object_refs
+-- expected?
+-- actual?
+-- difference?
+-- evidence_refs
```

---

# 28. Exemple `ENTRY_BALANCED`

```text
ControlDefinition:
    ENTRY_BALANCED

scope:
    JournalEntry

finding:
    entry_id
    total_debit
    total_credit
    difference
```

---

# 29. Exemple `TRIAL_BALANCE_BALANCED`

```text
expected:
    total_debit == total_credit

actual:
    total_debit
    total_credit

difference:
    total_debit - total_credit
```

---

# 30. Exemple `BALANCE_SHEET_BALANCED`

La définition doit être liée à la version du mapping / reporting.

Elle ne doit pas supposer des lignes codées en dur dans le core.

---

# 31. Exemple `CASHFLOW_RECONCILED`

Le contrôle vérifie conceptuellement :

```text
Opening Cash
+
CFO
+
CFI
+
CFF
=
Closing Cash
```

La définition exacte dépend du modèle de cash-flow.

---

# 32. Exemple `TEMPORARY_ACCOUNTS_CLOSED`

Le contrôle utilise :

```text
TemporaryAccountPolicy
```

et non :

```text
account code prefix
```

---

# 33. Exemple `UNKNOWN_ACCOUNT`

Contrôle :

```text
source account
does not map to known CompanyAccount
```

---

# 34. Exemple `INVALID_ACCOUNT`

Peut couvrir :

```text
inactive account

non-postable account

invalid historical binding
```

Le sens exact doit être versionné.

---

# 35. Exemple `CLOSED_PERIOD_ENTRY`

Contrôle diagnostique :

```text
entry accounting date
falls into closed period
with unauthorized posting provenance
```

---

# 36. Exemple `DUPLICATE_FEC`

Le projet CFA FRA traite certains doublons comme warning et ne les supprime pas automatiquement.

PyAccountingKit doit conserver cette prudence :

```text
duplicate candidate
!=
confirmed duplicate
```

---

# 37. Control Set

Un workflow peut exécuter un ensemble nommé.

```text
ControlSet
|
+-- id
+-- code
+-- version
+-- controls
+-- applicability
```

---

# 38. Exemples de ControlSet

```text
POSTING_INTEGRITY

FEC_IMPORT

MONTH_END

YEAR_END

PRE_CLOSE

POST_CLOSE

REGULATORY_REPORT

REFERENCE_UPGRADE

CUSTOM
```

---

# 39. `ControlRun`

Aggregate Root :

```text
ControlRun
|
+-- id
+-- accounting_entity_id
+-- control_set_id?
+-- status
+-- scope
+-- definition_snapshot
+-- policy_snapshot
+-- reference_snapshot?
+-- source_snapshot?
+-- results
+-- started_at
+-- completed_at?
+-- triggered_by
+-- correlation_id
+-- checksum?
```

---

# 40. Pourquoi `ControlRun` est un Aggregate Root

Il représente une exécution cohérente et historisée.

Il doit conserver :

```text
what was evaluated

with which definitions

against which data

when

with what result
```

---

# 41. `ControlRunStatus`

```text
PENDING

RUNNING

COMPLETED

PARTIALLY_FAILED

FAILED

CANCELLED
```

---

# 42. `ControlResult`

```text
ControlResult
|
+-- control_code
+-- control_version
+-- status
+-- severity
+-- blocking
+-- started_at
+-- completed_at
+-- findings
+-- metrics
+-- evidence_refs
+-- execution_checksum?
```

---

# 43. Immutabilité du résultat

Un `ControlResult` finalisé est immutable.

Une réévaluation produit :

```text
new ControlRun
```

---

# 44. Re-run

Correct :

```text
ControlRun #1
    FAIL

correction

ControlRun #2
    PASS
```

Incorrect :

```text
edit ControlRun #1 from FAIL to PASS
```

---

# 45. Blocking Decision

Le moteur peut exposer :

```text
ControlGateDecision
|
+-- allowed
+-- blocking_results
+-- warnings
+-- evaluated_at
```

---

# 46. `ControlGate`

```text
ControlGate
|
+-- gate_code
+-- required_control_set
+-- stage
+-- decision_policy
```

---

# 47. Exemples de gates

```text
IMPORT_FINALIZATION_GATE

POSTING_GATE

CLOSING_GATE

REGULATORY_EXPORT_GATE

REFERENCE_ACTIVATION_GATE
```

---

# 48. Gate != Control

```text
Control
    tells what is true

Gate
    decides whether workflow may continue
```

---

# 49. Closing gate

Exemple :

```text
CLOSING_GATE
requires

TRIAL_BALANCE_BALANCED = PASS

required reconciliations = PASS

no blocking findings

required adjustment runs complete
```

---

# 50. Gate evaluation is versioned

Changer :

```text
cash flow reconciliation from warning to blocking
```

est un changement de policy de gate.

---

# 51. `ControlDecisionTrace`

```text
ControlDecisionTrace
|
+-- gate_code
+-- gate_policy_version
+-- control_run_ids
+-- decision
+-- rationale
```

---

# 52. Evidence

Un contrôle doit pouvoir citer des preuves structurées.

```text
Evidence
|
+-- evidence_id
+-- evidence_type
+-- source_ref
+-- object_ref?
+-- checksum?
+-- observed_at?
+-- metadata
```

---

# 53. `EvidenceType`

```text
SOURCE_FILE

SOURCE_LINE

JOURNAL_ENTRY

JOURNAL_LINE

TRIAL_BALANCE

REPORT_SNAPSHOT

REFERENCE_ARTIFACT

POLICY_TRACE

CONTROL_RESULT

EXTERNAL_OBSERVATION

MANUAL_DOCUMENT

CUSTOM
```

---

# 54. Evidence != Source

Une preuve peut être :

```text
un résultat dérivé
```

Une source représente :

```text
l'origine d'une donnée
```

---

# 55. Provenance

La provenance répond à :

```text
D'où vient cette donnée ?
```

---

# 56. Audit

L'audit répond à :

```text
Qui a fait quoi et quand ?
```

---

# 57. Lineage

Le lineage répond à :

```text
Quelles transformations relient la source au résultat ?
```

---

# 58. Reproducibility

La reproductibilité répond à :

```text
Peut-on recalculer le résultat avec les mêmes inputs ?
```

---

# 59. Quatre concepts distincts

```text
Provenance

Audit

Lineage

Reproducibility
```

ne doivent pas être fusionnés dans un unique JSON générique.

---

# 60. `ProvenanceRef`

```text
ProvenanceRef
|
+-- source_type
+-- source_id
+-- source_version?
+-- source_location?
+-- source_record_id?
+-- source_line?
+-- checksum?
+-- metadata
```

---

# 61. `ObjectRef`

Référence générique interne :

```text
ObjectRef
|
+-- object_type
+-- object_id
+-- version?
```

---

# 62. `LineageEdge`

```text
LineageEdge
|
+-- from_ref
+-- to_ref
+-- transformation_type
+-- transformation_id?
+-- policy_trace_id?
+-- created_at
```

---

# 63. Lineage graph conceptuel

```text
Source File
    |
    v
Raw Record
    |
    v
Normalized Record
    |
    v
Company Account Mapping
    |
    v
JournalEntryLine
    |
    v
Trial Balance Row
    |
    v
Statement Line
    |
    v
Financial Ratio
```

---

# 64. Chaque edge doit être explicable

Exemple :

```text
Raw FEC line
    ->
JournalLine

transformation:
    FEC_NORMALIZATION
```

---

# 65. Lineage n'implique pas stockage d'un graphe dédié en P0

P0 peut stocker :

```text
source refs

target refs

trace ids
```

dans les objets existants.

Un graph store n'est pas nécessaire.

---

# 66. `TraceContext`

Objet transversal :

```text
TraceContext
|
+-- correlation_id
+-- causation_id?
+-- request_id?
+-- actor_context?
+-- workflow_id?
+-- batch_id?
+-- source_ref?
```

---

# 67. `correlation_id`

Relie plusieurs opérations appartenant au même workflow.

Exemple :

```text
FEC upload

parse

mapping

import

controls
```

---

# 68. `causation_id`

Relie :

```text
event B
caused by
event A
```

---

# 69. `request_id`

Permet la corrélation technique avec :

```text
HTTP

worker

CLI

job
```

---

# 70. Actor Context

```text
ActorContext
|
+-- actor_id?
+-- actor_type
+-- display_ref?
+-- delegated_by?
+-- authentication_context?
```

---

# 71. `ActorType`

```text
USER

SYSTEM

SERVICE

IMPORT

SCHEDULED_JOB

MIGRATION

UNKNOWN
```

---

# 72. Ne pas exiger un utilisateur humain

Des écritures peuvent être créées par :

```text
workflow engine

API integration

scheduled closing

migration
```

---

# 73. Audit Trail

Le modèle central :

```text
AuditEvent
```

est append-only.

---

# 74. `AuditEvent`

```text
AuditEvent
|
+-- audit_event_id
+-- event_type
+-- occurred_at
+-- actor_context
+-- accounting_entity_id?
+-- object_ref
+-- action
+-- before?
+-- after?
+-- reason?
+-- source_ref?
+-- correlation_id
+-- causation_id?
+-- request_id?
+-- metadata
+-- integrity_hash?
```

---

# 75. Append-only

Interdit :

```text
UPDATE audit event

DELETE audit event
```

via API métier ordinaire.

---

# 76. Correction d'un AuditEvent

Si une erreur de metadata doit être corrigée :

```text
new AuditCorrectionEvent
```

référencant l'événement initial.

---

# 77. Before / After

Les mutations pertinentes peuvent conserver :

```text
before

after
```

---

# 78. Attention aux snapshots complets

Ne pas stocker systématiquement :

```text
full entity before
full entity after
```

si cela :

```text
duplique des données sensibles

augmente fortement le volume

crée un risque de confidentialité
```

---

# 79. Diff minimal

Préférer lorsque possible :

```text
changed_fields
```

---

# 80. `AuditChangeSet`

```text
AuditChangeSet
|
+-- fields
+-- previous_values
+-- new_values
```

---

# 81. Audit actions P0

```text
ENTRY_CREATE

ENTRY_VALIDATE

ENTRY_POST

ENTRY_REVERSE

ACCOUNT_CREATE

ACCOUNT_UPDATE

ACCOUNT_DEACTIVATE

REFERENCE_BIND

POLICY_SET_ACTIVATE

CONTROL_RUN_START

CONTROL_RUN_COMPLETE

PERIOD_CLOSE

PERIOD_REOPEN

FEC_UPLOAD

FEC_PARSE

FEC_IMPORT

REGULATORY_MAPPING_UPDATE

REGULATORY_EXPORT_CREATE
```

---

# 82. DomainEvent vs AuditEvent

Exemple :

```text
JournalEntryPosted
    = DomainEvent

ENTRY_POST
    = AuditEvent
```

---

# 83. DomainEvent

But :

```text
réagir à un fait métier
```

---

# 84. AuditEvent

But :

```text
constituer une preuve durable de mutation / décision
```

---

# 85. Un DomainEvent peut générer un AuditEvent

Mais les deux modèles restent distincts.

---

# 86. AuditEvent != log applicatif

Log :

```text
debug / operations / observability
```

Audit :

```text
business evidence / accountability
```

---

# 87. AuditEvent != ControlResult

Un `ControlResult` dit :

```text
le contrôle a échoué
```

L'`AuditEvent` dit :

```text
le ControlRun a été lancé / terminé par tel acteur
```

---

# 88. Audit Query

```python
class AuditQuery(Protocol):
    def search(
        self,
        request: AuditSearchRequest,
    ) -> AuditPage:
        ...
```

---

# 89. Filtres

```text
entity

actor

action

object_type

object_id

date range

correlation_id

request_id
```

---

# 90. Pagination

L'audit est potentiellement massif.

La pagination serveur est obligatoire dans les adapters de production.

---

# 91. Ordering

Ordre déterministe :

```text
occurred_at

audit_sequence

audit_event_id
```

---

# 92. `AuditSequence`

Une séquence durable peut faciliter :

```text
ordering

incremental export

integrity checks
```

---

# 93. Integrity hash

Option de durcissement :

```text
AuditEvent.integrity_hash
```

---

# 94. Hash chain future

Extension :

```text
event_n.hash =
hash(
    event_n_payload
    +
    event_n-1.hash
)
```

---

# 95. Hash chain n'est pas requise P0

Elle est utile si l'on veut renforcer la détection de modification.

Mais elle introduit :

```text
complexité de sharding

ordering global

migration
```

---

# 96. Recommandation P0

P0 :

```text
append-only repository

immutable event model

database constraints

artifact checksums where useful
```

Hash chain :

```text
P1 / optional hardening
```

---

# 97. Checksums

Le framework utilise les checksums pour :

```text
source file identity

reference artifact identity

snapshot identity

export integrity

control reproducibility
```

---

# 98. SHA-256

Algorithme recommandé initialement :

```text
SHA-256
```

---

# 99. Hash != semantic equivalence

Deux fichiers de hash différents peuvent représenter les mêmes données.

Deux objets de hash identiques prouvent uniquement l'identité des bytes / canonical payload selon le mécanisme choisi.

---

# 100. Canonical serialization

Pour hash d'objet logique :

```text
stable key ordering

stable number representation

stable dates

explicit excluded volatile fields
```

---

# 101. `CanonicalHasher`

Port / service :

```python
class CanonicalHasher(Protocol):
    def hash(self, payload: object) -> str:
        ...
```

---

# 102. `ArtifactChecksum`

```text
ArtifactChecksum
|
+-- algorithm
+-- value
+-- canonicalization_version?
```

---

# 103. Checksum version

Si le canonical JSON change :

```text
canonicalization_version
```

doit changer.

---

# 104. Source Snapshot

```text
SourceSnapshot
|
+-- snapshot_id
+-- source_type
+-- source_version
+-- captured_at
+-- artifact_refs
+-- checksums
```

---

# 105. Reference Snapshot

Déjà défini :

```text
AccountingReferenceSnapshot
```

---

# 106. Policy Snapshot

Déjà défini :

```text
AccountingPolicySet version
```

ou :

```text
PolicyExecutionTrace
```

---

# 107. Projection Snapshot

Exemples :

```text
TrialBalanceSnapshot

ReportSnapshot
```

---

# 108. `ExecutionSnapshot`

Objet générique optionnel :

```text
ExecutionSnapshot
|
+-- code_version
+-- policy_snapshot
+-- reference_snapshot
+-- source_snapshots
+-- external_observations
+-- parameters
+-- generated_at
+-- checksum
```

---

# 109. Reproductibilité

Pour reproduire un calcul :

```text
same canonical inputs

same reference snapshot

same policy versions

same algorithm version

same external observations
```

doivent être disponibles.

---

# 110. Code version

Un run important doit pouvoir conserver :

```text
library version

application version

git commit?
```

sans rendre le domaine dépendant de Git.

---

# 111. `RuntimeVersionProvider`

Port :

```python
class RuntimeVersionProvider(Protocol):
    def get_version(self) -> RuntimeVersion:
        ...
```

---

# 112. `RuntimeVersion`

```text
RuntimeVersion
|
+-- package_version
+-- build_id?
+-- commit?
```

---

# 113. Reproducibility envelope

```text
ReproducibilityEnvelope
|
+-- runtime_version
+-- reference_snapshot_id
+-- policy_set_version
+-- input_snapshots
+-- control_definition_versions?
+-- mapping_versions?
+-- external_observations
+-- calculation_parameters
+-- output_checksum
```

---

# 114. Scope de reproductibilité

Tous les objets n'ont pas besoin du même niveau.

Niveaux proposés :

```text
NONE

BASIC

AUDITABLE

FULL_REPLAY
```

---

# 115. BASIC

Conserve :

```text
source refs

policy version

runtime version
```

---

# 116. AUDITABLE

Ajoute :

```text
reference snapshot

mapping versions

checksums

control run refs
```

---

# 117. FULL_REPLAY

Ajoute :

```text
captured external observations

full normalized inputs or immutable refs

deterministic parameters
```

---

# 118. `ReproducibilityLevel`

La policy détermine le niveau requis selon le cas.

---

# 119. Exemple import FEC

```text
Source file checksum

raw line hash

normalized key

mapping version

JournalEntry.source_reference

JournalLine.source_line_number
```

permettent un lineage source -> accounting.

---

# 120. Exemple Policy measurement

```text
source subject

measurement inputs

policy version

external valuation

MeasurementResult

PolicyExecutionTrace
```

---

# 121. Exemple Financial Statement

```text
TrialBalanceSnapshot

StatementMappingVersion

ReferenceReportingModel version

StatementDefinition version

ReportSnapshot

output checksum
```

---

# 122. Exemple Financial Analysis

```text
ReportSnapshot

AnalyticalDefinition version

AnalysisSnapshot

output checksum
```

---

# 123. Provenance du mapping

Un mapping doit indiquer :

```text
manual

rule-based

imported

validated candidate

actor

validation date

source evidence
```

---

# 124. Candidate mapping

Ne pas perdre :

```text
suggestion origin

confidence

reason

review status
```

même après validation.

---

# 125. `MappingProvenance`

```text
MappingProvenance
|
+-- method
+-- candidate_id?
+-- rule_id?
+-- source_ref?
+-- validated_by?
+-- validated_at?
```

---

# 126. Data lineage pour import

```text
External file
    |
    v
RawImportRecord
    |
    v
NormalizedImportRecord
    |
    v
Account / Journal Mapping
    |
    v
JournalEntry
    |
    v
JournalLine
```

---

# 127. Source preservation

Lorsque l'adapter le permet :

```text
raw data is preserved
```

au moins jusqu'à la durée de rétention définie.

---

# 128. Reprocessing

Le pipeline doit permettre :

```text
reparse from raw

renormalize with new adapter version

compare results
```

sans altérer le run initial.

---

# 129. `ProcessingRun`

Concept générique :

```text
ProcessingRun
|
+-- run_id
+-- process_type
+-- input_snapshot
+-- algorithm_version
+-- output_refs
+-- trace
```

---

# 130. Provenance réglementaire

`AccountingReferenceData` conserve déjà :

```text
source document

page / heading refs

provenance type

review status
```

Les consommateurs doivent conserver le `ReferenceSnapshot` correspondant.

---

# 131. Provenance doctrinale

Les ouvrages doctrinaux :

```text
ne sont pas une source runtime réglementaire
```

Ils servent :

```text
spécification

golden scenarios

terminologie

tests conceptuels
```

---

# 132. Contrôles réglementaires

Un contrôle peut être déclaré :

```text
REGULATORY_RULE-based
```

avec :

```text
standard_id

edition

reference_snapshot

control_version
```

---

# 133. Contrôle générique vs réglementaire

```text
ENTRY_BALANCED
    generic

REGULATORY_STATEMENT_LINE_REQUIRED
    standard-specific
```

---

# 134. `RegulatoryControlDefinition`

Extension possible :

```text
RegulatoryControlDefinition
|
+-- standard_id
+-- edition
+-- source_reference
+-- executable_status
```

---

# 135. Candidate regulatory control

Si une règle réglementaire est :

```text
human_validation_required
```

elle ne devient pas contrôle automatique bloquant par défaut.

---

# 136. Evidence strength

Option :

```text
EvidenceStrength
```

---

# 137. Valeurs

```text
DIRECT_SOURCE

DERIVED

HUMAN_ASSERTED

HEURISTIC

EXTERNAL
```

---

# 138. Ne pas confondre confidence et validation

```text
confidence = 0.99
```

ne signifie pas :

```text
validated = true
```

---

# 139. `EvidenceValidationStatus`

```text
UNREVIEWED

VALIDATED

REJECTED

SUPERSEDED
```

---

# 140. Manual sign-off

Certains workflows nécessitent une validation humaine.

---

# 141. `SignOff`

```text
SignOff
|
+-- signoff_id
+-- object_ref
+-- signoff_type
+-- actor
+-- decision
+-- reason?
+-- signed_at
+-- evidence_refs
```

---

# 142. `SignOffDecision`

```text
APPROVED

REJECTED

ACKNOWLEDGED
```

---

# 143. SignOff != authorization

Le framework stocke le fait qu'une validation a eu lieu.

L'application décide :

```text
qui a le droit de signer
```

---

# 144. Closing sign-off

Le futur close package peut exiger :

```text
reviewer sign-off

approver sign-off
```

comme `PROCESS_REQUIREMENT`.

---

# 145. Control override

Un résultat `FAIL` non bloquant peut être accepté.

Un `FAIL` bloquant peut éventuellement être waived si la policy autorise un override.

---

# 146. `ControlOverride`

```text
ControlOverride
|
+-- control_result_ref
+-- decision
+-- reason
+-- actor
+-- approved_at
+-- policy_ref
+-- evidence_refs
```

---

# 147. Override immuable

L'override est append-only.

---

# 148. Interdit par défaut

Pour certains invariants critiques :

```text
ENTRY_BALANCED
```

un override ne peut pas rendre une écriture déséquilibrée postable.

---

# 149. Distinction essentielle

```text
ControlOverride
```

peut agir sur :

```text
workflow gating
```

mais pas sur :

```text
universal domain invariant
```

---

# 150. Control remediation

Un finding peut référencer :

```text
recommended remediation
```

mais le Control Engine n'applique pas automatiquement la correction.

---

# 151. `RemediationHint`

```text
RemediationHint
|
+-- code
+-- description
+-- target_object_refs
```

---

# 152. Automated remediation future

Si implémentée, elle doit être un command explicite avec audit.

---

# 153. Control ownership

Une définition peut porter :

```text
owner_role

review_frequency
```

mais ces champs sont metadata organisationnelles.

---

# 154. Scheduled controls

Une application peut exécuter :

```text
hourly

daily

month-end
```

via scheduler externe.

Le domaine ne contient pas de scheduler.

---

# 155. Incremental controls

Certains contrôles peuvent être incrémentaux.

Exemple :

```text
new posted entries since posting_sequence X
```

---

# 156. `ControlWatermark`

```text
ControlWatermark
|
+-- control_code
+-- entity_id
+-- last_sequence
+-- last_run_id
```

---

# 157. Full vs incremental

Un contrôle doit déclarer :

```text
supports_incremental
```

---

# 158. P0

Le P0 peut privilégier :

```text
full evaluation
```

pour simplicité.

---

# 159. Control dependencies

Un contrôle peut dépendre :

```text
TrialBalance

FinancialStatements

CashFlow

Mappings

ReferenceSnapshot
```

---

# 160. `ControlDependency`

```text
ControlDependency
|
+-- dependency_type
+-- required_freshness
+-- required_version?
```

---

# 161. Stale input

Si un contrôle requiert une balance à jour et reçoit un snapshot stale :

```text
INDETERMINATE
```

ou :

```text
ERROR
```

selon policy.

---

# 162. Freshness

```text
CURRENT

STALE

SUPERSEDED

UNKNOWN
```

---

# 163. Control scope

```text
AccountingControlScope
|
+-- entity_id
+-- fiscal_year_id?
+-- period_id?
+-- date_range?
+-- journal_ids?
+-- account_ids?
+-- entry_types?
+-- source_types?
+-- dimensions?
```

---

# 164. Aucun scope global implicite

L'entité comptable est obligatoire.

---

# 165. Multi-entité

Un contrôle cross-entity appartient plutôt à :

```text
Consolidation

Group Controls
```

hors P0.

---

# 166. Control metrics

Exemples :

```text
checked_objects

failed_objects

warning_objects

difference_amount

coverage_ratio
```

---

# 167. `ControlMetric`

```text
ControlMetric
|
+-- name
+-- value
+-- unit?
```

---

# 168. Ratio de couverture

Un contrôle de mapping peut exposer :

```text
mapped_accounts / relevant_accounts
```

mais ne doit pas confondre couverture et exactitude.

---

# 169. Contrôles de provenance

Exemples :

```text
SOURCE_REFERENCE_PRESENT

POLICY_TRACE_PRESENT

REFERENCE_SNAPSHOT_PRESENT

EXPORT_CHECKSUM_PRESENT

AUDIT_ACTOR_PRESENT
```

---

# 170. Contrôles de reproductibilité

Exemples :

```text
REPRODUCIBILITY_ENVELOPE_COMPLETE

EXTERNAL_OBSERVATIONS_CAPTURED

MAPPING_VERSION_PINNED
```

---

# 171. Contrôles de lineage

Exemple :

```text
UNTRACEABLE_REPORT_LINE
```

si une ligne de reporting ne peut pas être reliée à sa source.

---

# 172. Drill-down requirement

Toute donnée comptable dérivée significative doit idéalement permettre :

```text
result
    ->
source accounting objects
```

---

# 173. Contrôle de drill-down

```text
REPORT_LINE_DRILLDOWN_COMPLETE
```

peut vérifier cette capacité dans les golden tests.

---

# 174. Audit repository

```python
class AuditRepository(Protocol):
    def append(
        self,
        event: AuditEvent,
    ) -> None:
        ...

    def get(
        self,
        audit_event_id: AuditEventId,
    ) -> AuditEvent:
        ...
```

Pas de :

```text
update()

delete()
```

dans le port métier.

---

# 175. ControlRun repository

```python
class ControlRunRepository(Protocol):
    def save(self, run: ControlRun) -> None:
        ...

    def get(self, run_id: ControlRunId) -> ControlRun:
        ...
```

---

# 176. Evidence repository

P0 peut utiliser des refs vers les objets existants.

Un `EvidenceRepository` dédié n'est nécessaire que pour les artefacts externes.

---

# 177. `ArtifactStorePort`

```python
class ArtifactStorePort(Protocol):
    def put(self, artifact) -> ArtifactRef:
        ...

    def get(self, artifact_ref) -> bytes:
        ...
```

---

# 178. Artifact immutability

Un artefact référencé par checksum doit être immutable ou versionné.

---

# 179. AuditPort

Pour simplifier l'Application Layer :

```python
class AuditPort(Protocol):
    def record(
        self,
        event: AuditEvent,
    ) -> None:
        ...
```

---

# 180. TracePort

Optionnel :

```python
class TracePort(Protocol):
    def record_lineage(
        self,
        edge: LineageEdge,
    ) -> None:
        ...
```

---

# 181. Domain API

Le domaine ne doit pas appeler directement un logger technique pour constituer l'audit.

---

# 182. Application orchestration

Exemple posting :

```text
load entry

validate

post

save entry

record AuditEvent

persist DomainEvent / outbox

commit
```

---

# 183. Atomic audit

Pour les mutations critiques :

```text
business mutation
+
audit record
```

doivent idéalement être transactionnels.

---

# 184. Transactional Outbox

Si l'audit est externe :

```text
business DB
+
outbox
```

peut garantir la diffusion.

---

# 185. P0 recommandé

Si possible :

```text
audit table in same transactional store
```

avec publication éventuelle après commit.

---

# 186. Audit failure

Pour une mutation comptable critique :

```text
cannot persist audit
```

doit généralement :

```text
rollback mutation
```

---

# 187. Audit policy

Ce comportement peut être configurable pour les actions non critiques.

---

# 188. Logging failure != Audit failure

Un échec de log opérationnel ne doit pas toujours bloquer le posting.

---

# 189. Privacy

L'audit ne doit pas devenir un stockage incontrôlé de données sensibles.

---

# 190. Principes privacy

```text
data minimization

purpose limitation

retention policy

pseudonymization where appropriate

access control outside domain
```

---

# 191. PII in before/after

Eviter de copier :

```text
full third-party objects
```

si seuls :

```text
IDs / changed fields
```

suffisent.

---

# 192. Secrets

Interdit dans audit metadata :

```text
password

token

API key

full credential
```

---

# 193. Retention

La durée de conservation dépend :

```text
jurisdiction

company policy

artifact type

audit requirements
```

---

# 194. `RetentionPolicy`

Peut exister dans l'application / compliance layer.

Le core expose les catégories.

---

# 195. Immutabilité logique vs droit à l'effacement

Si certaines données personnelles doivent être supprimées :

```text
redaction / pseudonymization
```

doit préserver autant que possible l'intégrité comptable.

Ce sujet est hors P0 détaillé.

---

# 196. `AuditRedactionEvent`

Extension future :

```text
records that specific sensitive fields were redacted
```

sans supprimer l'historique de l'action.

---

# 197. Access control

Le domaine n'implémente pas :

```text
auditor can read audit
accountant cannot delete audit
```

Cette responsabilité appartient à l'application.

---

# 198. Security boundary

L'architecture doit néanmoins permettre :

```text
read-only audit roles
organization scoping
```

dans les adapters.

---

# 199. Export audit

Une application peut produire :

```text
AuditExport
```

pour inspection externe.

---

# 200. `AuditExport`

```text
AuditExport
|
+-- scope
+-- generated_at
+-- format
+-- artifact_ref
+-- checksum
+-- export_audit_event_id
```

---

# 201. Control report

Même principe :

```text
ControlReport
```

---

# 202. Control dashboard

Un dashboard est une projection sur les `ControlRun`.

Il ne modifie pas les résultats.

---

# 203. `ControlSummaryQuery`

```text
latest status by control

failed controls

blocking controls

trend

coverage
```

---

# 204. Latest != historical truth

Le dernier PASS ne remplace pas les runs précédents.

---

# 205. History

```text
ControlHistoryQuery
```

doit permettre :

```text
FAIL -> FAIL -> PASS
```

---

# 206. Control finding resolution

Un finding peut être relié à :

```text
resolution object

new entry

mapping change

new control run
```

---

# 207. `FindingResolution`

```text
FindingResolution
|
+-- finding_ref
+-- resolution_type
+-- object_refs
+-- resolved_by
+-- resolved_at
+-- notes?
```

---

# 208. Finding status

```text
OPEN

ACKNOWLEDGED

RESOLVED

ACCEPTED_RISK

SUPERSEDED
```

---

# 209. Accepted risk

Doit être explicitement audité.

---

# 210. Accepted risk != PASS

Le control result reste :

```text
FAIL
```

ou :

```text
WARNING
```

Le workflow peut être autorisé par une décision séparée.

---

# 211. Import Controls

P0 peut intégrer les contrôles observés dans CFA FRA :

```text
FEC_REQUIRED_COLUMNS

FEC_MISSING_JOURNAL_CODE

FEC_MISSING_ENTRY_NUMBER

FEC_MISSING_ACCOUNT_NUMBER

FEC_INVALID_ENTRY_DATE

FEC_DATE_OUTSIDE_FISCAL_YEAR

FEC_INVALID_DEBIT

FEC_INVALID_CREDIT

FEC_DEBIT_AND_CREDIT

FEC_ZERO_LINE

FEC_NEGATIVE_AMOUNT

FEC_UNBALANCED_ENTRY

FEC_GLOBAL_UNBALANCED
```

---

# 212. Warnings import

Exemples :

```text
FEC_DUPLICATE_LINE

FEC_INVALID_CURRENCY_AMOUNT
```

Le caractère warning/blocage reste défini par l'adapter de format.

---

# 213. Generic import controls

Le core générique peut définir :

```text
IMPORT_REQUIRED_FIELD

IMPORT_INVALID_DATE

IMPORT_UNKNOWN_ACCOUNT

IMPORT_UNBALANCED_ENTRY
```

Le FEC adapter mappe ses règles format-spécifiques vers ce moteur.

---

# 214. FEC rules stay adapter-level

`FEC_*` ne deviennent pas des règles du domaine universel.

---

# 215. Accounting Controls P0

Catalogue initial :

```text
ENTRY_BALANCED

ENTRY_HAS_MINIMUM_LINES

ACCOUNT_EXISTS

ACCOUNT_ACTIVE

ACCOUNT_POSTABLE

PERIOD_OPEN_FOR_POSTING

TRIAL_BALANCE_BALANCED

NO_UNAUTHORIZED_CLOSED_PERIOD_ENTRY

TEMPORARY_ACCOUNTS_CLOSED
```

---

# 216. Reporting Controls P0

```text
BALANCE_SHEET_BALANCED

CASHFLOW_RECONCILED

REQUIRED_STATEMENT_LINE_PRESENT

STATEMENT_MAPPING_VALID
```

---

# 217. Provenance Controls P0

```text
SOURCE_REFERENCE_PRESENT

POSTED_ENTRY_AUDIT_PRESENT

REFERENCE_SNAPSHOT_PINNED

POLICY_TRACE_PRESENT

EXPORT_CHECKSUM_PRESENT
```

---

# 218. Closing Controls P0

```text
NO_BLOCKING_CONTROL_FAILURE

NO_RELEVANT_DRAFT_ENTRIES

REQUIRED_ADJUSTMENT_RUNS_COMPLETED

TRIAL_BALANCE_BALANCED

TEMPORARY_ACCOUNTS_CLOSED
```

---

# 219. Controls peuvent partager un evaluator

Exemple :

```text
balance equation evaluator
```

avec paramètres différents.

---

# 220. Definition-driven evaluator

```text
ControlDefinition
    ->
evaluator_id
    ->
ControlEvaluatorRegistry
```

---

# 221. `ControlEvaluatorRegistry`

```text
register evaluator

resolve evaluator by id/version
```

---

# 222. Plugins

Des adapters / packages peuvent ajouter :

```text
custom evaluators
```

sans modifier le core.

---

# 223. Dynamic code execution

Ne jamais charger du code arbitraire non fiable depuis un dataset.

---

# 224. Declarative controls

Les contrôles simples peuvent être déclaratifs.

Exemple :

```text
left expression

operator

right expression
```

---

# 225. DSL limité

Exemples adaptés :

```text
equality

threshold

required field

coverage ratio

sum comparison
```

---

# 226. Complex evaluator

Pour :

```text
cash-flow reconciliation

mapping completeness

cross-period controls
```

préférer un evaluator Python dédié.

---

# 227. Control parameters

```text
ControlParameters
```

sont versionnés avec la définition ou policy.

---

# 228. Threshold controls

Exemple :

```text
difference <= tolerance
```

---

# 229. Decimal tolerance

Les tolérances monétaires utilisent :

```text
Decimal
```

---

# 230. Tolérance != partie double posting

Une écriture postée peut exiger :

```text
strict equality
```

alors qu'un reporting arrondi peut utiliser :

```text
tolerance
```

---

# 231. Currency

Un contrôle doit expliciter :

```text
currency

rounding

scale
```

si pertinent.

---

# 232. `ControlCalculationContext`

Peut inclure :

```text
functional_currency

reporting_currency

rounding_policy
```

---

# 233. Reproducible controls

Chaque ControlRun doit pouvoir figer :

```text
definition versions

input snapshot refs

policy versions

reference snapshot

runtime version
```

au niveau requis.

---

# 234. Control checksum

Le checksum du résultat peut couvrir :

```text
canonical control results
```

hors timestamps volatils.

---

# 235. Replay

Commande future :

```text
ReplayControlRun
```

---

# 236. Replay types

```text
EXACT

CURRENT_ENGINE_COMPARISON
```

---

# 237. EXACT

Utilise :

```text
captured versions / inputs
```

---

# 238. CURRENT_ENGINE_COMPARISON

Rejoue les mêmes inputs avec :

```text
current code / policy
```

et compare.

---

# 239. Regression testing

Ce second mode est utile pour :

```text
non-regression

migration

release qualification
```

---

# 240. `ReplayComparison`

```text
ReplayComparison
|
+-- original_result
+-- replay_result
+-- differences
+-- compatible
```

---

# 241. Golden dataset CFA FRA

Le classeur / MVP peut rester :

```text
functional oracle

golden dataset

comparison support
```

pour les contrôles du moteur.

---

# 242. Golden tests

Exemples :

```text
unbalanced entry -> FAIL

balanced trial balance -> PASS

cashflow mismatch -> FAIL

draft remaining at close -> blocking

reversal keeps audit trace

FEC raw line -> JournalLine lineage preserved
```

---

# 243. Property-based controls

Exemple :

```text
for every posted entry:
    ENTRY_BALANCED == PASS
```

---

# 244. Property-based audit

```text
for every critical mutation:
    corresponding AuditEvent exists
```

dans les integration tests.

---

# 245. Property-based lineage

```text
for every imported JournalLine:
    source line ref exists
```

si l'import adapter promet cette capability.

---

# 246. Snapshot consistency

```text
output checksum
```

doit être stable pour inputs canoniques identiques.

---

# 247. Control contract tests

Tous les evaluators doivent respecter :

```text
no mutation

deterministic when declared deterministic

explicit INDETERMINATE on missing required input

stable result schema
```

---

# 248. Audit contract tests

Tous les adapters doivent respecter :

```text
append-only

entity scope

stable ordering

immutable event payload
```

---

# 249. Artifact contract tests

```text
put -> get returns identical bytes

checksum matches

immutable ref cannot be overwritten
```

---

# 250. Multi-tenant / multi-entity isolation

Toutes les queries d'audit et contrôle sont scopées.

---

# 251. Required scope

```text
AccountingEntityId
```

sauf certains événements techniques globaux explicitement classés.

---

# 252. Cross-entity audit

Réservé à un service d'administration / platform audit hors du domaine comptable principal.

---

# 253. Object identity

Les refs doivent distinguer :

```text
JournalEntryId

CompanyAccountId

ReferenceAccountId

PolicyId

ControlRunId

AuditEventId

ArtifactRef
```

---

# 254. IDs réglementaires

Les `ReferenceAccountId` externes sont conservés tels quels.

---

# 255. Avoid generic string refs everywhere

Le public API doit fournir des Value Objects lorsque possible.

---

# 256. Search indexing

Adapter peut indexer :

```text
control_code

status

severity

entity_id

period_id

object_ref

audit action

actor_id

date
```

---

# 257. Control result volume

Un ControlRun massif peut avoir :

```text
millions de findings
```

---

# 258. P0 strategy

Stocker :

```text
summary in ControlRun

findings as separate records / pages
```

si volume élevé.

---

# 259. `ControlFindingRepository`

Port optionnel :

```python
class ControlFindingRepository(Protocol):
    def append_many(...):
        ...

    def page(...):
        ...
```

---

# 260. Audit volume

Même approche :

```text
append

indexed query

pagination
```

---

# 261. Archiving

Les adapters peuvent archiver :

```text
old audit partitions

large evidence files
```

sans changer les IDs logiques.

---

# 262. Observability

Metrics :

```text
control_runs_total

control_failures_total

blocking_control_failures_total

control_duration

audit_events_total

audit_persist_failures_total

lineage_edges_total

replay_failures_total
```

---

# 263. Logs

Les logs techniques peuvent inclure :

```text
control_run_id

control_code

audit_event_id

correlation_id
```

sans dupliquer les evidence payloads.

---

# 264. Tracing

Spans :

```text
run_control_set

evaluate_control

persist_control_run

record_audit_event

build_reproducibility_envelope

replay_control_run
```

---

# 265. Alerting

La plateforme peut alerter sur :

```text
critical blocking control fail

audit persistence failure

checksum mismatch

unexpected lineage gap
```

hors domaine.

---

# 266. `AuditIntegrityControl`

Contrôle système possible :

```text
AUDIT_SEQUENCE_GAP

AUDIT_HASH_MISMATCH
```

si le hardening est activé.

---

# 267. `ArtifactIntegrityControl`

```text
ARTIFACT_CHECKSUM_MISMATCH
```

---

# 268. Checksum mismatch

Toujours :

```text
CRITICAL
```

pour un artefact déclaré immutable, sauf contexte de migration explicitement contrôlé.

---

# 269. Control execution errors

Si l'evaluator lève une exception :

```text
ControlStatus.ERROR
```

Le moteur ne transforme pas cela en PASS.

---

# 270. Timeout

Un evaluator externe peut produire :

```text
INDETERMINATE
```

avec reason :

```text
DEPENDENCY_TIMEOUT
```

---

# 271. External control provider

Port futur :

```text
ExternalControlProvider
```

pour des contrôles opérés par un service externe.

---

# 272. Trust boundary

Le résultat externe conserve :

```text
provider

provider version

request

response ref

checksum
```

---

# 273. Manual control

Certains contrôles ne sont pas automatisables.

---

# 274. `ManualControlResult`

```text
ManualControlResult
|
+-- control_code
+-- decision
+-- actor
+-- evidence
+-- reason
+-- signed_at
```

---

# 275. Manual != unverifiable

Il doit toujours avoir :

```text
actor

date

evidence

scope
```

---

# 276. Checklist

Les checklists de close peuvent être projetées comme :

```text
PROCESS controls
```

ou modèle séparé.

Recommandation :

```text
séparer checklist process
et accounting controls
```

tout en permettant un gate commun.

---

# 277. `ProcessCheck`

```text
ProcessCheck
|
+-- code
+-- completed
+-- evidence
+-- actor
```

---

# 278. Gate composition

```text
Accounting Controls

+

Process Checks

+

SignOffs

=

Workflow Gate Decision
```

---

# 279. Regulatory export gate

Avant export :

```text
required mappings valid

required lines present

balance equation valid

snapshot current

reference snapshot pinned
```

---

# 280. Reference activation gate

Avant activation d'un nouveau dataset :

```text
schema valid

checksums valid

negative constraints respected

human-review flags respected
```

---

# 281. Policy activation gate

Avant activation :

```text
policy schema valid

references available

no ambiguous binding

tests / qualification status as required
```

---

# 282. Public API - controls

```python
run = accounting.controls.run(
    entity_id=entity_id,
    control_set="YEAR_END",
    scope=scope,
)
```

---

# 283. Public API - gate

```python
decision = accounting.controls.evaluate_gate(
    gate="CLOSING_GATE",
    control_run_id=run.id,
)
```

---

# 284. Public API - audit

```python
events = accounting.audit.search(
    entity_id=entity_id,
    action="ENTRY_POST",
)
```

---

# 285. Public API - lineage

```python
lineage = accounting.trace.lineage(
    object_ref=ObjectRef(
        "JournalLine",
        line_id,
    ),
)
```

---

# 286. Public API - provenance

```python
provenance = accounting.trace.provenance(
    object_ref=...
)
```

---

# 287. Public API - reproducibility

```python
envelope = accounting.trace.reproducibility(
    object_ref=report_snapshot_ref,
)
```

---

# 288. Package domaine

```text
src/pyaccountingkit/domain/
|
+-- controls/
|   +-- definition.py
|   +-- control_set.py
|   +-- evaluator.py
|   +-- run.py
|   +-- result.py
|   +-- finding.py
|   +-- severity.py
|   +-- gate.py
|   +-- override.py
|
+-- audit/
|   +-- event.py
|   +-- action.py
|   +-- actor.py
|   +-- change_set.py
|
+-- traceability/
    +-- provenance.py
    +-- evidence.py
    +-- lineage.py
    +-- trace_context.py
    +-- checksum.py
    +-- snapshot.py
    +-- reproducibility.py
```

---

# 289. Application package

```text
application/
|
+-- controls/
|   +-- run_control.py
|   +-- run_control_set.py
|   +-- evaluate_gate.py
|   +-- resolve_finding.py
|   +-- override_control.py
|
+-- audit/
|   +-- record_event.py
|   +-- export_audit.py
|
+-- traceability/
    +-- build_provenance.py
    +-- build_lineage.py
    +-- build_reproducibility.py
    +-- replay.py
```

---

# 290. Ports

```text
ControlRunRepository

ControlFindingRepository

AuditRepository

AuditQuery

ArtifactStorePort

RuntimeVersionProvider

CanonicalHasher

TracePort

Clock

UnitOfWork
```

---

# 291. Adapters

```text
adapters/
|
+-- controls/
|   +-- in_memory/
|   +-- sql/
|
+-- audit/
|   +-- sql/
|   +-- append_only_file/
|
+-- artifacts/
|   +-- filesystem/
|   +-- object_storage/
|
+-- tracing/
    +-- sql/
    +-- external_lineage/
```

---

# 292. InMemory

L'adapter InMemory doit servir :

```text
unit tests

property tests

golden tests
```

---

# 293. SQL

L'adapter SQL doit fournir :

```text
transactions

append constraints

indexes

pagination

entity scope
```

---

# 294. Persistence details

Les garanties précises seront détaillées dans :

```text
10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md
```

---

# 295. Transaction boundary - control run

```text
create ControlRun

evaluate

persist results

persist findings

finalize run

audit CONTROL_RUN_COMPLETE

commit
```

---

# 296. Long-running controls

Pour un run long :

```text
run header

incremental finding persistence

checkpoint

final status
```

peuvent être nécessaires.

---

# 297. Partial failure

Un ControlSet peut finir :

```text
PARTIALLY_FAILED
```

si un evaluator a échoué tandis que d'autres ont produit des résultats.

---

# 298. Gate on partial failure

Un gate ne doit pas traiter :

```text
PARTIALLY_FAILED
```

comme PASS.

---

# 299. Transaction boundary - accounting mutation + audit

```text
business aggregate update

audit append

outbox append

commit
```

---

# 300. Audit sequence race

L'adapter gère la concurrence.

Le domaine ne génère pas une séquence globale naïve en mémoire.

---

# 301. Idempotence AuditEvent

Une commande idempotente ne doit pas produire une infinité de doublons métier.

---

# 302. `AuditDeduplicationKey`

Option :

```text
command idempotency key

+

audit action
```

---

# 303. Mais pas de déduplication agressive

Deux actions identiques réellement exécutées séparément doivent produire deux événements.

---

# 304. Control run idempotence

Fingerprint possible :

```text
control set version

scope

input snapshot

policy snapshot
```

---

# 305. Reuse

Le moteur peut :

```text
reuse completed equivalent run
```

seulement si la policy le permet.

---

# 306. P0 default

Créer un nouveau run explicite.

Cela simplifie l'audit.

---

# 307. Error taxonomy

```text
ControlError
|
+-- ControlDefinitionNotFoundError
+-- ControlEvaluatorNotFoundError
+-- ControlExecutionError
+-- ControlDependencyUnavailableError
+-- ControlInputStaleError
+-- ControlRunStateError
+-- ControlGateBlockedError
+-- ControlOverrideNotAllowedError
|
+-- AuditError
|   +-- AuditPersistenceError
|   +-- AuditIntegrityError
|   +-- AuditScopeError
|
+-- ProvenanceError
|   +-- ProvenanceMissingError
|   +-- LineageBrokenError
|
+-- ArtifactIntegrityError
|   +-- ChecksumMismatchError
|
+-- ReproducibilityError
    +-- SnapshotMissingError
    +-- RuntimeVersionUnavailableError
    +-- ExternalObservationMissingError
    +-- ReplayMismatchError
```

---

# 308. Fail-closed

Les cas suivants ne doivent jamais être transformés en succès silencieux :

```text
blocking control failed

required control not evaluated

audit persistence failed for critical mutation

checksum mismatch

required source provenance missing

required reference snapshot missing

replay exact impossible when FULL_REPLAY required
```

---

# 309. Tests P0 - definitions

```text
test_control_code_is_stable

test_control_version_required

test_severity_and_blocking_are_independent

test_control_set_pins_definition_versions
```

---

# 310. Tests P0 - execution

```text
test_control_run_stores_scope

test_control_run_stores_input_snapshots

test_control_fail_creates_findings

test_missing_dependency_produces_indeterminate_or_error

test_finalized_control_result_is_immutable
```

---

# 311. Tests P0 - gate

```text
test_blocking_fail_blocks_gate

test_non_blocking_warning_allows_gate

test_required_missing_result_blocks_gate

test_override_cannot_bypass_universal_invariant
```

---

# 312. Tests P0 - audit

```text
test_audit_event_is_append_only

test_audit_event_has_actor_context

test_audit_event_has_object_ref

test_audit_search_is_entity_scoped

test_critical_mutation_rolls_back_when_audit_persistence_fails
```

---

# 313. Tests P0 - provenance

```text
test_imported_line_has_source_ref

test_reference_based_decision_has_reference_snapshot

test_policy_generated_entry_has_policy_trace

test_export_has_checksum
```

---

# 314. Tests P0 - lineage

```text
test_fec_raw_line_to_journal_line_lineage

test_trial_balance_row_drills_to_journal_lines

test_report_line_drills_to_trial_balance_source
```

---

# 315. Tests P0 - reproducibility

```text
test_same_canonical_inputs_same_checksum

test_reproducibility_envelope_pins_policy_version

test_reproducibility_envelope_pins_reference_snapshot

test_external_observation_is_captured_when_required
```

---

# 316. Golden test - unbalanced entry

Input :

```text
Dr 100

Cr 90
```

Expected :

```text
ENTRY_BALANCED = FAIL

difference = 10
```

---

# 317. Golden test - closing gate

Inputs :

```text
TRIAL_BALANCE_BALANCED = PASS

CASHFLOW_RECONCILED = FAIL

cash flow control configured blocking
```

Expected :

```text
CLOSING_GATE = BLOCKED
```

---

# 318. Golden test - non-blocking warning

```text
DUPLICATE_FEC_LINE = WARNING

blocking = false
```

Expected :

```text
import may proceed
if all mandatory controls pass
```

---

# 319. Golden test - provenance FEC

Source :

```text
file SHA-256

raw line 42

row hash

normalized key
```

Target :

```text
JournalLine
```

Expected :

```text
source lineage fully reconstructible
```

---

# 320. Golden test - audit

Posting entry E :

```text
JournalEntryPosted

+

AuditEvent ENTRY_POST
```

Expected audit :

```text
entry id

actor

timestamp

entity

correlation id
```

---

# 321. Golden test - regulatory export

Expected :

```text
reference snapshot

report snapshot

mapping version

artifact checksum

REGULATORY_EXPORT_CREATE audit
```

---

# 322. Golden test - replay

Capture :

```text
runtime v1

policy v3

reference snapshot R5

input snapshot S8
```

Replay exact :

```text
same output checksum
```

---

# 323. Property test - immutable audit

For any AuditEvent:

```text
repository exposes no update semantic
```

---

# 324. Property test - control history

For any re-run:

```text
previous ControlRun remains unchanged
```

---

# 325. Property test - lineage acyclic?

Le lineage n'est pas nécessairement un DAG universel si des corrections/reversals sont modélisées comme relations.

Ne pas imposer :

```text
global DAG
```

comme invariant.

---

# 326. Property test - correlation

Pour un workflow import :

```text
all major audit events share correlation_id
```

si adapter/application le promet.

---

# 327. Reconciliation with Logs

Logs techniques :

```text
may be ephemeral
```

Audit :

```text
durable
```

---

# 328. Reconciliation with OpenTelemetry

Traces OTel peuvent porter :

```text
correlation_id

request_id

entry_id

control_run_id
```

mais ne remplacent pas l'audit.

---

# 329. Audit externalization

Une copie vers :

```text
SIEM

data lake

compliance store
```

peut être produite par adapter/outbox.

---

# 330. Source of truth audit

PyAccountingKit doit clairement définir quel store constitue :

```text
authoritative audit store
```

pour une installation.

---

# 331. Tamper evidence

P1 peut ajouter :

```text
WORM storage

hash chain

signed manifests

external timestamping
```

---

# 332. Digital signature

Une signature cryptographique n'est pas exigée P0.

---

# 333. Signed export future

Extension :

```text
SignedArtifactManifest
```

---

# 334. `ArtifactManifest`

```text
ArtifactManifest
|
+-- artifact_ref
+-- checksum
+-- generated_at
+-- runtime_version
+-- source_snapshot_refs
```

---

# 335. Control package for close

Un closing package peut contenir :

```text
ControlRun summary

blocking findings

sign-offs

closing snapshot

checksums
```

---

# 336. `ControlEvidenceBundle`

```text
ControlEvidenceBundle
|
+-- control_run_id
+-- definitions
+-- findings
+-- evidence_refs
+-- input_snapshots
+-- runtime_version
+-- checksum
```

---

# 337. Audit evidence bundle

Même logique pour :

```text
period close

regulatory export

reference activation
```

---

# 338. API immutability

Les public methods ne doivent pas exposer :

```text
control_result.status = PASS

audit_event.action = ...
```

---

# 339. Frozen models

Utiliser lorsque pertinent :

```text
frozen dataclasses

immutable mappings

tuples
```

---

# 340. Serialization

Les objets d'audit et evidence doivent être sérialisables :

```text
JSON
```

avec schema version.

---

# 341. `AuditSchemaVersion`

```text
audit_schema_version
```

permet l'évolution.

---

# 342. `ControlResultSchemaVersion`

Même principe.

---

# 343. Schema migration

Une migration de stockage ne doit pas altérer la sémantique historique.

---

# 344. Event type renaming

Ne jamais renommer silencieusement un event type historique.

Créer :

```text
new event type
```

ou mapper au query layer.

---

# 345. Internationalization

Les codes restent stables en anglais technique.

Les messages peuvent être localisés côté application.

---

# 346. User-facing message

Ne pas utiliser le texte traduit comme clé logique.

---

# 347. Deterministic messages

Les résultats structurés doivent fournir :

```text
code

parameters
```

et le message peut être généré séparément.

---

# 348. Control output schema

Exemple :

```json
{
  "control_code": "TRIAL_BALANCE_BALANCED",
  "status": "PASS",
  "metrics": {
    "total_debit": "1000.00",
    "total_credit": "1000.00",
    "difference": "0.00"
  }
}
```

---

# 349. Decimal serialization

Toujours :

```text
string
```

ou représentation décimale canonique.

Jamais float JSON généré depuis `float`.

---

# 350. Date serialization

ISO 8601.

---

# 351. Timezone

Audit timestamps :

```text
timezone-aware
```

---

# 352. Business date vs timestamp

Conserver séparément :

```text
accounting_date

occurred_at
```

---

# 353. External event date

Une source peut avoir :

```text
source_event_date
```

distincte de l'import.

---

# 354. Provenance completeness levels

```text
NONE

PARTIAL

COMPLETE
```

---

# 355. `ProvenanceCompleteness`

Un contrôle peut calculer le niveau de couverture.

---

# 356. P0 expectation

Pour :

```text
imported JournalLine

policy-generated JournalEntry

regulatory export
```

la provenance doit être :

```text
COMPLETE
```

selon le contrat de l'adapter.

---

# 357. Audit completeness

Un contrôle système peut comparer :

```text
critical domain objects

vs

required audit actions
```

---

# 358. `AuditCompletenessControl`

Exemple :

```text
all posted entries have ENTRY_POST audit
```

---

# 359. Source-to-output trace query

```text
TraceQuery
```

doit supporter :

```text
upstream

downstream
```

---

# 360. Upstream

```text
ReportLine
    ->
JournalLines
```

---

# 361. Downstream

```text
RawImportLine
    ->
JournalLine
    ->
Reports
```

---

# 362. P0 implementation

Une première implementation peut être basée sur :

```text
explicit foreign keys / refs

source_reference

trace ids
```

sans moteur graphe.

---

# 363. Referential integrity

Lorsque même store :

```text
foreign keys
```

peuvent être utilisées.

Lorsque artifact externe :

```text
immutable ArtifactRef + checksum
```

---

# 364. Dangling evidence

Un artefact référencé mais supprimé doit être détectable.

---

# 365. `EVIDENCE_ARTIFACT_MISSING`

Control code possible.

---

# 366. Retention dependency

Une retention policy ne doit pas supprimer un artefact encore requis par un snapshot audit.

---

# 367. Legal hold future

P1 :

```text
LegalHold
```

hors P0.

---

# 368. ADRs

| ID | Décision |
|---|---|
| ADR-CTRL-001 | `CONTROL` reste distinct de `UNIVERSAL_ACCOUNTING_INVARIANT` |
| ADR-CTRL-002 | `ControlDefinition` est versionnée |
| ADR-CTRL-003 | Severity et Blocking sont deux dimensions distinctes |
| ADR-CTRL-004 | `ControlRun` est un Aggregate Root |
| ADR-CTRL-005 | Un `ControlResult` finalisé est immutable |
| ADR-CTRL-006 | Une réévaluation crée un nouveau `ControlRun` |
| ADR-CTRL-007 | `INDETERMINATE` est un statut explicite |
| ADR-CTRL-008 | Un gate décide du workflow à partir des controls |
| ADR-CTRL-009 | Un override de control ne peut pas contourner un invariant universel |
| ADR-CTRL-010 | Les FEC controls restent adapter-specific |
| ADR-AUD-001 | `AuditEvent` est append-only |
| ADR-AUD-002 | DomainEvent, AuditEvent et log technique sont distincts |
| ADR-AUD-003 | Les mutations critiques doivent produire un audit durable |
| ADR-AUD-004 | L'audit conserve ActorContext et TraceContext |
| ADR-AUD-005 | Before/After doit respecter la minimisation des données |
| ADR-AUD-006 | Le port Audit métier n'expose ni update ni delete |
| ADR-TRACE-001 | Provenance, Audit, Lineage et Reproducibility sont quatre concepts distincts |
| ADR-TRACE-002 | Les source refs sont conservées jusqu'au niveau JournalLine lorsqu'un adapter le permet |
| ADR-TRACE-003 | Les reference snapshots sont pinés pour les calculs réglementaires |
| ADR-TRACE-004 | Les policy versions sont pinées pour les calculs métier |
| ADR-TRACE-005 | SHA-256 est le checksum initial recommandé |
| ADR-TRACE-006 | Un checksum ne constitue pas une validation sémantique |
| ADR-TRACE-007 | Le canonicalization schema des hashes est versionné |
| ADR-TRACE-008 | Les outputs publiables peuvent porter un `ReproducibilityEnvelope` |
| ADR-TRACE-009 | Les external observations sont capturées lorsque FULL_REPLAY est requis |
| ADR-TRACE-010 | P0 ne nécessite pas de graph database |
| ADR-TRACE-011 | Les evidence artifacts immutables sont adressés par refs/version/checksum |
| ADR-TRACE-012 | Les snapshots historiques restent immutables |
| ADR-TRACE-013 | Les golden datasets CFA FRA servent d'oracle de non-régression |
| ADR-TRACE-014 | Les ouvrages doctrinaux ne deviennent pas des sources réglementaires runtime |
| ADR-TRACE-015 | L'audit est multi-entity scoped |
| ADR-TRACE-016 | Le hash chaining est un hardening P1, pas un prérequis P0 |

---

# 369. Critères d'acceptation P0.10

```text
[ ] ControlDefinition est spécifié

[ ] ControlCode stable est défini

[ ] control versioning est défini

[ ] ControlSeverity est défini

[ ] Blocking est distinct de Severity

[ ] ControlApplicability est défini

[ ] ControlEvaluator est défini

[ ] ControlStatus inclut PASS / FAIL / WARNING / INDETERMINATE / ERROR

[ ] ControlFinding est défini

[ ] ControlSet est défini

[ ] ControlRun est défini

[ ] ControlResult finalisé est immutable

[ ] re-run crée un nouveau ControlRun

[ ] ControlGate est défini

[ ] control override ne contourne pas universal invariant

[ ] catalogue P0 des accounting controls est défini

[ ] catalogue P0 des closing controls est défini

[ ] catalogue P0 des provenance controls est défini

[ ] AuditEvent append-only est défini

[ ] ActorContext est défini

[ ] TraceContext est défini

[ ] before/after est minimisé

[ ] DomainEvent != AuditEvent

[ ] AuditEvent != technical log

[ ] ProvenanceRef est défini

[ ] Evidence est défini

[ ] LineageEdge est défini

[ ] source -> normalized -> JournalLine lineage est possible

[ ] ArtifactChecksum est défini

[ ] SHA-256 est disponible

[ ] canonical hashing est versionné

[ ] ReproducibilityEnvelope est défini

[ ] runtime version peut être capturée

[ ] policy version est pinée

[ ] reference snapshot est piné

[ ] external observations peuvent être capturées

[ ] replay architecture est prévue

[ ] audit/control queries sont multi-entity scoped

[ ] contract tests adapters sont définis

[ ] golden tests CFA FRA sont définis
```

---

# 370. Ordre d'implémentation recommandé

## CTRL-00 - Primitives

```text
ControlCode

ControlStatus

ControlSeverity

ControlFinding

ControlScope
```

---

## CTRL-01 - Definitions

```text
ControlDefinition

ControlVersion

ControlApplicability

ControlSet
```

---

## CTRL-02 - Evaluators

```text
ControlEvaluator

ControlEvaluatorRegistry

ControlEvaluationContext
```

---

## CTRL-03 - Runs

```text
ControlRun

ControlResult

ControlRunRepository
```

---

## CTRL-04 - Gates

```text
ControlGate

ControlGateDecision

blocking policies
```

---

## CTRL-05 - Audit

```text
AuditEvent

ActorContext

AuditRepository

AuditQuery
```

---

## CTRL-06 - Provenance

```text
ProvenanceRef

Evidence

ObjectRef

source references
```

---

## CTRL-07 - Lineage

```text
LineageEdge

TraceContext

TraceQuery
```

---

## CTRL-08 - Checksums

```text
ArtifactChecksum

CanonicalHasher

SHA-256
```

---

## CTRL-09 - Reproducibility

```text
RuntimeVersion

ReproducibilityEnvelope

SourceSnapshot

ReplayComparison
```

---

## CTRL-10 - Initial Catalog

```text
ENTRY_BALANCED

TRIAL_BALANCE_BALANCED

BALANCE_SHEET_BALANCED

CASHFLOW_RECONCILED

NO_RELEVANT_DRAFT_ENTRIES

TEMPORARY_ACCOUNTS_CLOSED

SOURCE_REFERENCE_PRESENT

POLICY_TRACE_PRESENT

REFERENCE_SNAPSHOT_PINNED

EXPORT_CHECKSUM_PRESENT
```

---

# 371. Démonstrateur P0.10

Scénario recommandé :

```text
1. Create entity

2. Import source file
      source SHA-256 captured

3. Preserve raw records
      source line refs captured

4. Normalize and create accounting entries

5. Preserve:
      source -> JournalLine lineage

6. Post entries
      AuditEvent ENTRY_POST

7. Run accounting ControlSet

8. Verify:
      ENTRY_BALANCED = PASS

9. Build Trial Balance

10. Run:
      TRIAL_BALANCE_BALANCED

11. Introduce report mapping

12. Build Financial Statements

13. Run:
      BALANCE_SHEET_BALANCED
      CASHFLOW_RECONCILED

14. Create ClosingRun

15. Evaluate CLOSING_GATE

16. Persist ControlRun and findings

17. Build reproducibility envelope

18. Verify:
      source checksum
      policy version
      reference snapshot
      runtime version
      output checksum

19. Replay control from same inputs

20. Verify identical result
```

---

# 372. Démonstrateur de failure / correction

```text
ControlRun #1
    CASHFLOW_RECONCILED = FAIL

Gate:
    BLOCKED

Correction:
    reversal + corrected entry

ControlRun #2
    CASHFLOW_RECONCILED = PASS

Gate:
    ALLOWED
```

Le premier résultat n'est jamais modifié.

---

# 373. Démonstrateur d'audit

```text
ENTRY_CREATE
    |
    v
ENTRY_VALIDATE
    |
    v
ENTRY_POST
    |
    v
ENTRY_REVERSE
```

Pour le même workflow :

```text
correlation_id = constant
```

et chaque événement conserve son propre :

```text
occurred_at
actor
object_ref
```

---

# 374. Démonstrateur lineage FEC

```text
FEC file
    checksum = H1

line 42
    row_hash = H2

normalized key = K

JournalEntry = E

JournalLine = L

Trace:
    file:H1
      -> raw:42/H2
      -> normalized:K
      -> entry:E
      -> line:L
```

---

# 375. Démonstrateur export réglementaire

```text
ReferenceSnapshot R

TrialBalanceSnapshot T

StatementMappingVersion M

ReportSnapshot S

ExportArtifact A

checksum(A) = H
```

Audit :

```text
REGULATORY_EXPORT_CREATE
```

Reproducibility envelope :

```text
R + T + M + S + runtime version + H
```

---

# 376. Frontière avec Persistence / Concurrency

Le prochain document doit détailler :

```text
repository semantics

UnitOfWork

transaction boundaries

locking

optimistic concurrency

pessimistic concurrency

idempotency stores

append-only persistence

outbox

adapter contract tests
```

---

# 377. Frontière avec Testing

La stratégie globale de tests devra réutiliser :

```text
Control contract tests

Audit contract tests

Lineage contract tests

Replay tests

Golden datasets

Property-based tests
```

---

# 378. Frontière avec Reporting

Reporting produit :

```text
ReportSnapshot
```

et doit fournir :

```text
source refs

mapping version

statement definition version
```

Controls consomme ces éléments.

---

# 379. Frontière avec Financial Analysis

Financial Analysis produit :

```text
AnalysisSnapshot
```

qui doit pouvoir conserver :

```text
analytical definition version

input report snapshot

checksum

reproducibility envelope
```

---

# 380. Frontière avec Regulatory Reference

Controls peut inspecter :

```text
reference snapshot

validation status

human review flags

negative constraints
```

mais ne réécrit pas les données réglementaires.

---

# 381. Frontière avec Accounting Policies

Controls peut vérifier :

```text
policy trace present

policy version valid

applicability coherent
```

mais ne choisit pas à la place du Policy Resolution Service.

---

# 382. Frontière avec Closing

Closing consomme :

```text
ControlGateDecision
```

et non une liste codée en dur de conditions.

---

# 383. Frontière avec Imports

Imports produisent :

```text
source provenance

raw artifacts

normalized records

import-specific controls
```

qui rejoignent le modèle générique de traçabilité.

---

# 384. Risques principaux

## RISK-CTRL-001 - Tout mettre dans AuditEvent

Réponse :

```text
séparer Audit / Control / Provenance / Lineage
```

---

## RISK-CTRL-002 - Warning traité comme blocking implicitement

Réponse :

```text
severity != blocking
```

---

## RISK-CTRL-003 - Fail technique traité comme PASS

Réponse :

```text
INDETERMINATE / ERROR
```

---

## RISK-CTRL-004 - Contrôle modifié en place

Réponse :

```text
versioning + immutable runs
```

---

## RISK-AUD-001 - Audit non transactionnel

Réponse :

```text
same UoW / outbox strategy
```

---

## RISK-AUD-002 - Audit trop verbeux / sensible

Réponse :

```text
minimal change sets
```

---

## RISK-TRACE-001 - Hash présenté comme preuve comptable

Réponse :

```text
checksum only proves integrity / identity
```

---

## RISK-TRACE-002 - Reproductibilité impossible

Réponse :

```text
pin versions + snapshots + external observations
```

---

## RISK-TRACE-003 - Lineage inféré par heuristique

Réponse :

```text
explicit source refs
```

---

## RISK-TRACE-004 - Raw source supprimée trop tôt

Réponse :

```text
retention policy aware of audit dependencies
```

---

# 385. Conclusion

L'architecture de contrôle et de traçabilité de PyAccountingKit devient :

```text
ACCOUNTING OBJECTS
      |
      +-------------------+
      |                   |
      v                   v
Control Engine        Audit Trail
      |                   |
      v                   v
ControlRun           AuditEvent
      |                   |
      +---------+---------+
                |
                v
      Provenance / Evidence
                |
                v
             Lineage
                |
                v
     Reproducibility Envelope
```

Les principes structurants sont :

```text
Invariant != Control

Validation != ControlRun

Severity != Blocking

ControlResult is immutable

Re-run creates a new result

Gate != Control

AuditEvent is append-only

DomainEvent != AuditEvent

Audit != Log

Provenance != Audit

Lineage != Provenance

Checksum != Semantic Validation

Reference versions must be pinned

Policy versions must be pinned

Published outputs must be traceable

Critical computations should be reproducible
```

Le P0.10 donne ainsi au framework une propriété essentielle pour une bibliothèque comptable sérieuse :

> **Toute valeur importante doit pouvoir être reliée à son origine, à la règle qui l'a produite, au contrôle qui l'a validée et à la version exacte du contexte dans lequel elle a été calculée.**

---

**Prochain document recommandé :**

```text
10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md
```
