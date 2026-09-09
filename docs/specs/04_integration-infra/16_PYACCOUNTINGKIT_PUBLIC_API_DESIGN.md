# 16 - PyAccountingKit - Design de l'API publique

> **Projet** : PyAccountingKit  
> **Document** : `16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md`  
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
> - `12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`
> - `13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`
> - `14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`
> - `15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md`
> **Statut** : P1.5 - Design de l'API publique  
> **Langue** : Français  
> **Objet** : Définir la surface publique stable de PyAccountingKit, ses façades, commandes, queries, DTOs, erreurs, objets de contexte, conventions de nommage, compatibilité, extensibilité, async boundary, dépendances optionnelles et règles de stabilité avant release candidate.

---

# 1. Résumé exécutif

PyAccountingKit doit exposer une API publique :

```text
simple à découvrir

cohérente

stable

typée

framework-neutral

testable

extensible

indépendante de Django / SQLAlchemy
```

La surface cible est organisée autour d'une façade principale :

```python
accounting = AccountingApplication(...)
```

puis de sous-façades :

```text
accounting.references
accounting.charts
accounting.entries
accounting.ledger
accounting.closing
accounting.controls
accounting.imports
accounting.statements
accounting.reporting
accounting.analysis
accounting.subledgers
```

Principe central :

```text
Public API
    !=
Internal implementation

Public API
    !=
ORM API

Public API
    !=
Repository API

Public API
    !=
Database transaction API
```

---

# 2. Objectifs

L'API publique doit permettre de :

1. créer/configurer une application PyAccountingKit ;
2. gérer les référentiels comptables ;
3. gérer les plans de comptes entreprise ;
4. créer/valider/poster/extourner des écritures ;
5. interroger journal, grand livre et balance ;
6. gérer périodes et clôtures ;
7. gérer contrôles et audit ;
8. gérer imports et FEC ;
9. générer états financiers ;
10. générer reporting réglementaire ;
11. produire analyses financières ;
12. gérer sous-livres clients/fournisseurs ;
13. rester indépendante de tout ORM ;
14. offrir des erreurs publiques stables ;
15. offrir des DTOs publics stables ;
16. permettre des adapters tiers ;
17. permettre une évolution contrôlée ;
18. supporter des dépendances optionnelles ;
19. maintenir une API synchrone claire en P1 ;
20. préparer une API async future sans casser le modèle.

---

# 3. Non-objectifs

Le design public ne doit pas exposer :

```text
Django QuerySet

SQLAlchemy Session

transaction.atomic

select_for_update

SQL

ORM models

database cursors

internal domain private methods

internal repository implementation details
```

---

# 4. Principes généraux

## API-001 - Une façade applicative principale

```python
accounting = AccountingApplication(...)
```

---

## API-002 - Des sous-façades par bounded context

```text
accounting.entries
accounting.ledger
accounting.imports
...
```

---

## API-003 - L'utilisateur ordinaire ne manipule pas UnitOfWork

Le UoW reste infrastructure/application interne.

---

## API-004 - Les commandes sont explicites

Préférer :

```python
accounting.entries.post(entry_id=...)
```

à :

```python
entry.post()
```

dans l'API publique principale.

---

## API-005 - Les queries retournent des DTOs

Pas d'objets ORM.

---

## API-006 - Les objets de domaine importants peuvent être exposés en lecture

Exemples :

```text
Money
JournalEntry
CompanyAccount
AccountingPeriod
```

mais les mutations critiques restent orchestrées via services.

---

## API-007 - Les erreurs publiques sont stables

L'utilisateur ne doit pas recevoir :

```text
IntegrityError
StaleDataError
OperationalError
```

directement.

---

# 5. Point d'entrée principal

```python
from pyaccountingkit import AccountingApplication
```

Construction :

```python
accounting = AccountingApplication(
    uow_factory=uow_factory,
    reference_provider=reference_provider,
    clock=clock,
    id_factory=id_factory,
)
```

---

# 6. Composition root

La configuration réelle peut être assemblée par helper :

```python
accounting = configure_accounting(
    persistence="django",
    reference_provider=...,
)
```

mais le coeur ne doit pas dépendre d'un registry global implicite.

---

# 7. `AccountingApplication`

```python
class AccountingApplication:
    references: ReferenceAPI
    charts: ChartsAPI
    entries: EntriesAPI
    ledger: LedgerAPI
    closing: ClosingAPI
    controls: ControlsAPI
    imports: ImportsAPI
    statements: StatementsAPI
    reporting: RegulatoryReportingAPI
    analysis: FinancialAnalysisAPI
    subledgers: SubledgersAPI
```

---

# 8. API namespace

Surface recommandée :

```text
pyaccountingkit
|
+-- AccountingApplication
+-- Money
+-- DecimalAmount
+-- CurrencyCode
+-- AccountingDate
+-- public/
```

---

# 9. Package public

```text
src/pyaccountingkit/public/
|
+-- application.py
+-- references.py
+-- charts.py
+-- entries.py
+-- ledger.py
+-- closing.py
+-- controls.py
+-- imports.py
+-- statements.py
+-- reporting.py
+-- analysis.py
+-- subledgers.py
+-- dto/
+-- errors.py
+-- types.py
+-- pagination.py
+-- protocols.py
```

---

# 10. Import ergonomics

Préférer :

```python
from pyaccountingkit import AccountingApplication, Money
```

et :

```python
from pyaccountingkit.public import ...
```

pour extensions avancées.

---

# 11. `__all__`

La racine du package doit déclarer explicitement :

```python
__all__ = [
    "AccountingApplication",
    "Money",
    ...
]
```

---

# 12. Ne pas exposer tout `domain.*`

Les internals restent accessibles pour contributeurs mais non garantis stables.

---

# 13. Surface publique stable

Les objets déclarés publics sont :

```text
documented
typed
tested
versioned
```

---

# 14. Surface interne

Les modules :

```text
_internal
adapters
application internals
domain implementation details
```

peuvent évoluer plus librement.

---

# 15. Public API Manifest

À partir de RC :

```text
PUBLIC_API_MANIFEST.json
```

doit lister les symboles publics.

---

# 16. `ReferenceAPI`

Exemple :

```python
class ReferenceAPI:
    def get_standard(...)
    def list_standards(...)
    def get_structure(...)
    def get_effective_plan(...)
    def get_reporting_model(...)
    def create_snapshot(...)
```

---

# 17. Usage référence

```python
pcg = accounting.references.get_standard(
    standard_id="fr-pcg",
    edition="2026",
)
```

---

# 18. Snapshot référence

```python
snapshot = accounting.references.create_snapshot(
    standard_id="fr-pcg",
    edition="2026",
)
```

---

# 19. API reference read-only

La façade référence ne modifie pas les datasets réglementaires.

---

# 20. `ChartsAPI`

Méthodes principales :

```python
create(...)
generate_from_reference(...)
add_account(...)
activate_account(...)
deactivate_account(...)
bind_reference(...)
validate(...)
activate(...)
migrate(...)
get(...)
search_accounts(...)
```

---

# 21. Exemple chart

```python
chart = accounting.charts.create(
    entity_id=entity_id,
    code="MAIN",
    account_code_policy=NumericVariableLengthPolicy(...),
)
```

---

# 22. Génération depuis référentiel

```python
draft = accounting.charts.generate_from_reference(
    entity_id=entity_id,
    reference_snapshot=reference_snapshot,
    generation_policy=policy,
)
```

---

# 23. Ajout de compte

```python
account = accounting.charts.add_account(
    chart_id=chart.id,
    code="51200101",
    label="Banque principale",
)
```

---

# 24. Mapping réglementaire

```python
accounting.charts.bind_reference(
    company_account_id=account.id,
    reference_account_id="account:fr-pcg:2026:512",
)
```

---

# 25. `EntriesAPI`

Méthodes :

```python
create(...)
add_line(...)
remove_line(...)
validate(...)
post(...)
reverse(...)
get(...)
list(...)
```

---

# 26. Create entry

```python
entry = accounting.entries.create(
    entity_id=entity_id,
    journal_id=journal_id,
    accounting_date=date(2026, 9, 9),
    description="Facture fournisseur",
)
```

---

# 27. Add line

```python
accounting.entries.add_line(
    entry_id=entry.id,
    account_id=expense_account.id,
    debit=Money("100.00", "EUR"),
)
```

---

# 28. Add credit

```python
accounting.entries.add_line(
    entry_id=entry.id,
    account_id=payable_account.id,
    credit=Money("100.00", "EUR"),
)
```

---

# 29. Validate

```python
validated = accounting.entries.validate(
    entry_id=entry.id,
)
```

---

# 30. Post

```python
posted = accounting.entries.post(
    entry_id=entry.id,
)
```

---

# 31. Reverse

```python
reversal = accounting.entries.reverse(
    entry_id=posted.id,
    reversal_date=date(2026, 9, 10),
    reason="Correction",
)
```

---

# 32. No direct mutation after posted

L'API ne doit pas offrir :

```python
posted.lines.append(...)
```

comme mutation supported.

---

# 33. `LedgerAPI`

Queries :

```python
journal(...)
general_ledger(...)
trial_balance(...)
account_balance(...)
entry_history(...)
```

---

# 34. Journal

```python
page = accounting.ledger.journal(
    entity_id=entity_id,
    date_from=...,
    date_to=...,
)
```

---

# 35. General Ledger

```python
ledger = accounting.ledger.general_ledger(
    entity_id=entity_id,
    account_id=account_id,
    date_from=...,
    date_to=...,
)
```

---

# 36. Trial Balance

```python
tb = accounting.ledger.trial_balance(
    entity_id=entity_id,
    period_id=period_id,
    variant="ADJUSTED",
)
```

---

# 37. Trial Balance Snapshot

```python
snapshot = accounting.ledger.snapshot_trial_balance(
    entity_id=entity_id,
    period_id=period_id,
    variant="ADJUSTED",
)
```

---

# 38. Query objects

Support possible :

```python
query = TrialBalanceQueryRequest(...)
result = accounting.ledger.trial_balance(query)
```

pour appels avancés.

---

# 39. `ClosingAPI`

Méthodes :

```python
start_review(...)
generate_adjustments(...)
validate(...)
close(...)
reopen(...)
status(...)
create_snapshot(...)
```

---

# 40. Close

```python
result = accounting.closing.close(
    period_id=period_id,
    expected_revision=revision,
)
```

---

# 41. Reopen

```python
result = accounting.closing.reopen(
    period_id=period_id,
    reason="Adjustment after audit review",
)
```

---

# 42. `ControlsAPI`

Méthodes :

```python
run(...)
evaluate(...)
get_run(...)
list_findings(...)
gate(...)
```

---

# 43. Run controls

```python
run = accounting.controls.run(
    control_set="PERIOD_CLOSE",
    entity_id=entity_id,
    period_id=period_id,
)
```

---

# 44. Gate

```python
decision = accounting.controls.gate(
    gate_code="PERIOD_CLOSE_GATE",
    context=...,
)
```

---

# 45. `ImportsAPI`

Méthodes :

```python
create(...)
preflight(...)
discover(...)
map_account(...)
map_journal(...)
validate(...)
build_plan(...)
approve(...)
execute(...)
trace(...)
reprocess(...)
```

---

# 46. FEC import

```python
batch = accounting.imports.create(
    entity_id=entity_id,
    adapter="fec",
    source=file_ref,
    purpose="MIGRATION",
)
```

---

# 47. Preflight

```python
preflight = accounting.imports.preflight(
    batch_id=batch.id,
)
```

---

# 48. Mapping account

```python
accounting.imports.map_account(
    batch_id=batch.id,
    source_account_code="512001",
    company_account_id=bank.id,
)
```

---

# 49. Build plan

```python
plan = accounting.imports.build_plan(
    batch_id=batch.id,
)
```

---

# 50. Execute

```python
result = accounting.imports.execute(
    batch_id=batch.id,
    expected_plan_checksum=plan.checksum,
)
```

---

# 51. `StatementsAPI`

Méthodes :

```python
build(...)
preview(...)
snapshot(...)
publish(...)
drilldown(...)
compare(...)
```

---

# 52. Build statement

```python
result = accounting.statements.build(
    entity_id=entity_id,
    statement="balance_sheet",
    source=trial_balance_snapshot,
    mapping_set=mapping_set,
)
```

---

# 53. Snapshot report

```python
snapshot = accounting.statements.snapshot(
    result=result,
)
```

---

# 54. Drill-down

```python
details = accounting.statements.drilldown(
    snapshot_id=snapshot.id,
    line_id="BS-A100",
)
```

---

# 55. `RegulatoryReportingAPI`

Méthodes :

```python
create_profile(...)
activate_profile(...)
build_report(...)
validate_report(...)
export(...)
plan_upgrade(...)
```

---

# 56. Create profile

```python
profile = accounting.reporting.create_profile(
    entity_id=entity_id,
    standard_id="fr-pcg",
    edition="2026",
    reference_snapshot=reference_snapshot,
)
```

---

# 57. Export

```python
artifact = accounting.reporting.export(
    snapshot_id=report_snapshot.id,
    export_definition="statutory-json-v1",
)
```

---

# 58. `FinancialAnalysisAPI`

Méthodes :

```python
define_indicator(...)
define_ratio(...)
create_definition_set(...)
activate_definition_set(...)
run(...)
snapshot(...)
drilldown(...)
trend(...)
diagnostic(...)
```

---

# 59. Run analysis

```python
analysis = accounting.analysis.run(
    entity_id=entity_id,
    source_snapshot_ids=(report_snapshot.id,),
    definition_set_id=definition_set.id,
)
```

---

# 60. Trend

```python
trend = accounting.analysis.trend(
    metric_code="NET_MARGIN",
    snapshot_ids=(s1.id, s2.id, s3.id),
)
```

---

# 61. `SubledgersAPI`

Sous-façades :

```text
accounting.subledgers.partners
accounting.subledgers.receivables
accounting.subledgers.payables
accounting.subledgers.settlements
accounting.subledgers.matching
```

---

# 62. Receivable

```python
receivable = accounting.subledgers.receivables.recognize(
    entity_id=entity_id,
    partner_id=customer.id,
    document=document,
)
```

---

# 63. Settlement

```python
settlement = accounting.subledgers.settlements.record(
    entity_id=entity_id,
    partner_id=customer.id,
    amount=Money("500.00", "EUR"),
    settlement_date=date(2026, 9, 9),
)
```

---

# 64. Allocation

```python
allocation = accounting.subledgers.settlements.allocate(
    settlement_id=settlement.id,
    due_item_id=due_item.id,
    amount=Money("500.00", "EUR"),
)
```

---

# 65. Reconciliation

```python
reconciliation = accounting.subledgers.reconcile(
    entity_id=entity_id,
    subledger_type="accounts_receivable",
    control_account_id=control_account.id,
    as_of=date(2026, 12, 31),
)
```

---

# 66. DTOs publics

Les réponses publiques complexes utilisent des DTOs immuables.

Exemples :

```text
JournalEntryDTO
JournalLineDTO
TrialBalanceDTO
ReportSnapshotDTO
AnalysisSnapshotDTO
ImportPreflightDTO
SubledgerReconciliationDTO
```

---

# 67. DTO != Aggregate

Un DTO peut exposer une vue simplifiée.

---

# 68. Immutabilité DTO

Recommandation :

```python
@dataclass(frozen=True, slots=True)
```

---

# 69. Pydantic ?

Ne pas rendre Pydantic obligatoire dans le core.

Peut exister comme adapter/extra.

---

# 70. Dataclasses publiques

Default P1 :

```text
stdlib dataclasses
```

---

# 71. Value Objects publics

Exemples :

```text
Money
CurrencyCode
AccountingDate
AccountCode
Revision
IdempotencyKey
```

---

# 72. `Money`

```python
amount = Money("123.45", "EUR")
```

---

# 73. Interdit

```python
Money(123.45, "EUR")
```

si float rejeté.

---

# 74. Type aliases

Utiliser des NewTypes / classes IDs stables :

```text
JournalEntryId
CompanyAccountId
AccountingPeriodId
ReportSnapshotId
```

---

# 75. IDs comme strings ?

La représentation interne peut être str/UUID/ULID, mais le type public doit rester explicite.

---

# 76. `Result` wrappers ?

P1 recommande exceptions pour erreurs métiers attendues et DTOs pour succès.

Pas de wrapper universel :

```text
Result[T, E]
```

obligatoire.

---

# 77. Pourquoi

Python idiomatique :

```text
return object

raise typed exception
```

---

# 78. Exceptions publiques

Racine :

```text
PyAccountingKitError
```

---

# 79. Taxonomie

```text
PyAccountingKitError
|
+-- ValidationError
+-- AccountingInvariantError
+-- PolicyResolutionError
+-- ReferenceDataError
+-- PersistenceError
+-- ConcurrencyConflictError
+-- IdempotencyConflictError
+-- ImportError
+-- ReportingError
+-- FinancialAnalysisError
+-- SubledgerError
```

---

# 80. Error codes

Chaque erreur publique importante doit exposer :

```text
code
message
context
retryable?
```

---

# 81. `PublicErrorInfo`

```text
PublicErrorInfo
|
+-- code
+-- message
+-- retryable
+-- details
```

---

# 82. No raw DB detail

Interdit :

```text
duplicate key value violates unique constraint ...
```

dans message public par défaut.

---

# 83. Machine-readable errors

Exemple :

```text
ENTRY_NOT_BALANCED
PERIOD_CLOSED
ACCOUNT_NOT_ACTIVE
CONCURRENCY_CONFLICT
IMPORT_PLAN_STALE
```

---

# 84. Stable error codes

Un changement de code d'erreur peut être breaking.

---

# 85. Error context

Exemple :

```python
except PeriodClosedError as exc:
    exc.period_id
    exc.code
```

---

# 86. Retryability

Exposer :

```text
retryable = true
```

pour :

```text
lock timeout
transient persistence
```

---

# 87. Pagination

Public model :

```text
Page[T]
├─ items
├─ page_size
├─ total?
├─ next_cursor?
└─ previous_cursor?
```

---

# 88. Cursor-first

Pour ledger/open items gros volumes :

```text
cursor pagination
```

recommandée.

---

# 89. Sort conventions

Tout query paginé doit documenter un ordre stable.

---

# 90. Filter objects

Préférer objets typés pour queries complexes :

```text
LedgerFilter
ImportBatchFilter
OpenItemFilter
```

---

# 91. Avoid kwargs explosion

Si une méthode dépasse plusieurs critères :

```python
accounting.ledger.general_ledger(
    LedgerQuery(...)
)
```

préférable.

---

# 92. Request DTOs

```text
CreateEntryRequest
PostEntryRequest
TrialBalanceRequest
BuildReportRequest
RunAnalysisRequest
```

---

# 93. Simple call ergonomics

Pour les usages courants, accepter keyword args directs.

---

# 94. Advanced request object

Pour usage complexe, accepter un objet request.

---

# 95. Convention P1

Une méthode ne doit pas supporter deux signatures ambiguës.

---

# 96. Command API

Pattern :

```text
verb + noun
```

Exemples :

```text
create
validate
post
reverse
close
reopen
execute
publish
activate
```

---

# 97. Query API

Pattern :

```text
get
list
search
journal
trial_balance
drilldown
trend
```

---

# 98. Idempotency key public

Certaines commandes acceptent :

```python
idempotency_key="..."
```

---

# 99. Exemple posting

```python
posted = accounting.entries.post(
    entry_id=entry.id,
    idempotency_key="post-entry-123",
)
```

---

# 100. Idempotency optional?

Dépend du contexte.

Pour intégrations externes :

```text
strongly recommended
```

---

# 101. Expected revision

Les mutations concurrentes peuvent accepter :

```python
expected_revision=4
```

---

# 102. Exemple

```python
accounting.entries.validate(
    entry_id=entry.id,
    expected_revision=entry.revision,
)
```

---

# 103. Pessimistic locking not public

L'utilisateur ne choisit pas :

```text
FOR_UPDATE
```

dans l'API publique ordinaire.

---

# 104. Transaction boundary not public

Pas de :

```python
with accounting.transaction():
```

dans l'API de base.

---

# 105. Extension API avancée

Un mode expert peut exposer :

```text
UnitOfWorkFactory
Repository protocols
```

dans :

```text
pyaccountingkit.public.protocols
```

---

# 106. Distinction API user / adapter author

```text
User API
    simple façades

Extension API
    protocols / ports
```

---

# 107. Extension API stability

Les ports publics doivent être versionnés comme extension contracts.

---

# 108. `AdapterContractVersion`

Exposé pour adapter authors.

---

# 109. Async boundary

P1 API :

```text
sync
```

---

# 110. Future async

Ne pas transformer une méthode sync en coroutine dans une minor release.

---

# 111. Future shape

Possible :

```python
AsyncAccountingApplication
```

---

# 112. Alternative

Namespace séparé :

```text
pyaccountingkit.asyncio
```

---

# 113. P1 recommandation

Prévoir :

```text
AsyncAccountingApplication
```

future, sans compromettre le sync API.

---

# 114. No sync-over-async hidden runtime

---

# 115. No async-over-sync blocking surprise

---

# 116. Context objects

Pour les commandes, un contexte transverse peut être fourni :

```text
CommandContext
|
+-- actor
+-- correlation_id
+-- request_id?
+-- idempotency_key?
+-- metadata
```

---

# 117. Usage

```python
context = CommandContext(
    actor=actor,
    correlation_id="...",
)
```

---

# 118. API context optional

Peut être passé :

```python
accounting.entries.post(..., context=context)
```

---

# 119. Actor

L'API ne fait pas l'authentification.

Elle accepte une identité déjà résolue.

---

# 120. Authorization

Application concern.

---

# 121. Correlation ID

Fortement recommandé pour audit/trace.

---

# 122. API defaults

Les defaults doivent être :

```text
safe
explicit
non-magical
```

---

# 123. Fail closed

Pas de fallback implicite vers :

```text
default entity
default period
default account
```

si ambiguity.

---

# 124. Default currency

Peut être résolue via entity config si explicitement définie.

---

# 125. Default standard

Même règle.

---

# 126. Default period

Pas recommandé pour mutations.

---

# 127. Dates obligatoires

Pour opérations comptables :

```text
accounting_date
```

doit être explicite ou policy-driven de manière documentée.

---

# 128. Clock

Le framework ne demande pas à l'utilisateur de passer `now` partout.

`Clock` est injecté.

---

# 129. Serialization

Public DTOs doivent avoir une sérialisation stable.

---

# 130. JSON adapter

Optional helper :

```python
accounting.serialization.to_json(...)
```

ou package séparé.

---

# 131. Canonical serialization

Important pour :

```text
snapshots
checksums
replay
```

---

# 132. Public DTO JSON

Ne garantit pas nécessairement même format que canonical snapshot schema.

---

# 133. API schema versions

Les payloads persistés/exportés doivent inclure :

```text
schema_version
```

---

# 134. Backward compatibility

P1 policy recommandée :

```text
public Python API:
    semver

serialized snapshots:
    versioned schema

adapter contracts:
    explicit contract version
```

---

# 135. Breaking changes

Examples :

```text
remove public method
rename public error code
change method return meaning
change public DTO field requiredness
change default semantics
```

---

# 136. Non-breaking

Examples :

```text
add optional method
add optional field with default
add new error subclass
add new enum member if forward-compatible
```

---

# 137. Enum evolution

Attention :

```text
match/case exhaustive users
```

peuvent casser si new enum member.

Documenter.

---

# 138. String codes vs Python Enum

Pour plugin/extensibility-heavy concepts, typed string codes peuvent être plus compatibles.

---

# 139. Recommendation

Use Enum for stable closed sets.

Use Code/ValueObject for extensible registries.

---

# 140. Public dataclass evolution

Ajouter un champ obligatoire est breaking.

---

# 141. Optional fields

Peuvent être ajoutés avec default.

---

# 142. Return objects

Préférer DTOs nommés plutôt que tuples.

---

# 143. No raw dict as primary API

Éviter :

```python
return {"status": ...}
```

pour core API.

---

# 144. `Mapping[str, Any]`

Réservé aux metadata.

---

# 145. Metadata

Doit rester :

```text
non-structural
```

---

# 146. Public protocol examples

```python
class AccountingReferenceProvider(Protocol):
    ...

class UnitOfWorkFactory(Protocol):
    ...

class ReportRenderer(Protocol):
    ...

class RegulatoryExporter(Protocol):
    ...
```

---

# 147. Adapter author API

Location :

```text
pyaccountingkit.public.protocols
```

---

# 148. Do not import internal adapters from public protocols

---

# 149. Dependency optionality

Core install :

```bash
pip install pyaccountingkit
```

---

# 150. Django extra

```bash
pip install pyaccountingkit[django]
```

---

# 151. SQLAlchemy extra

```bash
pip install pyaccountingkit[sqlalchemy]
```

---

# 152. All

```bash
pip install pyaccountingkit[all]
```

optional.

---

# 153. Import without extras

```python
import pyaccountingkit
```

must succeed without Django/SQLAlchemy.

---

# 154. Adapter missing dependency

Should raise clear:

```text
OptionalDependencyMissingError
```

---

# 155. Framework-neutral DTOs

Never import from Django/Pydantic required in public dataclasses.

---

# 156. Validation in API boundary

Public API validates:

```text
types
required fields
basic shape
```

before domain invocation.

---

# 157. Domain validation remains authoritative

---

# 158. Input coercion

Avoid aggressive coercion.

---

# 159. Money coercion

Do not accept float silently.

---

# 160. Date coercion

Can accept:

```text
date
```

primarily.

Optional parser helpers can accept strings.

---

# 161. String IDs

Can accept typed IDs or str and normalize safely if documented.

---

# 162. API strictness

P1 recommendation:

```text
typed inputs preferred
small safe coercions only
```

---

# 163. Error wrapping

Public façade catches infrastructure exceptions and maps them.

---

# 164. Do not catch all and hide

Unknown exception should preserve debugging context.

---

# 165. `cause`

Public error can preserve:

```python
raise PersistenceUnavailableError(...) from exc
```

---

# 166. Logging

Public API should not log every error by itself.

Runtime/application integration owns logging.

---

# 167. API tracing hooks

Optional:

```text
CommandObserver
QueryObserver
```

future.

---

# 168. Event hooks

Domain events published after commit.

---

# 169. Public event subscription

Future interface:

```python
accounting.events.subscribe(...)
```

not required P1.

---

# 170. No in-process event bus mandatory

---

# 171. Discoverability

Each sub-API should expose coherent verbs.

Bad:

```text
accounting.do_posting_thing
```

Good:

```text
accounting.entries.post
```

---

# 172. Naming conventions

Python:

```text
snake_case methods
PascalCase types
UPPER_CASE enum values
```

---

# 173. IDs

Use suffix:

```text
*_id
```

---

# 174. Snapshots

Use suffix:

```text
*_snapshot
```

or type object.

---

# 175. Checksums

Use explicit:

```text
checksum
plan_checksum
source_checksum
```

---

# 176. Versions

Use explicit:

```text
definition_version
adapter_version
reference_snapshot
```

---

# 177. Mutation returns

A mutation should return:

```text
updated object / result DTO
```

not only `True`.

---

# 178. Boolean returns

Use for pure predicates, not commands.

---

# 179. Command result examples

```text
PostEntryResult
ClosePeriodResult
ExecuteImportResult
PublishReportResult
```

---

# 180. `PostEntryResult`

```text
entry_id
status
posting_sequence
revision
audit_ref?
```

---

# 181. `ReverseEntryResult`

```text
original_entry_id
reversal_entry_id
status
```

---

# 182. `ClosePeriodResult`

```text
period_id
status
close_revision
control_run_refs
snapshot_refs
```

---

# 183. Query consistency visibility

Queries may expose:

```text
freshness
watermark
```

when relevant.

---

# 184. `QueryMetadata`

```text
freshness
source_watermark
generated_at
```

---

# 185. Report query

Should expose source snapshot refs.

---

# 186. Async jobs

Some large operations may eventually run async:

```text
import
report export
large reconciliation
```

---

# 187. P1 synchronous API semantics

Can still return:

```text
JobRef
```

if runtime chooses an async adapter, but default core should remain deterministic.

---

# 188. Recommendation

Do not bake background job semantics into domain API P1.

---

# 189. Bulk APIs

Possible:

```python
accounting.entries.create_many(...)
```

future.

---

# 190. Avoid broad generic bulk mutation

No:

```text
save_all(objects)
```

---

# 191. Import is the dedicated bulk path

---

# 192. Context manager API

No mandatory transaction context.

---

# 193. Advanced extension

Adapter authors may use UoW directly.

---

# 194. Testing public API

All README/example workflows must use public façade, not internals.

---

# 195. Public API contract tests

Examples:

```text
create / validate / post / reverse
trial balance
FEC preflight
report snapshot
analysis snapshot
subledger settlement
```

---

# 196. Golden API scenarios

At least one full scenario:

```text
create entity/chart
create accounts
create entry
post
trial balance
statement
analysis
```

---

# 197. Public import smoke

```python
from pyaccountingkit import AccountingApplication, Money
```

must succeed in core-only environment.

---

# 198. Optional dependency smoke

```text
core only
django extra
sqlalchemy extra
```

---

# 199. API docs

Every public method documents:

```text
purpose
inputs
outputs
errors
idempotency
concurrency
examples
```

---

# 200. Error docs

Public error codes should have reference documentation.

---

# 201. API stability labels

Possible:

```text
EXPERIMENTAL
STABLE
DEPRECATED
INTERNAL
```

---

# 202. Experimental API

May evolve within minor releases if documented.

---

# 203. Stable API

Semver guarantees.

---

# 204. Deprecated API

Must emit:

```text
DeprecationWarning
```

or framework-specific warning.

---

# 205. Deprecation window

At least one minor release recommended before removal.

---

# 206. Removal

Only major release, except pre-1.0 policy if explicitly documented.

---

# 207. Pre-1.0 policy

PyAccountingKit can still treat:

```text
0.x minor
```

as breaking if SemVer convention is adopted.

But API freeze before RC should minimize this.

---

# 208. Version endpoint

Expose:

```python
pyaccountingkit.__version__
```

---

# 209. Runtime info

Optional:

```python
accounting.runtime_info()
```

---

# 210. `RuntimeInfo`

```text
framework_version
adapter_versions
contract_version
python_version
```

---

# 211. Capabilities

Public advanced method:

```python
accounting.capabilities()
```

---

# 212. `ApplicationCapabilities`

```text
persistence
reference
import_adapters
renderers
exporters
```

---

# 213. Why

Helps plugin/runtime integration.

---

# 214. Not for business logic

Business semantics still use policies.

---

# 215. Dependency injection

Constructor injection preferred.

---

# 216. No global service locator

---

# 217. No hidden singleton DB connection

---

# 218. Thread safety

`AccountingApplication` may be long-lived if its dependencies are factories and stateless.

UoW/session remains request/command scoped.

---

# 219. Worker safety

Each command opens its own UoW.

---

# 220. Web framework adapters

Possible integrations:

```text
Django
FastAPI
Flask
CLI
Celery
```

---

# 221. HTTP API

Not part of `pyaccountingkit` core public Python API.

Can be built on top.

---

# 222. FastAPI extension

Possible future:

```text
pyaccountingkit-fastapi
```

---

# 223. Django integration

Possible helper:

```text
pyaccountingkit.integrations.django
```

but not required for core use.

---

# 224. CLI

Could use same public façade.

---

# 225. Notebook

Same.

---

# 226. Command naming examples

Good:

```text
entries.create
entries.validate
entries.post
entries.reverse

closing.close
closing.reopen

imports.preflight
imports.execute

statements.build
statements.publish

analysis.run
analysis.snapshot
```

---

# 227. Avoid redundant names

Bad:

```text
accounting.entries.post_entry()
```

Prefer:

```text
accounting.entries.post()
```

---

# 228. API return immutability

DTOs and snapshots read-only.

---

# 229. Domain aggregate return

If exposed, mutation methods should remain internal or safe.

---

# 230. Recommendation

User API returns DTOs/results, not mutable aggregates, for most operations.

---

# 231. Why

Protects transaction boundaries and invariants.

---

# 232. `EntryView`

Public DTO can represent JournalEntry.

---

# 233. `CompanyAccountView`

Same.

---

# 234. `PeriodView`

Same.

---

# 235. Advanced domain imports

Contributors can import domain types explicitly from:

```text
pyaccountingkit.domain
```

without stability guarantee before 1.0.

---

# 236. Public DTO naming

Use suffix:

```text
View
Result
Request
Page
Snapshot
```

---

# 237. Avoid `DTO` suffix everywhere

Can be internal naming.

Public names should be ergonomic.

---

# 238. Examples

```text
EntryView
TrialBalanceView
ImportPreflightResult
ReportSnapshot
AnalysisSnapshot
```

---

# 239. Snapshot types can be domain/public

Immutable snapshot objects can be stable public types.

---

# 240. Protocol versioning

```text
PORT_CONTRACT_VERSION = "1"
```

---

# 241. Adapter author conformance

Custom adapter declares:

```text
supported_contract_version
```

---

# 242. Startup validation

If incompatible:

```text
AdapterContractMismatchError
```

---

# 243. Feature capability

Adapter may expose:

```text
supports_pessimistic_locking
supports_transactional_outbox
```

---

# 244. User API hides implementation choice

---

# 245. Persistence configuration

Example helper:

```python
accounting = AccountingApplication.from_sqlalchemy(
    session_factory=...
)
```

Should this exist?

---

# 246. Recommendation

Keep convenience constructors in adapter packages:

```python
from pyaccountingkit.adapters.sqlalchemy import create_accounting_application
```

not in core façade.

---

# 247. Django convenience

```python
from pyaccountingkit.adapters.django import create_accounting_application
```

---

# 248. This prevents core import coupling

---

# 249. API examples - end-to-end accounting

```python
account = accounting.charts.add_account(...)

entry = accounting.entries.create(
    entity_id=entity_id,
    journal_id=journal_id,
    accounting_date=date(2026, 9, 9),
    description="Operation",
)

accounting.entries.add_line(
    entry_id=entry.id,
    account_id=debit_account.id,
    debit=Money("100.00", "EUR"),
)

accounting.entries.add_line(
    entry_id=entry.id,
    account_id=credit_account.id,
    credit=Money("100.00", "EUR"),
)

accounting.entries.validate(entry_id=entry.id)
posted = accounting.entries.post(entry_id=entry.id)
```

---

# 250. API examples - reporting

```python
tb = accounting.ledger.snapshot_trial_balance(
    entity_id=entity_id,
    period_id=period_id,
    variant="ADJUSTED",
)

report = accounting.statements.build(
    entity_id=entity_id,
    statement="balance_sheet",
    source=tb,
    mapping_set=mapping_set,
)

snapshot = accounting.statements.snapshot(result=report)
```

---

# 251. API examples - analysis

```python
analysis = accounting.analysis.run(
    entity_id=entity_id,
    source_snapshot_ids=(snapshot.id,),
    definition_set_id=definition_set.id,
)
```

---

# 252. API examples - subledger

```python
receivable = accounting.subledgers.receivables.recognize(...)

payment = accounting.subledgers.settlements.record(...)

accounting.subledgers.settlements.allocate(
    settlement_id=payment.id,
    due_item_id=receivable.due_items[0].id,
    amount=Money("500.00", "EUR"),
)
```

---

# 253. Public API anti-patterns

Interdit :

```python
entry_model = JournalEntryModel.objects.get(...)
entry_model.status = "POSTED"
entry_model.save()
```

---

# 254. Interdit

```python
session.query(JournalEntry).filter(...).update(...)
```

comme workflow utilisateur.

---

# 255. Interdit

```python
accounting.repository("JournalEntry").save(...)
```

dans API utilisateur.

---

# 256. Interdit

```python
accounting.transaction.atomic(...)
```

---

# 257. Interdit

```python
accounting.run_sql(...)
```

---

# 258. Interdit

```python
accounting.imports.fec.parser._parse_line(...)
```

comme API publique.

---

# 259. API test matrix

| Surface | Unit | Contract | Integration | Public Smoke |
|---|---:|---:|---:|---:|
| references | oui | oui | oui | oui |
| charts | oui | oui | oui | oui |
| entries | oui | oui | oui | oui |
| ledger | oui | query | oui | oui |
| closing | oui | oui | oui | oui |
| controls | oui | oui | oui | oui |
| imports | oui | oui | oui | oui |
| statements | oui | oui | oui | oui |
| reporting | oui | oui | oui | oui |
| analysis | oui | oui | oui | oui |
| subledgers | oui | oui | oui | oui |

---

# 260. Public API release gates

Avant RC :

```text
all public symbols documented

all public methods typed

all error codes documented

all examples executable

manifest generated

no accidental internal exports
```

---

# 261. Stable release gate

```text
public API manifest frozen

breaking diff = 0

adapter contract compatible

README examples green

core-only install green
```

---

# 262. `PUBLIC_API_MANIFEST.json`

Exemple :

```json
{
  "version": "1",
  "symbols": [
    "pyaccountingkit.AccountingApplication",
    "pyaccountingkit.Money",
    "pyaccountingkit.public.errors.PeriodClosedError"
  ]
}
```

---

# 263. `PUBLIC_ERROR_CODES.json`

Possible artifact :

```text
ENTRY_NOT_BALANCED
PERIOD_CLOSED
ACCOUNT_NOT_ACTIVE
IMPORT_PLAN_STALE
CONCURRENCY_CONFLICT
```

---

# 264. `PORT_CONTRACT_MANIFEST.json`

Pour adapter authors.

---

# 265. Docs generation

API docs can be built via :

```text
mkdocstrings
Sphinx
pdoc
```

without making tool choice part of semantic contract.

---

# 266. Docstrings

Public methods require meaningful docstrings.

---

# 267. Examples in docstrings

Prefer short, tested examples.

---

# 268. Type check for users

Published package should include:

```text
py.typed
```

---

# 269. PEP 561

Recommended.

---

# 270. API discoverability IDE

Type hints + docstrings enable IDE support.

---

# 271. Generic Page typing

```python
Page[EntryView]
```

---

# 272. Protocol typing

Runtime checkable only if needed.

---

# 273. `typing.Protocol`

Preferred for ports.

---

# 274. Avoid runtime ABC inheritance if unnecessary

---

# 275. Validation helpers

Public helper modules may provide :

```text
parse_account_code
parse_money
```

but should not become magical coercion in main API.

---

# 276. Extension registries

Potential stable APIs :

```text
register_import_adapter
register_metric_definition
register_report_renderer
```

---

# 277. Registry ownership

Prefer application instance scoped registry, not global registry.

---

# 278. Example

```python
accounting.imports.register_adapter(custom_adapter)
```

---

# 279. Plugin discovery

P2 could support entry points.

---

# 280. Avoid automatic plugin side effects at import

---

# 281. Public event schemas

If domain events exposed externally, version them separately.

---

# 282. Event schema version

```text
event_schema_version
```

---

# 283. Public domain event stability

Not guaranteed unless explicitly declared.

---

# 284. API deprecation example

Old:

```python
accounting.entries.finalize(...)
```

New:

```python
accounting.entries.post(...)
```

Old emits warning then removed in major release.

---

# 285. Strict semver after 1.0

Recommended.

---

# 286. 0.x strategy

Document in `17_RELEASE_AND_VERSIONING_STRATEGY`.

---

# 287. Error compatibility

Subclasses may be added non-breaking.

Renaming root errors is breaking.

---

# 288. Error message text

Not considered stable API.

---

# 289. Error code

Stable.

---

# 290. Public status enums

Values are contract.

---

# 291. Internal enum mapping

Adapters map DB strings to public enums.

---

# 292. Serialization compatibility

Public enums serialize as stable strings.

---

# 293. Decimal serialization

Always string in JSON helpers.

---

# 294. Date serialization

ISO 8601.

---

# 295. None semantics

Use `None` for absent optional values.

---

# 296. Avoid sentinel strings

No:

```text
"N/A"
```

in semantic DTOs.

---

# 297. Undefined metric

Use status enum, not string value.

---

# 298. Money absent

`None`, not zero.

---

# 299. Tolerance semantics

Explicit objects where needed.

---

# 300. Immutable request objects?

Can be frozen dataclasses.

---

# 301. Mutability

Requests can be immutable to simplify traceability.

---

# 302. `CommandContext`

Also frozen.

---

# 303. Public clock?

Clock is extension/injection API.

---

# 304. Public IdFactory?

Same.

---

# 305. Testing helpers

Future:

```text
pyaccountingkit.testing
```

---

# 306. Stable testing API

Not required P1, but adapter contract kit may become public.

---

# 307. Interactive environments

API should work in notebook/REPL.

---

# 308. Avoid mandatory async/event loop

---

# 309. Avoid mandatory web settings

---

# 310. Avoid mandatory environment variables

---

# 311. Configuration object

Possible :

```text
AccountingApplicationConfig
```

---

# 312. `AccountingApplicationConfig`

```text
default_currency?
strictness
feature_flags
```

---

# 313. No business policy hidden in global config

Accounting policies remain explicit/versioned.

---

# 314. Feature flags

Only for technical/experimental capabilities.

---

# 315. Public application metadata

```python
accounting.info()
```

may expose :

```text
framework version
capabilities
```

---

# 316. Health

Infrastructure-specific health check not part of accounting domain API.

---

# 317. Adapter health

Can be extension API.

---

# 318. Transactions and retries

User-facing command may raise:

```text
ConcurrencyConflictError
LockTimeoutError
```

---

# 319. Automatic retries

Should not be invisible if they could change timing/side effects.

---

# 320. Runtime policy may retry idempotent commands

---

# 321. Public retry hint

Error:

```text
retryable = true
```

---

# 322. Long operations

Could expose progress future.

---

# 323. P1 no mandatory streaming API

---

# 324. Import raw source

Source can be:

```text
ArtifactRef
file-like adapter input
connector reference
```

depending adapter.

---

# 325. Core public API should not hardcode local filesystem paths

---

# 326. `ArtifactRef`

Public type.

---

# 327. Report export return

Returns:

```text
RegulatoryExportArtifact
```

not local path assumption.

---

# 328. Subledger external refs

Use typed:

```text
OperationalSourceRef
```

---

# 329. API boundaries summary

```text
User
  |
  v
Public Facade
  |
  v
Application Services
  |
  v
Domain
  |
  v
Ports
  |
  v
Adapters
```

---

# 330. No reverse dependency

Adapters never define the public user experience.

---

# 331. API versioning metadata

Expose:

```text
PUBLIC_API_VERSION
```

if useful.

---

# 332. Not same as package version

Could be:

```text
api_contract_version = "1"
```

---

# 333. Public API contract version

Useful for custom integration validation.

---

# 334. ADRs

| ID | Décision |
|---|---|
| ADR-API-001 | `AccountingApplication` est la façade publique principale |
| ADR-API-002 | Les bounded contexts sont exposés via sous-façades |
| ADR-API-003 | L'API publique n'expose ni ORM ni SQL |
| ADR-API-004 | L'utilisateur ordinaire ne manipule pas directement `UnitOfWork` |
| ADR-API-005 | Les mutations critiques passent par des commandes applicatives |
| ADR-API-006 | Les queries retournent des objets framework-neutral |
| ADR-API-007 | Les erreurs ORM sont traduites vers des erreurs publiques stables |
| ADR-API-008 | Les codes d'erreur publics sont stables |
| ADR-API-009 | `Money` rejette le float |
| ADR-API-010 | Les DTOs publics sont immuables par défaut |
| ADR-API-011 | Pydantic n'est pas une dépendance obligatoire du core |
| ADR-API-012 | Les ports destinés aux adapter authors sont exposés séparément |
| ADR-API-013 | L'API utilisateur et l'extension API ont des niveaux de stabilité distincts |
| ADR-API-014 | Le sync API est la cible P1 |
| ADR-API-015 | Une future API async sera distincte et non une mutation silencieuse du sync API |
| ADR-API-016 | Les dépendances Django/SQLAlchemy restent optionnelles |
| ADR-API-017 | Les convenience constructors ORM vivent dans les packages adapters |
| ADR-API-018 | Les public methods sont typées et documentées |
| ADR-API-019 | Les retours de commande sont des objets nommés, pas des booléens génériques |
| ADR-API-020 | Les queries volumineuses supportent pagination/cursors |
| ADR-API-021 | Les defaults ambiguës sont interdits |
| ADR-API-022 | L'API publique ne choisit pas les stratégies de locking SQL |
| ADR-API-023 | L'idempotence peut être fournie explicitement par command |
| ADR-API-024 | `expected_revision` peut être exposé pour optimistic concurrency |
| ADR-API-025 | La sérialisation publique et la sérialisation canonique de snapshot sont distinctes |
| ADR-API-026 | Les schemas persistés/exportés sont versionnés |
| ADR-API-027 | `PUBLIC_API_MANIFEST.json` est généré à partir de RC |
| ADR-API-028 | Les breaking API changes suivent SemVer |
| ADR-API-029 | Les exemples README utilisent exclusivement la public API |
| ADR-API-030 | Le package racine ne réexporte qu'une surface explicitement choisie |
| ADR-API-031 | `py.typed` est livré pour le typage utilisateur |
| ADR-API-032 | Les registries de plugins sont instance-scoped |
| ADR-API-033 | Les métadonnées ne remplacent pas les champs structurants |
| ADR-API-034 | Les snapshots publics publiés restent immuables |
| ADR-API-035 | Aucun framework web n'est requis pour utiliser PyAccountingKit |
| ADR-API-036 | La public API est utilisable en CLI, notebook, web et workers |
| ADR-API-037 | Les event schemas externes sont versionnés séparément si exposés |
| ADR-API-038 | Les messages d'erreur textuels ne sont pas un contrat stable, les codes le sont |
| ADR-API-039 | Les adapters ne dictent jamais la forme de la façade utilisateur |
| ADR-API-040 | Le gel de l'API publique précède la release stable |

---

# 335. Critères d'acceptation P1.5

```text
[ ] AccountingApplication défini

[ ] sous-façades publiques définies

[ ] ReferenceAPI défini

[ ] ChartsAPI défini

[ ] EntriesAPI défini

[ ] LedgerAPI défini

[ ] ClosingAPI défini

[ ] ControlsAPI défini

[ ] ImportsAPI défini

[ ] StatementsAPI défini

[ ] RegulatoryReportingAPI défini

[ ] FinancialAnalysisAPI défini

[ ] SubledgersAPI défini

[ ] API utilisateur distincte de l'extension API

[ ] aucun ORM exposé

[ ] aucun UoW exposé dans l'usage normal

[ ] DTOs immuables définis

[ ] Money public défini

[ ] public error hierarchy définie

[ ] error codes machine-readable définis

[ ] pagination publique définie

[ ] request objects définis pour appels complexes

[ ] idempotency_key public préparé

[ ] expected_revision public préparé

[ ] sync API P1 défini

[ ] future async boundary préparée

[ ] dépendances optionnelles définies

[ ] public protocol contracts définis

[ ] adapter contract version préparée

[ ] public API manifest défini

[ ] semver compatibility définie

[ ] deprecation policy définie

[ ] `py.typed` recommandé

[ ] public examples définis

[ ] core-only install compatible

[ ] contract tests publics définis
```

---

# 336. Ordre d'implémentation recommandé

## API-00 - Core public types

```text
Money
IDs
Page
CommandContext
PublicError
```

---

## API-01 - AccountingApplication

```text
main facade
composition
```

---

## API-02 - References / Charts

```text
ReferenceAPI
ChartsAPI
```

---

## API-03 - Entries / Ledger

```text
EntriesAPI
LedgerAPI
```

---

## API-04 - Closing / Controls

```text
ClosingAPI
ControlsAPI
```

---

## API-05 - Imports

```text
ImportsAPI
```

---

## API-06 - Statements / Reporting

```text
StatementsAPI
RegulatoryReportingAPI
```

---

## API-07 - Analysis

```text
FinancialAnalysisAPI
```

---

## API-08 - Subledgers

```text
SubledgersAPI
```

---

## API-09 - Error Translation

```text
public errors
stable codes
```

---

## API-10 - Public DTOs

```text
View
Request
Result
Page
```

---

## API-11 - Extension Protocols

```text
providers
renderers
exporters
uow factory
```

---

## API-12 - Manifest / Compatibility

```text
PUBLIC_API_MANIFEST
PORT_CONTRACT_MANIFEST
```

---

## API-13 - Examples / Docs / Smoke Tests

```text
README
notebook
CLI
clean install
```

---

# 337. Démonstrateur P1.5 - End-to-end

```python
accounting = AccountingApplication(...)

reference = accounting.references.get_standard(
    standard_id="fr-pcg",
    edition="2026",
)

chart = accounting.charts.generate_from_reference(
    entity_id=entity_id,
    reference_snapshot=reference_snapshot,
    generation_policy=policy,
)

entry = accounting.entries.create(
    entity_id=entity_id,
    journal_id=journal_id,
    accounting_date=date(2026, 9, 9),
    description="Test",
)

accounting.entries.add_line(
    entry_id=entry.id,
    account_id=debit_account.id,
    debit=Money("100.00", "EUR"),
)

accounting.entries.add_line(
    entry_id=entry.id,
    account_id=credit_account.id,
    credit=Money("100.00", "EUR"),
)

accounting.entries.validate(entry_id=entry.id)
accounting.entries.post(entry_id=entry.id)

tb = accounting.ledger.snapshot_trial_balance(
    entity_id=entity_id,
    period_id=period_id,
    variant="ADJUSTED",
)

report = accounting.statements.build(
    entity_id=entity_id,
    statement="balance_sheet",
    source=tb,
    mapping_set=mapping_set,
)

report_snapshot = accounting.statements.snapshot(result=report)

analysis = accounting.analysis.run(
    entity_id=entity_id,
    source_snapshot_ids=(report_snapshot.id,),
    definition_set_id=definition_set.id,
)
```

---

# 338. Démonstrateur - ORM neutrality

Le même code public doit fonctionner avec :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

sans changement des appels métier.

---

# 339. Démonstrateur - error stability

```python
try:
    accounting.entries.post(entry_id=entry.id)
except PeriodClosedError as exc:
    assert exc.code == "PERIOD_CLOSED"
```

Le backend peut être Django ou SQLAlchemy ; l'erreur publique reste identique.

---

# 340. Démonstrateur - concurrency

```python
accounting.entries.validate(
    entry_id=entry.id,
    expected_revision=4,
)
```

Si stored revision = 5 :

```text
ConcurrencyConflictError
```

---

# 341. Démonstrateur - adapter author

```python
class MyReferenceProvider(AccountingReferenceProvider):
    ...

accounting = AccountingApplication(
    reference_provider=MyReferenceProvider(),
    ...
)
```

---

# 342. Démonstrateur - core-only install

```bash
pip install pyaccountingkit
python -c "import pyaccountingkit"
```

doit fonctionner sans Django/SQLAlchemy.

---

# 343. Matrice User API / Extension API

| Capability | User API | Extension API |
|---|---:|---:|
| Create/Post Entry | **oui** | non nécessaire |
| Trial Balance | **oui** | query port possible |
| Reference Provider custom | non | **oui** |
| Renderer custom | non | **oui** |
| UoW custom | non | **oui** |
| Repository implementation | non | **oui** |
| SQL / ORM | non | adapter interne |
| Error codes | **oui** | **oui** |

---

# 344. Frontière avec le prochain document

Le prochain jalon recommandé est :

```text
17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md
```

Il devra formaliser :

```text
SemVer

0.x policy

alpha / beta / rc / stable

public API freeze

adapter contract versions

regulatory dataset compatibility

migration compatibility

deprecation policy

release gates

package publishing
```

---

# 345. Conclusion

La surface publique de PyAccountingKit devient :

```text
AccountingApplication
    |
    +--> references
    +--> charts
    +--> entries
    +--> ledger
    +--> closing
    +--> controls
    +--> imports
    +--> statements
    +--> reporting
    +--> analysis
    +--> subledgers
```

Les principes structurants sont :

```text
Public API != ORM

Public API != Repository

Public API != Transaction API

Commands are explicit

Queries return stable framework-neutral objects

Errors are typed and machine-readable

DTOs are immutable by default

Core install has no mandatory ORM dependency

Adapter authors use a separate extension API

Sync API is stable before async expansion

Public API is frozen before stable release
```

Le P1.5 définit ainsi une API Python cohérente, ergonomique et durable, capable de masquer la complexité DDD/hexagonale interne tout en conservant les garanties comptables, transactionnelles et de reproductibilité définies dans les documents précédents.

---

**Prochain document recommandé :**

```text
17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md
```


---

## Sources et références documentaires du projet

- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)

---

## Couverture dans les plans d'implémentation

Ce document est couvert par les plans suivants :

- [PLAN-05 — Public API & Adapters (0.5.0)](../../plans/PLAN-05_PUBLIC_API_ADAPTERS_0.5.0.md)
