# 12 - PyAccountingKit - Architecture des imports comptables et de l'adapter FEC

> **Projet** : PyAccountingKit  
> **Document** : `12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`  
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
> - `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`
> - `10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`
> - `11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`
> **Statut** : P1.1 - Architecture générique d'import comptable et adapter FEC  
> **Langue** : Français  
> **Objet** : Définir l'architecture des imports comptables génériques, la conservation des sources, le parsing, la normalisation, le mapping des comptes/journaux, les validations, l'idempotence, la transactionnalité, la provenance, l'audit, ainsi que l'adapter FEC français comme format spécialisé sans contaminer le coeur de PyAccountingKit.

---

# 1. Résumé exécutif

PyAccountingKit doit supporter l'import de comptabilités existantes sans transformer le format source en modèle interne.

La chaîne cible est :

```text
External Source
    |
    v
Source Acquisition
    |
    v
Immutable Source Artifact
    |
    v
Parsing
    |
    v
Raw Import Records
    |
    v
Normalization
    |
    v
Normalized Accounting Records
    |
    +--> Account Mapping
    +--> Journal Mapping
    +--> Period Resolution
    +--> Entry Grouping
    |
    v
Import Validation
    |
    v
Import Plan
    |
    v
JournalEntry / JournalEntryLine
    |
    v
Validation / Posting
    |
    v
Audit / Lineage / Controls
```

Le FEC est traité comme :

```text
AccountingImportAdapter
    specialization = FEC
```

et non comme :

```text
la définition universelle d'un import comptable
```

Le coeur générique ne doit donc jamais dépendre de :

```text
JournalCode
EcritureNum
CompteNum
Debit
Credit
ValidDate
```

comme noms de colonnes universels.

Ces noms appartiennent à l'adapter FEC.

---

# 2. Objectifs

Le bounded context `Accounting Imports` doit permettre de :

1. ingérer un fichier ou flux comptable externe ;
2. conserver l'artefact source et son checksum ;
3. parser sans perte de provenance ;
4. conserver les lignes brutes lorsque requis ;
5. normaliser vers un modèle générique ;
6. regrouper correctement les lignes en écritures ;
7. mapper les comptes sources vers `CompanyAccount` ;
8. mapper les journaux sources vers `Journal` ;
9. résoudre les périodes ;
10. détecter les erreurs et anomalies ;
11. distinguer erreurs bloquantes et warnings ;
12. gérer l'idempotence ;
13. empêcher les doubles imports ;
14. importer par transaction ou par chunks ;
15. préserver le lineage source -> écriture ;
16. auditer chaque étape ;
17. permettre un reprocessing déterministe ;
18. permettre un adapter FEC conforme à ses règles spécifiques ;
19. permettre d'autres adapters : CSV, ERP, API, legacy, custom ;
20. réutiliser le même Accounting Core après normalisation.

---

# 3. Non-objectifs

Le bounded context Import ne doit pas :

```text
devenir un second Posting Engine

modifier directement les balances

inventer un compte cible

inventer un mapping réglementaire

déduire automatiquement la sémantique d'un code

faire de l'analyse financière

devenir spécifique à Django ou PostgreSQL

contenir les règles de clôture

coder en dur le FEC dans le domaine générique
```

---

# 4. Principe fondamental

```text
Source Format
    !=
Domain Model
```

Exemple :

```text
FEC row
    ->
NormalizedImportLine
    ->
JournalEntryLine
```

---

# 5. Deux couches d'import

PyAccountingKit sépare :

```text
Generic Accounting Import Core

Specialized Import Adapters
```

---

# 6. Generic Import Core

Le core connaît :

```text
ImportBatch

SourceArtifact

RawImportRecord

NormalizedImportRecord

MappingDecision

ImportIssue

ImportPlan

ImportExecution
```

---

# 7. Specialized Adapter

Un adapter connaît :

```text
format-specific columns

format-specific parsing

format-specific controls

format-specific canonical identifiers

format-specific warnings
```

---

# 8. Exemple adapter FEC

```text
FECAdapter
|
+-- FECParser
+-- FECNormalizer
+-- FECValidator
+-- FECGroupingStrategy
+-- FECSourceFingerprintStrategy
```

---

# 9. Bounded contexts impliqués

```text
Accounting Imports

Company Chart of Accounts

Journal & Entries

Posting & Reversal

Accounting Periods

Controls

Audit & Traceability

Persistence / UoW
```

---

# 10. `AccountingImportBatch`

Aggregate Root principal :

```text
AccountingImportBatch
|
+-- id
+-- accounting_entity_id
+-- source_type
+-- adapter_id
+-- adapter_version
+-- status
+-- source_artifact_ref
+-- source_checksum
+-- source_fingerprint
+-- fiscal_year_id?
+-- import_mode
+-- transaction_mode
+-- created_at
+-- started_at?
+-- completed_at?
+-- created_by?
+-- correlation_id
+-- metadata
```

---

# 11. `ImportBatchStatus`

```text
CREATED

ACQUIRED

PARSED

NORMALIZED

MAPPED

VALIDATED

READY

IMPORTING

COMPLETED

COMPLETED_WITH_WARNINGS

FAILED

CANCELLED
```

---

# 12. State machine

```text
CREATED
   |
   v
ACQUIRED
   |
   v
PARSED
   |
   v
NORMALIZED
   |
   v
MAPPED
   |
   v
VALIDATED
   |
   v
READY
   |
   v
IMPORTING
   |
   +--> COMPLETED
   +--> COMPLETED_WITH_WARNINGS
   +--> FAILED
```

---

# 13. Transitions interdites

```text
CREATED -> COMPLETED

PARSED -> IMPORTING

FAILED -> COMPLETED
    sans retry/restart explicite

COMPLETED -> IMPORTING
```

---

# 14. Import run != Source Artifact

Le même source artifact peut être :

```text
parsed with adapter v1

reprocessed with adapter v2
```

Les runs restent distincts.

---

# 15. `SourceArtifact`

```text
SourceArtifact
|
+-- artifact_ref
+-- source_type
+-- filename?
+-- media_type?
+-- size?
+-- checksum
+-- acquired_at
+-- immutable
+-- metadata
```

---

# 16. Checksum source

P0/P1 recommande :

```text
SHA-256
```

---

# 17. Source checksum != import identity complète

Deux imports peuvent utiliser le même fichier avec :

```text
different entity

different fiscal year

different mapping policy
```

L'idempotence doit donc avoir un scope.

---

# 18. `ImportSourceFingerprint`

```text
ImportSourceFingerprint
|
+-- checksum
+-- entity_id
+-- fiscal_year_id?
+-- adapter_id
+-- adapter_version?
+-- source_business_key?
```

---

# 19. Raw preservation

Un adapter doit déclarer :

```text
raw_record_retention
```

---

# 20. `RawImportRecord`

```text
RawImportRecord
|
+-- batch_id
+-- record_index
+-- source_line_number?
+-- source_record_id?
+-- raw_fields
+-- row_checksum?
+-- provenance
```

---

# 21. Pourquoi conserver le raw

Permet :

```text
audit

debug

reprocessing

proof of source

mapping review

regression testing
```

---

# 22. Raw immutable

Une ligne brute finalisée est immutable.

---

# 23. Correction d'une source

Une correction de fichier produit :

```text
new SourceArtifact
+
new ImportBatch
```

---

# 24. `RawImportRecordRepository`

Le stockage peut être :

```text
database

parquet

object storage

hybrid
```

derrière un port.

---

# 25. Parsing

Le parser transforme :

```text
bytes
```

en :

```text
RawImportRecord
```

sans appliquer de logique comptable de posting.

---

# 26. `AccountingImportParser`

```python
class AccountingImportParser(Protocol):
    def parse(
        self,
        artifact: SourceArtifact,
        context: "ImportParsingContext",
    ) -> "ParsedImport":
        ...
```

---

# 27. `ParsedImport`

```text
ParsedImport
|
+-- header?
+-- records
+-- parser_version
+-- warnings
+-- checksum
```

---

# 28. Parsing errors

Exemples :

```text
invalid encoding

malformed row

missing delimiter

unexpected field count

invalid quoting
```

---

# 29. Parsing != validation comptable

Un fichier peut être :

```text
syntactically valid
```

mais :

```text
accounting invalid
```

---

# 30. Normalisation

La normalisation convertit le format source en vocabulaire générique.

---

# 31. `NormalizedImportRecord`

```text
NormalizedImportRecord
|
+-- batch_id
+-- normalized_record_id
+-- source_record_ref
+-- source_entry_key
+-- source_line_key?
+-- source_journal_code?
+-- source_account_code
+-- accounting_date
+-- document_date?
+-- description?
+-- debit
+-- credit
+-- currency?
+-- auxiliary_code?
+-- dimensions
+-- metadata
```

---

# 32. Montants

Toujours :

```text
Decimal
```

Jamais float.

---

# 33. Dates

Les dates normalisées sont de vrais objets date.

---

# 34. Source entry key

Le regroupement en écriture repose sur :

```text
source_entry_key
```

---

# 35. `SourceEntryKey`

Value Object :

```text
stable within source batch
```

---

# 36. Pourquoi

Une écriture source peut comporter :

```text
2

10

100

lignes
```

Il faut reconstruire l'aggregate.

---

# 37. Grouping strategy

```python
class ImportEntryGroupingStrategy(Protocol):
    def group(
        self,
        records: tuple[NormalizedImportRecord, ...],
    ) -> tuple["NormalizedEntryGroup", ...]:
        ...
```

---

# 38. `NormalizedEntryGroup`

```text
NormalizedEntryGroup
|
+-- source_entry_key
+-- records
+-- accounting_date
+-- source_journal_code?
+-- source_description?
+-- source_document_ref?
```

---

# 39. Grouping must be deterministic

Même source + même adapter version :

```text
same groups
```

---

# 40. Mapping des comptes

Source :

```text
source_account_code
```

Cible :

```text
CompanyAccountId
```

---

# 41. `ImportAccountMapping`

```text
ImportAccountMapping
|
+-- source_system
+-- source_account_code
+-- company_account_id
+-- mapping_type
+-- status
+-- effective_from?
+-- effective_to?
+-- validated_by?
+-- provenance
```

---

# 42. Mapping types

```text
MANUAL

CONFIGURED_RULE

IMPORTED

VALIDATED_CANDIDATE
```

---

# 43. Status

```text
CANDIDATE

VALIDATED

REJECTED

SUPERSEDED
```

---

# 44. Mapping automatique par égalité

Possible uniquement si la policy l'autorise.

Exemple :

```text
source code exactly matches CompanyAccount.code
```

---

# 45. Mais égalité de code != preuve réglementaire

Le mapping :

```text
source -> CompanyAccount
```

est différent de :

```text
CompanyAccount -> ReferenceAccount
```

---

# 46. Mapping fallback interdit

Interdit :

```python
if no mapping:
    pick nearest prefix
```

dans le core.

---

# 47. Candidate mapping

Une heuristique peut proposer :

```text
candidate account
```

mais sans validation :

```text
not executable
```

---

# 48. `ImportAccountMappingService`

```python
class ImportAccountMappingService:
    def resolve(
        self,
        source_account_code: str,
        context: "ImportMappingContext",
    ) -> "ImportMappingDecision":
        ...
```

---

# 49. `ImportMappingDecision`

```text
ImportMappingDecision
|
+-- source_ref
+-- target_account_id?
+-- status
+-- method
+-- confidence?
+-- rationale
+-- evidence
```

---

# 50. Mapping fail-closed

Aucun target :

```text
UNMAPPED_ACCOUNT
```

Plusieurs targets :

```text
AMBIGUOUS_ACCOUNT_MAPPING
```

---

# 51. Mapping des journaux

Même logique :

```text
source journal code
    ->
JournalId
```

---

# 52. `ImportJournalMapping`

```text
ImportJournalMapping
|
+-- source_journal_code
+-- journal_id
+-- status
+-- mapping_type
+-- provenance
```

---

# 53. Journal auto-create

Interdit par défaut.

Un adapter peut produire :

```text
JournalCreationSuggestion
```

---

# 54. Account auto-create

Même principe.

Import ne doit pas créer silencieusement :

```text
unknown CompanyAccount
```

---

# 55. Policy d'auto-création

Si une application veut autoriser :

```text
create unknown account
```

cela doit passer par :

```text
CompanyAccountCreationPolicy
```

et `Company Chart` service.

---

# 56. Period resolution

```text
accounting_date
    ->
AccountingPeriod
```

---

# 57. `ImportPeriodResolver`

```python
class ImportPeriodResolver(Protocol):
    def resolve(
        self,
        entity_id: AccountingEntityId,
        accounting_date: date,
    ) -> AccountingPeriod:
        ...
```

---

# 58. Period not found

```text
IMPORT_PERIOD_NOT_FOUND
```

---

# 59. Closed period

Le comportement dépend de :

```text
ImportClosedPeriodPolicy
```

---

# 60. Modes

```text
REJECT

REQUIRE_SPECIAL_IMPORT_MODE

ALLOW_MIGRATION_ONLY
```

---

# 61. Import historique

Pour migration d'une comptabilité existante, une application peut autoriser l'ingestion d'écritures historiquement postées.

---

# 62. Deux modes métier

```text
NORMAL_IMPORT

TRUSTED_POSTED_HISTORY_IMPORT
```

---

# 63. `NORMAL_IMPORT`

Pipeline :

```text
JournalEntryProposal
    ->
DRAFT
    ->
VALIDATED
    ->
POSTED
```

---

# 64. `TRUSTED_POSTED_HISTORY_IMPORT`

Exception explicite :

```text
source represents already validated accounting history
```

---

# 65. Conditions

Doivent au minimum être :

```text
adapter explicitly trusted

full validation passed

source provenance preserved

period migration policy allows

audit event emitted

transaction atomic

entry still balanced

accounts resolved
```

---

# 66. Pas de bypass d'invariant

Même trusted import ne peut importer :

```text
unbalanced posted entry
```

comme donnée valide sans mode de quarantine/migration spécial.

---

# 67. Quarantine

Données invalides peuvent être :

```text
QUARANTINED
```

mais pas :

```text
POSTED
```

---

# 68. `ImportRecordDisposition`

```text
ACCEPT

WARNING

REVIEW_REQUIRED

REJECT

QUARANTINE
```

---

# 69. Validation générique

Contrôles P1 :

```text
IMPORT_REQUIRED_FIELD

IMPORT_INVALID_DATE

IMPORT_DEBIT_OR_CREDIT

IMPORT_NON_NEGATIVE_AMOUNT

IMPORT_NON_ZERO_LINE

IMPORT_UNKNOWN_ACCOUNT

IMPORT_UNKNOWN_JOURNAL

IMPORT_PERIOD_NOT_FOUND

IMPORT_ENTRY_UNBALANCED

IMPORT_DUPLICATE_SOURCE
```

---

# 70. Validation ligne vs écriture

Ligne :

```text
field validity
amount validity
account mapping
```

Ecriture :

```text
minimum lines
balance
date consistency
journal consistency
```

---

# 71. Validation batch

Batch :

```text
global debit total

global credit total

duplicate file

coverage

unmapped counts
```

---

# 72. `ImportIssue`

```text
ImportIssue
|
+-- issue_code
+-- severity
+-- blocking
+-- source_record_refs
+-- source_entry_key?
+-- message
+-- expected?
+-- actual?
+-- metadata
```

---

# 73. Severity

```text
INFO

WARNING

ERROR

CRITICAL
```

---

# 74. Blocking remains separate

Comme dans le moteur Controls :

```text
severity != blocking
```

---

# 75. `ImportValidationReport`

```text
ImportValidationReport
|
+-- batch_id
+-- valid
+-- issues
+-- total_records
+-- accepted_records
+-- rejected_records
+-- warning_records
+-- unmapped_accounts
+-- unmapped_journals
+-- total_debit
+-- total_credit
+-- difference
```

---

# 76. `ImportControlSet`

Peut utiliser le moteur de controls existant.

---

# 77. Recommandation

Les validations format-spécifiques :

```text
adapter
```

Les validations comptables génériques :

```text
Control / domain validation
```

---

# 78. `ImportPlan`

Avant mutation, construire :

```text
ImportPlan
|
+-- batch_id
+-- entry_plans
+-- account_mappings
+-- journal_mappings
+-- period_resolutions
+-- warnings
+-- expected_entry_count
+-- expected_line_count
+-- checksum
```

---

# 79. Pourquoi un ImportPlan

Permet :

```text
preview

human review

dry run

reproducibility

idempotence
```

---

# 80. Dry run

```text
parse

normalize

map

validate

build plan

NO ACCOUNTING MUTATION
```

---

# 81. `ImportExecution`

```text
ImportExecution
|
+-- batch_id
+-- import_plan_checksum
+-- transaction_mode
+-- created_entry_ids
+-- failed_entry_keys
+-- started_at
+-- completed_at
+-- status
```

---

# 82. Transaction modes

Reprise du document 10 :

```text
ALL_OR_NOTHING

PER_ITEM

CHUNKED_ATOMIC
```

---

# 83. FEC recommandation

Pour un fichier FEC de migration raisonnable :

```text
ALL_OR_NOTHING
```

est le mode de référence.

---

# 84. Gros volume

Pour fichiers massifs :

```text
CHUNKED_ATOMIC
```

peut être nécessaire.

---

# 85. Chunking semantics

Doivent préciser :

```text
chunk size

ordering

checkpoint

retry semantics

partial completion semantics
```

---

# 86. `ImportCheckpoint`

```text
ImportCheckpoint
|
+-- batch_id
+-- last_source_entry_key?
+-- imported_count
+-- last_chunk_id
+-- plan_checksum
+-- updated_at
```

---

# 87. Reprise

Un retry doit reprendre à partir d'un checkpoint cohérent.

---

# 88. Idempotence de l'import

Deux niveaux :

```text
batch idempotence

entry idempotence
```

---

# 89. Batch idempotence

Fingerprint :

```text
entity
+
source checksum
+
adapter
+
business scope
```

---

# 90. Entry idempotence

Clé possible :

```text
entity
+
source system
+
source entry key
```

---

# 91. `SourceEntryIdentity`

```text
SourceEntryIdentity
|
+-- source_system
+-- source_batch_fingerprint
+-- source_entry_key
```

---

# 92. Unique constraint

Persistence peut renforcer :

```text
UNIQUE(
    entity_id,
    source_system,
    source_entry_key,
    source_scope
)
```

---

# 93. Duplicate candidate vs duplicate confirmed

La simple ressemblance de lignes ne suffit pas.

---

# 94. `DuplicateDetectionStrategy`

```text
EXACT_SOURCE_KEY

ROW_HASH

ENTRY_HASH

HEURISTIC
```

---

# 95. Heuristic duplicates

```text
WARNING
```

par défaut.

---

# 96. Exact source duplicate

Peut être :

```text
BLOCKING
```

selon import policy.

---

# 97. Source row hash

Hash d'une représentation canonique de la ligne.

---

# 98. Entry hash

Hash des lignes normalisées de l'écriture dans un ordre déterministe.

---

# 99. Hash not enough

Un hash identique prouve :

```text
canonical payload identity
```

pas :

```text
economic uniqueness
```

---

# 100. Provenance

Chaque `JournalEntry` importée doit conserver :

```text
source = IMPORT / FEC

source_reference

import_batch_id

source_entry_key
```

---

# 101. Provenance ligne

Chaque `JournalEntryLine` doit pouvoir conserver :

```text
source_record_ref

source_line_number

row_checksum
```

---

# 102. Lineage

```text
SourceArtifact
    ->
RawImportRecord
    ->
NormalizedImportRecord
    ->
MappingDecision
    ->
JournalEntry
    ->
JournalEntryLine
```

---

# 103. Audit events

```text
IMPORT_BATCH_CREATED

IMPORT_SOURCE_ACQUIRED

IMPORT_PARSED

IMPORT_NORMALIZED

IMPORT_MAPPED

IMPORT_VALIDATED

IMPORT_STARTED

IMPORT_COMPLETED

IMPORT_FAILED

IMPORT_REPROCESSED
```

---

# 104. Audit mutation

La création d'écritures produit aussi :

```text
ENTRY_CREATE

ENTRY_VALIDATE

ENTRY_POST
```

selon mode.

---

# 105. Correlation

Tous les événements d'un batch partagent :

```text
correlation_id
```

---

# 106. Reprocessing

Reprocess :

```text
same source artifact

new adapter or mapping version

new batch/run
```

---

# 107. Old batch remains immutable

Ne pas modifier :

```text
old normalized records

old import plan

old results
```

---

# 108. Compare reprocessing

```text
ImportComparison
|
+-- old_batch
+-- new_batch
+-- record_differences
+-- mapping_differences
+-- entry_differences
+-- control_differences
```

---

# 109. Adapter registry

```text
AccountingImportAdapterRegistry
```

---

# 110. `AccountingImportAdapter`

```python
class AccountingImportAdapter(Protocol):
    adapter_id: str
    adapter_version: str

    def supports(
        self,
        source: SourceDescriptor,
    ) -> bool:
        ...

    def parser(self) -> AccountingImportParser:
        ...

    def normalizer(self) -> "AccountingImportNormalizer":
        ...

    def validators(self) -> tuple["ImportValidator", ...]:
        ...
```

---

# 111. `AccountingImportNormalizer`

```python
class AccountingImportNormalizer(Protocol):
    def normalize(
        self,
        parsed: ParsedImport,
        context: "ImportNormalizationContext",
    ) -> tuple[NormalizedImportRecord, ...]:
        ...
```

---

# 112. Adapter capabilities

```text
ImportAdapterCapabilities
|
+-- raw_preservation
+-- source_checksum
+-- source_entry_key
+-- source_line_number
+-- currency
+-- auxiliary_fields
+-- dimensions
+-- trusted_posted_history
+-- streaming
```

---

# 113. Generic CSV adapter

Peut exister :

```text
ConfigurableCSVImportAdapter
```

avec schema mapping.

---

# 114. ERP API adapter

Peut lire :

```text
JSON API

paginated entries

source IDs
```

et converger vers le même modèle normalisé.

---

# 115. Legacy DB adapter

Peut lire :

```text
SQL table

ODBC

export
```

---

# 116. FEC adapter

Le FEC est un adapter spécialisé au contexte français.

---

# 117. Principe FEC

Le FEC adapter connaît les colonnes réglementaires attendues du format qu'il supporte.

Le core générique ne les connaît pas.

---

# 118. `FECSourceDescriptor`

```text
FECSourceDescriptor
|
+-- filename
+-- encoding
+-- delimiter
+-- fiscal_year?
+-- entity?
+-- source_system?
```

---

# 119. Colonnes FEC

Le FEC adapter expose une définition versionnée des champs attendus.

Exemples courants à supporter dans la configuration :

```text
JournalCode
JournalLib
EcritureNum
EcritureDate
CompteNum
CompteLib
CompAuxNum
CompAuxLib
PieceRef
PieceDate
EcritureLib
Debit
Credit
EcritureLet
DateLet
ValidDate
Montantdevise
Idevise
```

---

# 120. Important

Ces noms appartiennent au :

```text
FEC Adapter
```

pas au :

```text
Accounting Core
```

---

# 121. `FECFieldDefinition`

```text
FECFieldDefinition
|
+-- field_name
+-- required
+-- parser
+-- semantic_target
+-- validation_rules
```

---

# 122. FEC parser

Responsabilités :

```text
encoding

delimiter

header

field count

raw line number

raw value preservation
```

---

# 123. FEC normalizer

Responsabilités :

```text
dates

Decimal amounts

blank normalization

source entry key

source journal code

source account code

document refs

auxiliary refs
```

---

# 124. FEC source entry key

Proposition initiale :

```text
JournalCode
+
EcritureNum
```

dans le scope du fichier/import.

---

# 125. Attention

L'adapter doit vérifier les réalités du fichier et ne pas supposer que :

```text
EcritureNum alone
```

est globalement unique.

---

# 126. FEC line reference

```text
source_line_number
```

doit être conservé.

---

# 127. FEC raw row hash

Chaque ligne peut recevoir :

```text
SHA-256(canonical raw row)
```

---

# 128. FEC file checksum

Le fichier complet reçoit :

```text
SHA-256(bytes)
```

---

# 129. FEC required-field controls

Catalogue adapter :

```text
FEC_REQUIRED_COLUMNS

FEC_MISSING_JOURNAL_CODE

FEC_MISSING_ENTRY_NUMBER

FEC_MISSING_ACCOUNT_NUMBER

FEC_MISSING_ENTRY_DATE
```

---

# 130. FEC date controls

```text
FEC_INVALID_ENTRY_DATE

FEC_DATE_OUTSIDE_FISCAL_YEAR
```

---

# 131. FEC amount controls

```text
FEC_INVALID_DEBIT

FEC_INVALID_CREDIT

FEC_DEBIT_AND_CREDIT

FEC_ZERO_LINE

FEC_NEGATIVE_AMOUNT
```

---

# 132. FEC balance controls

```text
FEC_UNBALANCED_ENTRY

FEC_GLOBAL_UNBALANCED
```

---

# 133. FEC duplicate controls

```text
FEC_DUPLICATE_LINE
```

par défaut :

```text
WARNING
```

si la détection n'est qu'heuristique.

---

# 134. FEC currency controls

```text
FEC_INVALID_CURRENCY_AMOUNT

FEC_UNKNOWN_CURRENCY
```

si support devise activé.

---

# 135. FEC journal mapping

```text
JournalCode
    ->
JournalId
```

---

# 136. FEC account mapping

```text
CompteNum
    ->
CompanyAccountId
```

---

# 137. CompAuxNum

Ne doit pas être automatiquement concaténé au `CompteNum`.

Il peut alimenter :

```text
AuxiliaryReference
```

selon la `AuxiliaryAccountingPolicy`.

---

# 138. FEC auxiliary modes

Si company chart utilise :

```text
SUBLEDGER
```

alors `CompAuxNum` peut mapper vers :

```text
auxiliary_id
```

---

# 139. Extended account mode

Si entreprise utilise :

```text
EXTENDED_ACCOUNT_CODE
```

alors un adapter-specific rule peut construire un candidat de mapping.

---

# 140. Pas de règle universelle

Interdit :

```python
target_account = CompteNum + CompAuxNum
```

dans le core.

---

# 141. FEC journal auto-discovery

L'adapter peut lister :

```text
distinct JournalCode / JournalLib
```

pour construire des suggestions de configuration.

---

# 142. FEC account auto-discovery

Même logique :

```text
distinct CompteNum / CompteLib
```

---

# 143. Discovery != creation

L'utilisateur/application valide :

```text
create account?

bind account?

map journal?
```

---

# 144. `ImportDiscoveryReport`

```text
ImportDiscoveryReport
|
+-- source_accounts
+-- source_journals
+-- auxiliary_codes
+-- currencies
+-- date_range
+-- entry_count
+-- line_count
```

---

# 145. Preflight

Avant import :

```text
acquire

parse

discover

map

validate

preview
```

---

# 146. `ImportPreflightResult`

```text
ImportPreflightResult
|
+-- discovery
+-- validation
+-- mapping_coverage
+-- import_plan
+-- ready
```

---

# 147. Mapping coverage

```text
mapped accounts / source accounts

mapped journals / source journals
```

---

# 148. Coverage != correctness

100 % mapping coverage ne prouve pas :

```text
correct semantic mapping
```

---

# 149. Human review

Les mappings peuvent exiger :

```text
review before execution
```

---

# 150. Dry-run FEC

Doit permettre :

```text
validation report

unmapped accounts

unmapped journals

duplicate warnings

entry totals

sample normalized entries
```

sans écrire le ledger.

---

# 151. FEC import plan checksum

Le plan validé peut être hashé.

---

# 152. Approval

Un workflow enterprise peut exiger :

```text
ImportPlanApproved
```

avant exécution.

---

# 153. `ImportApproval`

```text
ImportApproval
|
+-- batch_id
+-- plan_checksum
+-- actor
+-- approved_at
+-- notes?
```

---

# 154. Approval != authorization

L'application gère RBAC.

---

# 155. Changed plan after approval

Si :

```text
plan checksum changes
```

l'approbation précédente n'est plus valable.

---

# 156. Import command

```python
result = accounting.imports.execute(
    batch_id=batch.id,
    expected_plan_checksum=plan.checksum,
)
```

---

# 157. Import execution pipeline

```text
verify batch READY

verify plan checksum

reserve idempotency key

open UoW

for each entry plan:
    create JournalEntry
    attach source refs
    validate
    post or preserve according import mode

append audit

append outbox

commit

complete idempotency
```

---

# 158. ALL_OR_NOTHING failure

Si l'entrée 999 échoue :

```text
rollback entries 1..998
```

---

# 159. PER_ITEM

Si choisi :

```text
successful entries remain

failures listed
```

---

# 160. CHUNKED_ATOMIC

Si chunk 4 échoue :

```text
chunks 1..3 remain

chunk 4 rolled back

resume supported
```

---

# 161. Status semantics

Pour chunked :

```text
COMPLETED_WITH_WARNINGS
```

n'est pas la même chose que :

```text
PARTIAL_FAILED
```

---

# 162. Ajouter `PARTIALLY_IMPORTED`

Statut recommandé :

```text
PARTIALLY_IMPORTED
```

pour batch explicitement partiel.

---

# 163. Final status set

```text
COMPLETED

COMPLETED_WITH_WARNINGS

PARTIALLY_IMPORTED

FAILED
```

---

# 164. Import statistics

```text
ImportStatistics
|
+-- source_records
+-- normalized_records
+-- entry_groups
+-- imported_entries
+-- imported_lines
+-- rejected_entries
+-- warnings
+-- total_debit
+-- total_credit
```

---

# 165. Reconciliation post-import

Construire :

```text
Trial Balance
```

sur le scope importé.

---

# 166. Post-import controls

```text
TRIAL_BALANCE_BALANCED

IMPORTED_ENTRY_COUNT_MATCH

IMPORTED_DEBIT_TOTAL_MATCH

IMPORTED_CREDIT_TOTAL_MATCH

SOURCE_LINEAGE_COMPLETE
```

---

# 167. Source total comparison

Si source fournit des totals fiables :

```text
source total
vs
imported total
```

---

# 168. FEC global reconciliation

Peut comparer :

```text
normalized debit total

normalized credit total

imported ledger debit total

imported ledger credit total
```

---

# 169. No direct balance mutation

Import ne fait jamais :

```text
Account.current_balance += amount
```

---

# 170. Ledger rebuild

Après import :

```text
ledger/trial balance
```

est dérivé des entries.

---

# 171. Import and posting sequence

Les écritures historiques peuvent avoir une `accounting_date` ancienne mais reçoivent :

```text
posting_sequence
```

au moment d'acceptation dans PyAccountingKit.

---

# 172. Historical ordering

Ledger order :

```text
accounting_date

posting_sequence

line_number
```

---

# 173. Source entry order

Pour audit, conserver également :

```text
source order
```

---

# 174. `SourceOrder`

```text
record_index

source_entry_order
```

---

# 175. Import into closed fiscal years

Migration historique peut nécessiter :

```text
MigrationImportPolicy
```

---

# 176. `MigrationImportPolicy`

```text
allow_closed_period_history

require_full_source_provenance

require_control_suite

freeze_import_after_migration

trusted_posted_history
```

---

# 177. Normal operational import

Ne doit pas utiliser cette policy.

---

# 178. Migration lock

Après migration validée :

```text
batch becomes immutable
```

---

# 179. Rollback d'import

Deux concepts :

```text
transaction rollback before commit

business reversal after commit
```

---

# 180. Post-commit "undo"

Une importation déjà postée ne doit pas être supprimée massivement.

---

# 181. `ReverseImportBatch`

Commande future :

```text
generate reversals
for all imported posted entries
```

---

# 182. Prérequis

```text
batch completed

entries identifiable

period accepts reversal

policy allows
```

---

# 183. No delete undo

Interdit :

```text
DELETE imported JournalEntries
```

si postées.

---

# 184. Import lineage query

```python
trace = accounting.imports.trace_source(
    entry_id=entry.id,
)
```

---

# 185. Source retrieval

Doit permettre :

```text
entry
    ->
source batch
    ->
source entry key
    ->
raw lines
```

---

# 186. Import query APIs

```text
list batches

batch status

validation report

mapping report

issues

statistics

source trace
```

---

# 187. Pagination

Pour millions de lignes :

```text
server-side pagination
```

---

# 188. Streaming parser

Adapter capability :

```text
streaming = true
```

---

# 189. Streaming normalization

Peut éviter de charger tout le fichier en mémoire.

---

# 190. Mais grouping par écriture

Nécessite parfois buffer :

```text
current source_entry_key
```

si fichier trié.

---

# 191. Unsorted source

Si les lignes d'une même écriture sont dispersées :

```text
external sort / temporary store
```

peut être nécessaire.

---

# 192. Adapter contract

Doit déclarer si :

```text
source is expected grouped by entry
```

---

# 193. `ImportOrderingCapability`

```text
GROUPED_BY_ENTRY

UNORDERED

UNKNOWN
```

---

# 194. FEC common strategy

Le parser doit préserver l'ordre du fichier.

Le grouping repose sur la clé d'écriture source.

---

# 195. Memory strategy

P0 peut commencer :

```text
load moderate file
```

mais architecture doit permettre streaming.

---

# 196. Large import optimization

P1 :

```text
chunked raw storage

batch account mapping lookup

bulk insert

COPY
```

---

# 197. Bulk account lookup

Interdit :

```text
one account query per line
```

---

# 198. Mapping cache

Scope batch :

```text
source account code
    ->
CompanyAccountId
```

---

# 199. Mapping cache validity

Inclure :

```text
chart version
mapping version
```

---

# 200. Journal mapping cache

Même principe.

---

# 201. Period cache

Dates répétées peuvent être résolues efficacement.

---

# 202. Import concurrency

Deux imports du même fichier :

```text
must not duplicate accounting effects
```

---

# 203. Strategy

```text
idempotency reservation

+

source fingerprint unique constraint
```

---

# 204. Distinct import purposes

Même fichier peut être réimporté pour :

```text
dry run

comparison

new sandbox entity
```

donc uniqueness scope doit inclure :

```text
purpose / entity
```

---

# 205. `ImportPurpose`

```text
PREVIEW

MIGRATION

OPERATIONAL

REPROCESSING

TEST
```

---

# 206. Only mutation purposes

```text
MIGRATION

OPERATIONAL
```

écrivent le core.

---

# 207. Preview

Ne produit pas d'écritures.

---

# 208. Reprocessing

Par défaut :

```text
no accounting mutation
```

jusqu'à comparaison/approval.

---

# 209. Adapter versioning

Toute évolution du parser/normalizer doit incrémenter :

```text
adapter_version
```

si semantics changent.

---

# 210. Parser schema version

Possible :

```text
source_schema_version
```

---

# 211. FEC adapter version

Exemple :

```text
fec-adapter/1
```

---

# 212. Reproducibility envelope

Un import completed conserve :

```text
runtime version

adapter version

source checksum

mapping version

chart version

policy version

reference snapshot if relevant

import plan checksum
```

---

# 213. `ImportReproducibilityEnvelope`

```text
ImportReproducibilityEnvelope
|
+-- runtime_version
+-- adapter_id
+-- adapter_version
+-- source_checksum
+-- normalization_version
+-- mapping_snapshot
+-- policy_snapshot
+-- plan_checksum
+-- output_entry_refs
```

---

# 214. Mapping snapshot

Les mappings utilisés doivent être figés.

---

# 215. `ImportMappingSnapshot`

```text
ImportMappingSnapshot
|
+-- account_mappings
+-- journal_mappings
+-- chart_version
+-- captured_at
+-- checksum
```

---

# 216. Mapping changes after import

N'affectent pas l'historique du batch.

---

# 217. Import issue resolution

Un issue peut être :

```text
resolved by mapping

waived

source corrected

batch abandoned
```

---

# 218. `ImportIssueResolution`

```text
issue_ref

resolution_type

actor

reason

object_refs

resolved_at
```

---

# 219. Waiver

Un warning peut être acknowledged.

Une erreur d'invariant comme unbalanced entry ne peut pas être waived vers POSTED normal.

---

# 220. Mapping approval

Candidate -> validated.

---

# 221. Source correction

Produit new artifact.

---

# 222. Batch clone

Une UX peut permettre :

```text
create new batch from previous configuration
```

sans réutiliser les résultats mutables.

---

# 223. Import security

Le parser traite les fichiers comme données non fiables.

---

# 224. Path traversal

Filename source ne doit jamais déterminer directement un path local non contrôlé.

---

# 225. Formula injection

Lors d'exports CSV futurs, protéger les champs si ouvert dans tableur.

---

# 226. Zip bombs

Si compression supportée :

```text
size limits
```

---

# 227. File size limits

Responsabilité application/adapters.

---

# 228. Encoding

Le FEC adapter doit gérer explicitement :

```text
encoding detection/configuration
```

sans silently corrupting text.

---

# 229. Unknown encoding

```text
FEC_ENCODING_UNSUPPORTED
```

---

# 230. Delimiter

Configurable :

```text
tab

pipe

semicolon

custom
```

selon source supportée.

---

# 231. Header validation

Le FEC adapter compare les colonnes attendues à la version configurée.

---

# 232. Extra columns

Policy :

```text
ALLOW_WITH_WARNING

REJECT

PRESERVE_AS_METADATA
```

---

# 233. Missing optional fields

Doivent rester :

```text
None
```

pas valeurs inventées.

---

# 234. Whitespace normalization

Doit être explicite.

---

# 235. Leading zeros

Tous les codes sont :

```text
strings
```

pour préserver :

```text
001
```

---

# 236. Date parsing

Format-specific.

---

# 237. Decimal parsing

Adapter doit gérer :

```text
decimal separator

empty value

sign

scale
```

---

# 238. FEC Debit/Credit

Normaliser vers :

```text
Decimal
```

---

# 239. Negative values

Si format source les contient contrairement aux règles attendues :

```text
issue
```

pas correction silencieuse.

---

# 240. Auto-fix interdit

Le parser ne transforme pas :

```text
Debit = -100
```

en :

```text
Credit = 100
```

sans policy explicite de correction/migration.

---

# 241. Correction rules

Si migration legacy nécessite des corrections :

```text
ImportTransformationRule
```

---

# 242. `ImportTransformationRule`

```text
rule_id

version

applicability

before

after

reason

audit
```

---

# 243. Toute transformation est tracée

---

# 244. Normalization trace

```text
NormalizationTrace
|
+-- source_record_ref
+-- transformations
+-- normalized_record_ref
```

---

# 245. FEC ValidDate

Si présent, peut être conservé dans :

```text
source metadata
```

et éventuellement utilisé par adapter policy.

---

# 246. FEC PieceRef / PieceDate

Conserver comme :

```text
source_document_reference

document_date
```

---

# 247. FEC EcritureLib

Conserver comme :

```text
description
```

---

# 248. FEC JournalLib / CompteLib

Peuvent servir :

```text
discovery

mapping assistance

audit
```

mais ne remplacent pas les objets internes.

---

# 249. Lettrage

`EcritureLet` / `DateLet` relèvent potentiellement d'un futur bounded context :

```text
Reconciliation / Matching
```

P1.1 les conserve comme metadata/source attributes si nécessaire.

---

# 250. Currency

`Montantdevise` / `Idevise` peuvent alimenter une extension multi-devise.

Le core P1.1 ne doit pas forcer leur usage si la feature multi-currency n'est pas activée.

---

# 251. Auxiliary data

`CompAuxNum` / `CompAuxLib` peuvent alimenter :

```text
AuxiliaryReference
```

---

# 252. Adapter-level errors

```text
FECAdapterError
|
+-- FECEncodingError
+-- FECHeaderError
+-- FECFieldCountError
+-- FECDateParseError
+-- FECDecimalParseError
+-- FECGroupingError
```

---

# 253. Generic import errors

```text
AccountingImportError
|
+-- ImportBatchNotFoundError
+-- ImportBatchStateError
+-- ImportSourceUnavailableError
+-- ImportChecksumMismatchError
+-- ImportParserError
+-- ImportNormalizationError
+-- ImportMappingError
+-- ImportValidationError
+-- ImportPlanChangedError
+-- ImportNotReadyError
+-- ImportIdempotencyConflictError
+-- ImportTransactionError
+-- ImportPartialFailureError
```

---

# 254. Mapping errors

```text
UnknownSourceAccountError

AmbiguousAccountMappingError

UnknownSourceJournalError

AmbiguousJournalMappingError
```

---

# 255. Period errors

```text
ImportPeriodNotFoundError

ImportClosedPeriodError
```

---

# 256. Fail-closed

Doivent bloquer :

```text
invalid checksum

unmapped required account

ambiguous mapping

unbalanced entry

invalid period

changed approved plan

idempotency payload conflict
```

---

# 257. Warning-only examples

```text
possible duplicate line

unused optional field

unknown noncritical label
```

---

# 258. Adapter-specific severity

FEC adapter peut définir ses propres defaults.

---

# 259. Controls integration

Un batch peut produire :

```text
ControlRun
```

lié au :

```text
ImportBatch
```

---

# 260. `ImportControlContext`

```text
batch_id

source snapshot

mapping snapshot

normalized records

import plan
```

---

# 261. Post-import ControlRun

Contrôles :

```text
IMPORT_ENTRY_COUNT_MATCH

IMPORT_TOTAL_DEBIT_MATCH

IMPORT_TOTAL_CREDIT_MATCH

TRIAL_BALANCE_BALANCED

SOURCE_LINEAGE_COMPLETE
```

---

# 262. Gate

```text
IMPORT_FINALIZATION_GATE
```

---

# 263. Finalization

Un batch devient `COMPLETED` seulement lorsque :

```text
execution succeeded

required post-import controls passed
```

selon policy.

---

# 264. Trusted posted history qualification

Avant de permettre :

```text
TRUSTED_POSTED_HISTORY_IMPORT
```

l'adapter doit avoir un statut :

```text
PRODUCTION
```

et passer une suite dédiée.

---

# 265. Import adapter qualification

Levels :

```text
TEST_ONLY

EXPERIMENTAL

VALIDATED

PRODUCTION
```

---

# 266. FEC adapter Production requirements

```text
parser contract

normalization golden tests

required-field tests

date tests

amount tests

balance tests

duplicate tests

raw lineage tests

idempotency tests

PostgreSQL transaction tests
```

---

# 267. Unit tests - import batch

```text
test_batch_state_machine

test_completed_batch_is_immutable

test_failed_batch_cannot_jump_to_completed
```

---

# 268. Unit tests - parser

```text
test_preserves_source_line_number

test_preserves_raw_values

test_invalid_row_detected
```

---

# 269. Unit tests - normalization

```text
test_amounts_are_decimal

test_codes_remain_strings

test_dates_are_dates

test_source_entry_key_stable
```

---

# 270. Unit tests - mapping

```text
test_exact_configured_mapping

test_unknown_account_fails

test_ambiguous_mapping_fails

test_candidate_not_executable
```

---

# 271. Unit tests - grouping

```text
test_two_lines_same_source_entry_grouped

test_different_entry_keys_not_grouped

test_grouping_deterministic
```

---

# 272. Unit tests - validation

```text
test_unbalanced_entry_blocking

test_zero_line_handling

test_unknown_journal_blocking
```

---

# 273. Unit tests - idempotence

```text
test_same_source_fingerprint_detected

test_same_entry_identity_not_duplicated
```

---

# 274. Property-based tests

```text
normalized amount never float

grouped records preserve all source record refs

same source + adapter version -> same normalized output
```

---

# 275. Property - imported entries balanced

Pour toute entry importée et postée :

```text
sum debit == sum credit
```

---

# 276. Property - lineage completeness

Pour toute imported JournalLine :

```text
source record ref exists
```

si adapter capability le promet.

---

# 277. Contract tests - adapters

Tous adapters doivent fournir :

```text
source support

parse

normalize

stable adapter id/version

declared capabilities
```

---

# 278. `ImportAdapterContractTests`

```text
test_adapter_has_stable_id

test_adapter_has_version

test_parser_preserves_record_order

test_normalizer_returns_generic_records

test_errors_are_translated
```

---

# 279. Integration - generic import

```text
source fixture

adapter

CompanyAccount mappings

Journal mappings

PostgreSQL

JournalEntries created
```

---

# 280. Integration - all-or-nothing rollback

Inject failure entry N.

Expected :

```text
no imported entries
```

---

# 281. Integration - chunked

Expected :

```text
completed chunks preserved

failed chunk rolled back

checkpoint valid
```

---

# 282. Concurrency - duplicate batch

Two workers same fingerprint.

Expected :

```text
one execution
```

---

# 283. Concurrency - same source entry

Expected :

```text
no duplicate JournalEntry
```

---

# 284. Golden FEC fixtures

Prévoir :

```text
fec_minimal_valid

fec_balanced_multi_entry

fec_missing_required_column

fec_invalid_date

fec_negative_amount

fec_debit_and_credit

fec_unbalanced_entry

fec_duplicate_candidate

fec_auxiliary_accounts

fec_currency_fields
```

---

# 285. Golden FEC valid

Expected :

```text
stable normalized rows

stable entry groups

stable totals

stable lineage
```

---

# 286. Golden invalid date

Expected :

```text
FEC_INVALID_ENTRY_DATE
```

---

# 287. Golden unbalanced

Expected :

```text
FEC_UNBALANCED_ENTRY

blocking = true
```

---

# 288. Golden duplicate candidate

Expected :

```text
FEC_DUPLICATE_LINE

warning
```

si configured heuristic.

---

# 289. Golden mapping

Source :

```text
CompteNum = 512001
```

Company mapping configured to account A.

Expected :

```text
target = A
```

sans inférence vers référence réglementaire.

---

# 290. Golden auxiliary

Input :

```text
CompteNum = 411000
CompAuxNum = CUST001
```

Expected depends on:

```text
AuxiliaryAccountingPolicy
```

---

# 291. Golden source lineage

```text
file checksum

line 42

row checksum

entry key

JournalEntry

JournalLine
```

must be reconstructible.

---

# 292. Replay test

Same:

```text
source artifact

adapter version

mapping snapshot

policy snapshot
```

Expected:

```text
same import plan checksum
```

---

# 293. Current engine comparison

Reprocess with adapter v2.

Expected:

```text
ImportComparison
```

---

# 294. Performance smoke

Targets:

```text
10k lines

100k lines

1M lines optional/nightly
```

---

# 295. Metrics

```text
import_batches_total

import_duration

import_lines_par_second

mapping_miss_total

validation_error_total

duplicate_warning_total

rollback_total

reprocess_total
```

---

# 296. Logging

Context:

```text
batch_id

adapter_id

source checksum

entity_id

stage

correlation_id
```

---

# 297. Ne pas logger

```text
full raw file

sensitive descriptions

credentials
```

---

# 298. Tracing spans

```text
acquire_source

parse_import

normalize_import

resolve_mappings

validate_import

build_import_plan

execute_import

post_import_controls
```

---

# 299. Package domain

```text
src/pyaccountingkit/domain/imports/
|
+-- batch.py
+-- status.py
+-- source.py
+-- raw_record.py
+-- normalized_record.py
+-- grouping.py
+-- mapping.py
+-- issue.py
+-- validation.py
+-- plan.py
+-- execution.py
+-- checkpoint.py
+-- reproducibility.py
```

---

# 300. Application package

```text
src/pyaccountingkit/application/imports/
|
+-- create_batch.py
+-- acquire_source.py
+-- parse_batch.py
+-- normalize_batch.py
+-- discover.py
+-- resolve_mappings.py
+-- validate_batch.py
+-- build_plan.py
+-- approve_plan.py
+-- execute_import.py
+-- reprocess.py
+-- reverse_import.py
```

---

# 301. Ports

```text
ImportBatchRepository

RawImportRecordRepository

NormalizedImportRecordRepository

ImportMappingRepository

ImportCheckpointRepository

ArtifactStorePort

IdempotencyStore

UnitOfWork

AccountingReferenceProvider

CompanyAccountRepository

JournalRepository

AccountingPeriodRepository
```

---

# 302. Adapter package

```text
src/pyaccountingkit/adapters/imports/
|
+-- fec/
|   +-- adapter.py
|   +-- parser.py
|   +-- normalizer.py
|   +-- schema.py
|   +-- validators.py
|   +-- grouping.py
|   +-- errors.py
|
+-- csv/
|
+-- api/
|
+-- in_memory/
```

---

# 303. FEC schema module

```text
schema.py
```

doit contenir les définitions spécifiques du format.

---

# 304. No FEC fields in generic domain

Interdit :

```text
domain/imports/fec_columns.py
```

---

# 305. Adapter configuration

```text
FECAdapterConfiguration
|
+-- encoding
+-- delimiter
+-- schema_version
+-- duplicate_policy
+-- currency_mode
+-- trusted_history_mode
```

---

# 306. Public API - create FEC batch

```python
batch = accounting.imports.create(
    entity_id=entity_id,
    adapter="fec",
    source=file_ref,
    purpose=ImportPurpose.MIGRATION,
)
```

---

# 307. Public API - preflight

```python
preflight = accounting.imports.preflight(
    batch_id=batch.id,
)
```

---

# 308. Public API - mappings

```python
accounting.imports.map_account(
    batch_id=batch.id,
    source_account_code="512001",
    company_account_id=bank_account.id,
)
```

---

# 309. Public API - validate

```python
report = accounting.imports.validate(
    batch_id=batch.id,
)
```

---

# 310. Public API - plan

```python
plan = accounting.imports.build_plan(
    batch_id=batch.id,
)
```

---

# 311. Public API - execute

```python
result = accounting.imports.execute(
    batch_id=batch.id,
    expected_plan_checksum=plan.checksum,
)
```

---

# 312. Public API - trace

```python
source = accounting.imports.trace(
    entry_id=entry_id,
)
```

---

# 313. Public API - reprocess

```python
comparison = accounting.imports.reprocess(
    source_batch_id=batch.id,
    adapter_version="fec-adapter/2",
    dry_run=True,
)
```

---

# 314. Dry run guarantee

`dry_run=True` :

```text
must not mutate accounting core
```

---

# 315. Import approval gate

Optional:

```text
IMPORT_PLAN_APPROVAL_GATE
```

---

# 316. Security gate

Optional:

```text
SOURCE_FILE_ACCEPTED
```

avant parsing.

---

# 317. Artifact retention

Source artifact retention doit être configurable.

---

# 318. Raw retention

Peut différer de source retention.

---

# 319. Audit dependency

Ne pas supprimer raw/source encore référencé par :

```text
published snapshot

audit requirement

migration evidence
```

---

# 320. PII

FEC peut contenir des libellés sensibles.

Audit et logs doivent minimiser leur duplication.

---

# 321. Encryption

Infrastructure concern.

---

# 322. Import sandbox

Un import peut être exécuté en :

```text
PREVIEW / sandbox
```

sans mutation.

---

# 323. Sandbox chart

Option future :

```text
temporary mapping context
```

---

# 324. Reject unknown standard

Import n'a pas toujours besoin d'un standard réglementaire.

Il peut fonctionner avec :

```text
existing CompanyChart
```

---

# 325. Reference snapshot use

Nécessaire seulement lorsque :

```text
mapping/reference compliance
```

est explicitement impliqué.

---

# 326. FEC adapter != regulatory-accounting-data-framework

Le FEC est :

```text
transactional accounting exchange format
```

Le regulatory framework est :

```text
reference data
```

---

# 327. Distinction

```text
FEC CompteNum
    ->
CompanyAccount

CompanyAccount
    ->
ReferenceAccount
```

deux étapes distinctes.

---

# 328. Import to reporting

Import ne mappe pas directement :

```text
FEC row -> StatementLine
```

---

# 329. Correct flow

```text
FEC
    ->
JournalEntry
    ->
Ledger
    ->
Trial Balance
    ->
Financial Statements
```

---

# 330. Import to financial analysis

Même principe.

---

# 331. Import and closing

Un FEC historique peut contenir :

```text
adjusting

closing

opening
```

entries.

L'adapter peut les classifier si des règles explicites existent.

---

# 332. EntryType classification

Doit être :

```text
adapter policy
```

pas heuristique silencieuse.

---

# 333. Journal prefix heuristics

Peuvent produire :

```text
EntryTypeSuggestion
```

---

# 334. Suggestion != classification validée

---

# 335. Legacy migration

Un adapter legacy peut permettre :

```text
source status -> EntryType
```

si mapping explicitement configuré.

---

# 336. Import reversal linkage

Si source contient une relation d'annulation :

```text
source_reversal_ref
```

adapter peut tenter de mapper vers :

```text
reversal_of
```

---

# 337. Must validate

Ne jamais marquer une reversal sans vérification comptable.

---

# 338. External posted status

Une source déclarant une écriture "posted" ne suffit pas.

Le trusted mode doit être activé.

---

# 339. Data quality score

Option :

```text
ImportQualitySummary
```

---

# 340. Metrics

```text
mapping_coverage

warning_rate

rejection_rate

duplicate_candidate_rate

lineage_completeness
```

---

# 341. Quality score != gate by default

Les controls/gates décident.

---

# 342. Discovery UX

L'API doit pouvoir fournir :

```text
unknown accounts

unknown journals

date ranges

duplicate candidates
```

avant execution.

---

# 343. Preview sample

Peut exposer :

```text
first N normalized entries
```

sans dépendre du stockage final.

---

# 344. Mapping templates

Une organisation peut sauvegarder :

```text
ImportMappingProfile
```

---

# 345. `ImportMappingProfile`

```text
profile_id

source_system

account mappings

journal mappings

version

effective dates
```

---

# 346. Profile version

Pinned in import batch.

---

# 347. Mapping profile changes

Do not affect historical batch.

---

# 348. Source systems

```text
FEC

ERP_X

LEGACY_Y

CSV_CUSTOM
```

---

# 349. `SourceSystemId`

Value Object string.

---

# 350. Multiple files

Un batch peut éventuellement regrouper plusieurs artifacts.

P1.1 recommande :

```text
one primary artifact per batch
```

pour simplicité.

---

# 351. Multi-file future

Exemple :

```text
header file

lines file
```

support via :

```text
SourceBundle
```

---

# 352. `SourceBundle`

P1 future extension.

---

# 353. Compression

Adapter may support:

```text
zip

gzip
```

but checksum semantics must specify:

```text
compressed bytes
or
decompressed payload
```

---

# 354. Recommendation

Store both if needed:

```text
artifact checksum

content checksum
```

---

# 355. `SourceChecksums`

```text
artifact_sha256

content_sha256?
```

---

# 356. Encoding conversion

If bytes converted before parse, preserve:

```text
original artifact

normalization trace
```

---

# 357. Error line reporting

ImportIssue must expose:

```text
source line number
```

when available.

---

# 358. Error aggregation

For massive errors, return:

```text
summary

paged findings
```

---

# 359. Max issue count

Application may cap materialized issue payload.

But must keep counts.

---

# 360. Streaming issue repository

P1 performance extension.

---

# 361. Import transaction audit

Final audit must include:

```text
source checksum

plan checksum

entry count

line count

totals

adapter version
```

---

# 362. Import evidence bundle

```text
ImportEvidenceBundle
|
+-- batch_id
+-- source_artifact_ref
+-- source_checksum
+-- adapter_id
+-- adapter_version
+-- mapping_snapshot
+-- validation_report_ref
+-- import_plan_ref
+-- control_run_refs
+-- execution_result
+-- audit_refs
+-- checksum
```

---

# 363. Evidence bundle immutable

After finalization.

---

# 364. Export evidence

Can be used for migration sign-off.

---

# 365. Reconciliation with source

A post-import report should answer:

```text
How many source lines?

How many normalized lines?

How many imported lines?

How many rejected?

Which source entry became which JournalEntry?
```

---

# 366. `ImportReconciliationReport`

```text
source_record_count

normalized_record_count

source_entry_count

imported_entry_count

imported_line_count

rejected_entry_count

source_debit_total

source_credit_total

imported_debit_total

imported_credit_total
```

---

# 367. Zero loss expectation

For a complete successful import:

```text
all accepted source records
have downstream trace
```

---

# 368. Rejected records

Must remain traceable to:

```text
ImportIssue
```

---

# 369. No silent drop

Interdit :

```text
skip malformed line without issue
```

---

# 370. No silent coercion

Interdit :

```text
invalid date -> today's date
```

---

# 371. No silent account fallback

Interdit :

```text
unknown account -> suspense account
```

sans explicit `FallbackAccountPolicy`.

---

# 372. `FallbackAccountPolicy`

Possible in migration scenarios:

```text
DISALLOW

REVIEW_REQUIRED

ALLOW_CONFIGURED_SUSPENSE
```

---

# 373. Suspense account

If allowed, must be:

```text
explicit CompanyAccountId
```

not code hardcoded.

---

# 374. Fallback produces finding

Always:

```text
WARNING or ERROR
```

and provenance.

---

# 375. Error recovery

User/application can:

```text
fix mapping

fix source

change policy

rebuild plan
```

---

# 376. Plan invalidation

Any change to:

```text
mapping

adapter version

normalization policy

source artifact

chart version
```

invalidates existing plan.

---

# 377. `ImportPlanStaleness`

```text
CURRENT

STALE

SUPERSEDED
```

---

# 378. Execute stale plan

Forbidden.

---

# 379. `ImportPlanChangedError`

Raised.

---

# 380. Mapping version pin

Required.

---

# 381. Chart version pin

Required.

---

# 382. Journal mapping snapshot pin

Required.

---

# 383. Period state at execute

Must be revalidated.

---

# 384. Why

Between preflight and execution:

```text
period may close

account may deactivate

journal may deactivate
```

---

# 385. Execute revalidation

Like posting:

```text
critical context is rechecked
```

---

# 386. Race import vs close

Same period serialization requirement as normal posting.

---

# 387. Import and account deactivation race

Revalidate inside UoW.

---

# 388. Import and chart migration race

Pin chart version.

---

# 389. Full batch lock?

Not required globally.

Use scoped concurrency primitives.

---

# 390. `ImportBatch.revision`

Mutable process aggregate should use revision.

---

# 391. Double execute

Prevent with:

```text
revision

idempotency

status
```

---

# 392. Two workers execute same READY batch

Expected:

```text
one IMPORTING transition

one conflict
```

---

# 393. Batch execution lock

Adapter may use:

```text
row lock
```

---

# 394. Application command

```text
ExecuteImportBatch
```

owns UoW.

---

# 395. External artifact storage

No long object-storage read inside DB transaction if avoidable.

---

# 396. Correct

Parse/build plan before accounting transaction.

---

# 397. Execute uses prepared plan

This keeps transaction shorter.

---

# 398. Plan storage

Can be:

```text
database JSON

artifact store

normalized tables
```

---

# 399. Plan checksum protects integrity

---

# 400. Schema versioning

```text
ImportPlanSchemaVersion
```

---

# 401. Adapter schema versioning

Separate.

---

# 402. Public API schema

Separate.

---

# 403. ADRs

| ID | Décision |
|---|---|
| ADR-IMP-001 | Le FEC est un adapter spécialisé, pas le modèle universel d'import |
| ADR-IMP-002 | `AccountingImportBatch` est l'Aggregate Root du processus d'import |
| ADR-IMP-003 | L'artefact source est conservé avec checksum |
| ADR-IMP-004 | Les raw records sont conservés lorsque la capability/policy l'exige |
| ADR-IMP-005 | Parsing, normalization, mapping et posting sont des étapes distinctes |
| ADR-IMP-006 | Les normalized records utilisent le vocabulaire générique PyAccountingKit |
| ADR-IMP-007 | Les codes sources restent des strings |
| ADR-IMP-008 | Les montants normalisés utilisent Decimal |
| ADR-IMP-009 | Les lignes sont regroupées par `SourceEntryKey` déterministe |
| ADR-IMP-010 | Source account mapping et RegulatoryAccountBinding sont distincts |
| ADR-IMP-011 | Une candidate mapping n'est pas exécutable sans validation |
| ADR-IMP-012 | Les journaux sources sont mappés explicitement |
| ADR-IMP-013 | Import ne crée pas silencieusement comptes ou journaux inconnus |
| ADR-IMP-014 | `ImportPlan` est construit avant mutation comptable |
| ADR-IMP-015 | Dry-run ne mute jamais le core |
| ADR-IMP-016 | L'exécution revalide les états critiques |
| ADR-IMP-017 | Le mode normal suit Create -> Validate -> Post |
| ADR-IMP-018 | `TRUSTED_POSTED_HISTORY_IMPORT` est une exception explicite |
| ADR-IMP-019 | Trusted history ne contourne pas la partie double |
| ADR-IMP-020 | L'idempotence existe au niveau batch et entry |
| ADR-IMP-021 | Duplicate heuristic != duplicate confirmed |
| ADR-IMP-022 | Les imports postés ne sont jamais annulés par DELETE |
| ADR-IMP-023 | Un undo métier utilise reversal |
| ADR-IMP-024 | Les source refs sont préservées jusqu'à JournalEntryLine |
| ADR-IMP-025 | Reprocessing crée un nouveau run, jamais une mutation de l'ancien |
| ADR-IMP-026 | Mapping snapshot et adapter version sont pinés |
| ADR-IMP-027 | FEC field names restent dans `adapters/imports/fec` |
| ADR-IMP-028 | `CompAuxNum` n'est jamais concaténé automatiquement au compte général dans le core |
| ADR-IMP-029 | FEC duplicate candidates sont warnings par défaut lorsqu'heuristiques |
| ADR-IMP-030 | `FEC_*` controls restent adapter-specific |
| ADR-IMP-031 | ALL_OR_NOTHING est la référence pour migrations FEC raisonnables |
| ADR-IMP-032 | CHUNKED_ATOMIC doit exposer ses semantics de reprise |
| ADR-IMP-033 | Aucun record source ne peut être silently dropped |
| ADR-IMP-034 | Toute correction/coercion explicite produit une trace |
| ADR-IMP-035 | Stale ImportPlan ne peut pas être exécuté |
| ADR-IMP-036 | Import et period close partagent les mêmes garanties de concurrence |
| ADR-IMP-037 | Le plan d'import final peut être approuvé par checksum |
| ADR-IMP-038 | Les post-import controls participent à la finalisation |
| ADR-IMP-039 | Le FEC n'est jamais mappé directement vers les états financiers |
| ADR-IMP-040 | Un adapter Production passe contract, golden, rollback et concurrency suites |

---

# 404. Critères d'acceptation P1.1

```text
[ ] AccountingImportBatch est défini

[ ] state machine d'import est définie

[ ] SourceArtifact est défini

[ ] SHA-256 source est défini

[ ] RawImportRecord est défini

[ ] parsing et normalization sont séparés

[ ] NormalizedImportRecord est défini

[ ] SourceEntryKey est défini

[ ] grouping strategy est définie

[ ] source account -> CompanyAccount mapping est défini

[ ] source journal -> Journal mapping est défini

[ ] candidate mapping fail-closed est défini

[ ] account auto-create n'est pas implicite

[ ] journal auto-create n'est pas implicite

[ ] period resolver est défini

[ ] closed period policy est définie

[ ] NORMAL_IMPORT est défini

[ ] TRUSTED_POSTED_HISTORY_IMPORT est défini

[ ] trusted mode ne contourne pas les invariants

[ ] ImportIssue est défini

[ ] ImportValidationReport est défini

[ ] ImportPlan est défini

[ ] dry-run est défini

[ ] plan checksum est défini

[ ] ImportExecution est défini

[ ] ALL_OR_NOTHING / PER_ITEM / CHUNKED_ATOMIC sont supportés

[ ] ImportCheckpoint est défini

[ ] batch idempotence est définie

[ ] entry idempotence est définie

[ ] lineage source -> JournalLine est défini

[ ] reprocessing est défini

[ ] FEC adapter est isolé du core

[ ] FEC field schema est versionné

[ ] FEC required fields controls sont définis

[ ] FEC dates controls sont définis

[ ] FEC amounts controls sont définis

[ ] FEC balance controls sont définis

[ ] FEC duplicate warnings sont définis

[ ] CompAuxNum est traité via policy auxiliaire

[ ] source artifact / raw / normalized refs sont auditables

[ ] ImportEvidenceBundle est défini

[ ] ImportReconciliationReport est défini

[ ] no silent drop / no silent coercion sont explicites

[ ] stale plan execute est interdit

[ ] adapter qualification suite est définie
```

---

# 405. Ordre d'implémentation recommandé

## IMP-00 - Import primitives

```text
ImportBatchId

ImportPurpose

ImportBatchStatus

SourceArtifact

SourceFingerprint
```

---

## IMP-01 - Batch aggregate

```text
AccountingImportBatch

revision

state machine
```

---

## IMP-02 - Parser contracts

```text
AccountingImportAdapter

AccountingImportParser

ParsedImport

RawImportRecord
```

---

## IMP-03 - Normalization

```text
NormalizedImportRecord

SourceEntryKey

GroupingStrategy
```

---

## IMP-04 - Mapping

```text
ImportAccountMapping

ImportJournalMapping

MappingDecision

MappingSnapshot
```

---

## IMP-05 - Validation / Preflight

```text
ImportIssue

ImportValidationReport

ImportDiscoveryReport

ImportPreflightResult
```

---

## IMP-06 - Import Plan

```text
ImportPlan

checksum

approval

staleness
```

---

## IMP-07 - Execution

```text
ExecuteImportBatch

UoW

idempotency

JournalEntry creation

posting
```

---

## IMP-08 - Provenance / Evidence

```text
lineage

evidence bundle

reconciliation report
```

---

## IMP-09 - FEC Adapter Bootstrap

```text
FEC schema

parser

normalizer

grouping
```

---

## IMP-10 - FEC Validation

```text
required columns

dates

amounts

balance

duplicates
```

---

## IMP-11 - FEC Mapping / Discovery

```text
accounts

journals

auxiliary refs

preview
```

---

## IMP-12 - FEC Golden Suite

```text
valid

invalid

duplicates

auxiliary

currency
```

---

## IMP-13 - PostgreSQL Qualification

```text
rollback

duplicate batch race

same-entry race

period close race
```

---

# 406. Démonstrateur P1.1 - FEC preflight

```text
1. Create entity

2. Create CompanyChart

3. Create / map journals

4. Upload FEC source

5. Compute SHA-256

6. Create ImportBatch

7. Parse source

8. Preserve raw line numbers

9. Normalize dates / Decimal amounts

10. Discover:
      accounts
      journals
      date range
      source entries

11. Resolve mappings

12. Validate:
      required fields
      dates
      debit/credit
      entry balance
      global balance

13. Build ImportPlan

14. Produce:
      mapping coverage
      validation report
      plan checksum

15. No JournalEntry created yet
```

---

# 407. Démonstrateur P1.1 - execution

```text
1. Approve ImportPlan checksum

2. Execute batch

3. Reserve idempotency fingerprint

4. Open UnitOfWork

5. For each source entry:
      build JournalEntry
      attach source refs
      validate
      post

6. Persist audit + outbox

7. Commit

8. Build post-import Trial Balance

9. Run post-import controls

10. Finalize batch
```

---

# 408. Démonstrateur - duplicate import

```text
First run:
    source checksum H
    entity E
    source scope S

Second run:
    same H + E + S

Expected:
    duplicate/idempotent detection
    no duplicate ledger effects
```

---

# 409. Démonstrateur - mapping review

```text
Source account:
    512001

No configured mapping

Heuristic suggests:
    CompanyAccount A

Status:
    CANDIDATE

Execution:
    BLOCKED

Human validates mapping

New plan generated

Execution:
    ALLOWED
```

---

# 410. Démonstrateur - auxiliary FEC

```text
CompteNum:
    411000

CompAuxNum:
    CUST-001

Company mode:
    SUBLEDGER

Expected:
    CompanyAccount = customer control account
    auxiliary_ref = CUST-001
```

No:

```text
411000CUST-001
```

automatic concatenation.

---

# 411. Démonstrateur - rollback

```text
Entry 1 valid

Entry 2 valid

Entry 3 invalid due to race / period close

Transaction mode:
    ALL_OR_NOTHING

Expected:
    0 entries imported
```

---

# 412. Démonstrateur - chunked

```text
100,000 source entries

chunks = 10,000

chunk 1 PASS
chunk 2 PASS
chunk 3 FAIL

Expected:
    chunk 1/2 durable
    chunk 3 rollback
    checkpoint points after chunk 2
    batch PARTIALLY_IMPORTED
```

---

# 413. Démonstrateur - reprocessing

```text
Original:
    FEC adapter v1
    mapping snapshot M1
    plan P1

Reprocess:
    FEC adapter v2
    mapping snapshot M2
    dry-run

Expected:
    ImportComparison
    no accounting mutation
```

---

# 414. Frontière avec Financial Statements

Le prochain document :

```text
13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md
```

doit consommer :

```text
TrialBalance / TrialBalanceSnapshot
```

et non directement :

```text
FEC
```

---

# 415. Frontière avec Financial Analysis

Même règle :

```text
FEC
    ->
Accounting Core
    ->
Statements
    ->
Financial Analysis
```

---

# 416. Frontière avec Controls

Le moteur Imports réutilise :

```text
ControlDefinition

ControlRun

ControlGate
```

pour la qualification.

---

# 417. Frontière avec Audit

Import conserve :

```text
source

mapping

plan

execution

post-import controls
```

dans la chaîne d'audit.

---

# 418. Frontière avec Persistence

Les guarantees :

```text
UnitOfWork

idempotency

unique constraints

locking

outbox
```

proviennent de `10`.

---

# 419. Frontière avec Testing

La qualification FEC doit utiliser :

```text
unit

property

contract

integration

concurrency

golden

replay
```

définis dans `11`.

---

# 420. Risques principaux

## RISK-IMP-001 - FEC contamine le core

Réponse :

```text
adapter boundary
```

---

## RISK-IMP-002 - Silent row loss

Réponse :

```text
raw count + normalized count + lineage
```

---

## RISK-IMP-003 - Wrong account mapping

Réponse :

```text
validated mappings + fail-closed
```

---

## RISK-IMP-004 - Duplicate import

Réponse :

```text
source fingerprint + idempotency + unique source entry identity
```

---

## RISK-IMP-005 - Large transaction

Réponse :

```text
CHUNKED_ATOMIC with explicit semantics
```

---

## RISK-IMP-006 - Historical import bypasses accounting rules

Réponse :

```text
trusted mode remains explicit and validated
```

---

## RISK-IMP-007 - Raw source unavailable later

Réponse :

```text
SourceArtifact + checksum + retention
```

---

## RISK-IMP-008 - Mapping changed after preview

Réponse :

```text
ImportPlan checksum + MappingSnapshot
```

---

## RISK-IMP-009 - Import races with period close

Réponse :

```text
same protected period semantics as Posting
```

---

## RISK-IMP-010 - Heuristic duplicate treated as certainty

Réponse :

```text
candidate warning != confirmed duplicate
```

---

# 421. Conclusion

L'architecture d'import de PyAccountingKit est :

```text
SOURCE
  |
  v
IMMUTABLE ARTIFACT
  |
  v
RAW
  |
  v
NORMALIZED
  |
  v
MAPPED
  |
  v
VALIDATED
  |
  v
IMPORT PLAN
  |
  v
JOURNAL ENTRY
  |
  v
POSTING
  |
  v
LEDGER
```

Le FEC s'insère comme :

```text
FEC
  |
  v
FEC Adapter
  |
  v
Generic Accounting Import Core
```

Les principes structurants sont :

```text
FEC != Accounting Core

Parse != Normalize

Normalize != Map

Map != Post

Candidate mapping != validated mapping

Source account != regulatory account

Import plan before mutation

Dry-run never mutates accounting

No silent row drop

No silent coercion

Imported posted entries remain immutable

Undo means reversal

Idempotency is explicit

Source lineage must be preserved

Reprocessing creates a new run

The same Accounting Core is used for every import format
```

Le P1.1 fournit ainsi une architecture capable d'ingérer le FEC sans enfermer PyAccountingKit dans un format français, tout en conservant un niveau élevé d'auditabilité, d'idempotence et de reproductibilité.

---

**Prochain document recommandé :**

```text
13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md
```


---

## Sources et références documentaires du projet

- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)
- 📦 [regulatory-accounting-data-framework](../../../resources/regulatory-accounting-data-framework/)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-03 — Imports & Reporting (0.3.0)](../../plans/PLAN-03_IMPORTS_REPORTING_0.3.0.md)
