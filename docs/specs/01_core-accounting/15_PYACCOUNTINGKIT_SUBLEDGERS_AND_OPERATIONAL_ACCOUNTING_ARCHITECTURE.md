# 15 - PyAccountingKit - Architecture des sous-livres et de la comptabilité opérationnelle

> **Projet** : PyAccountingKit  
> **Statut** : P1.4  
> **Langue** : Français  
> **Objet** : Définir les sous-livres clients, fournisseurs et auxiliaires, les échéances, règlements, allocations, lettrages, comptes collectifs, rapprochements avec le grand livre et la frontière entre événements opérationnels et écritures comptables.

Documents parents : `00` à `14` de la roadmap PyAccountingKit.

# 1. Résumé exécutif

PyAccountingKit doit supporter la comptabilité opérationnelle sans devenir un ERP complet.

```text
Operational Event
    ↓
Operational Accounting Policy
    ↓
Subledger Transaction
    ├─ Receivable
    ├─ Payable
    ├─ Due Item
    ├─ Settlement
    ├─ Allocation
    └─ Matching
    ↓
JournalEntryProposal
    ↓
Validation / Posting
    ↓
General Ledger
    ↓
Subledger ↔ GL Reconciliation
```

Principes structurants :

```text
Subledger != General Ledger
Operational Event != JournalEntry
Settlement != Allocation
Settlement != Matching
Matching != Reconciliation
BusinessPartner != CompanyAccount
AuxiliaryReference != account-code concatenation
```

# 2. Objectifs

Le bounded context doit permettre de représenter les tiers comptables, gérer les sous-livres clients/fournisseurs et auxiliaires, créer des créances et dettes, calculer des échéances, enregistrer des règlements, affecter des règlements à des open items, gérer les paiements partiels et avances, effectuer le lettrage, rapprocher sous-livre et grand livre, préserver la provenance et permettre les imports historiques.

Le framework doit également rester compatible avec plusieurs stratégies de plan auxiliaire : `SUBLEDGER`, `EXTENDED_ACCOUNT_CODE` et `HYBRID`, sans imposer une longueur de code ni une convention nationale.

# 3. Non-objectifs

PyAccountingKit ne devient pas un CRM, un logiciel complet de facturation, un système achats, un moteur de commandes, un PSP, un système de recouvrement, un moteur fiscal complet ou un ERP. Ces systèmes alimentent le framework via des adapters et événements.

# 4. Position dans l'architecture

```text
Billing / Procurement / Payments / Banking
                 ↓
      Operational Adapters
                 ↓
      Subledger Domain
                 ↓
     AccountingEvent
                 ↓
    JournalEntryProposal
                 ↓
         Posting Engine
                 ↓
       General Ledger
                 ↓
        Reconciliation
```

Le sous-livre ajoute du détail opérationnel ; le General Ledger demeure la projection canonique des écritures postées.

# 5. BusinessPartner

```text
BusinessPartner
├─ id
├─ entity_id
├─ partner_type
├─ external_ref?
├─ legal_name?
├─ display_name
├─ status
├─ default_currency?
└─ metadata
```

`BusinessPartnerType` :

```text
CUSTOMER
SUPPLIER
EMPLOYEE
LENDER
BORROWER
GOVERNMENT
RELATED_PARTY
OTHER
```

Un tiers n'est jamais un compte :

```text
BusinessPartner != CompanyAccount
```

# 6. Liaison tiers / compte collectif

```text
BusinessPartnerAccountBinding
├─ partner_id
├─ control_account_id
├─ auxiliary_mode
├─ auxiliary_reference?
├─ effective_from
├─ effective_to?
├─ status
└─ provenance
```

Modes :

```text
SUBLEDGER
EXTENDED_ACCOUNT_CODE
HYBRID
```

Dans `SUBLEDGER`, le compte collectif est partagé et le tiers est porté comme dimension auxiliaire. Dans `EXTENDED_ACCOUNT_CODE`, un compte entreprise spécifique au tiers peut être utilisé. `HYBRID` permet les deux.

# 7. AuxiliaryReference et FEC

```text
AuxiliaryReference
├─ system
├─ code
└─ label?
```

Dans l'adapter FEC :

```text
CompAuxNum -> AuxiliaryReference
```

Interdit dans le core :

```python
company_account_code = CompteNum + CompAuxNum
```

Une éventuelle concaténation dépend exclusivement de `AccountCodePolicy` / `AuxiliaryAccountingPolicy`.

# 8. OperationalDocument

```text
OperationalDocument
├─ id
├─ entity_id
├─ document_type
├─ partner_id?
├─ document_number
├─ document_date
├─ accounting_date?
├─ currency
├─ gross_amount
├─ status
├─ source_reference
└─ metadata
```

Types initiaux :

```text
SALES_INVOICE
SALES_CREDIT_NOTE
PURCHASE_INVOICE
PURCHASE_CREDIT_NOTE
PAYMENT_REQUEST
EXPENSE_CLAIM
ADVANCE
REFUND
OTHER
```

Le document opérationnel n'est pas une écriture. Il génère un `AccountingEvent`.

# 9. AccountingEvent

```text
AccountingEvent
├─ id
├─ event_type
├─ entity_id
├─ source_document_ref
├─ economic_date
├─ accounting_date
├─ partner_id?
├─ monetary_components
├─ policy_context
└─ source_provenance
```

Types :

```text
RECEIVABLE_RECOGNIZED
PAYABLE_RECOGNIZED
CREDIT_NOTE_RECOGNIZED
SETTLEMENT_RECORDED
ADVANCE_RECEIVED
ADVANCE_PAID
REFUND_RECORDED
WRITE_OFF
OTHER
```

Flux obligatoire :

```text
AccountingEvent
    ↓
OperationalAccountingPolicy
    ↓
JournalEntryProposal
    ↓
Validate
    ↓
Post
```

# 10. OperationalAccountingPolicy

```text
OperationalAccountingPolicy
├─ event_type
├─ recognition_rule
├─ account_role_mappings
├─ settlement_behavior
├─ reversal_behavior
├─ applicability
└─ version
```

Rôles génériques :

```text
CUSTOMER_RECEIVABLE_CONTROL
SUPPLIER_PAYABLE_CONTROL
REVENUE_ROLE
EXPENSE_ROLE
BANK_ROLE
CASH_ROLE
ADVANCE_RECEIVED_ROLE
ADVANCE_PAID_ROLE
```

Aucun numéro de compte national n'est hardcodé dans le core.

# 11. Receivable

```text
Receivable
├─ id
├─ entity_id
├─ partner_id
├─ source_document_ref
├─ original_amount
├─ currency
├─ accounting_date
├─ due_items
├─ status
└─ recognized_entry_id?
```

Statuts :

```text
OPEN
PARTIALLY_SETTLED
SETTLED
CANCELLED
WRITTEN_OFF
```

# 12. Payable

`Payable` suit le même pattern que `Receivable` :

```text
Payable
├─ id
├─ entity_id
├─ partner_id
├─ source_document_ref
├─ original_amount
├─ currency
├─ accounting_date
├─ due_items
├─ status
└─ recognized_entry_id?
```

# 13. DueItem et échéances

```text
DueItem
├─ id
├─ source_subledger_item_id
├─ due_date
├─ original_amount
├─ open_amount
├─ currency
├─ status
└─ payment_terms_ref?
```

Invariants :

```text
sum(due_item.original_amount)
=
receivable/payable.original_amount
```

`PaymentTerms` décrit l'échéancier opérationnel ; il ne décide pas de la reconnaissance comptable.

# 14. Settlement

```text
Settlement
├─ id
├─ entity_id
├─ partner_id?
├─ settlement_type
├─ settlement_date
├─ accounting_date
├─ amount
├─ currency
├─ source_reference
├─ status
├─ allocations
└─ posted_entry_id?
```

Types :

```text
CUSTOMER_PAYMENT
SUPPLIER_PAYMENT
REFUND
OFFSET
CASH_RECEIPT
CASH_DISBURSEMENT
OTHER
```

# 15. SettlementAllocation

```text
SettlementAllocation
├─ id
├─ settlement_id
├─ due_item_id
├─ allocated_amount
├─ currency
├─ allocation_date
├─ status
└─ provenance
```

Invariants :

```text
allocated_amount > 0
allocated_amount <= settlement_open_amount
allocated_amount <= due_item_open_amount
```

Un règlement peut couvrir plusieurs factures et une facture peut être couverte par plusieurs règlements.

# 16. Surpaiements et avances

Un règlement supérieur aux open items ne doit pas être absorbé silencieusement.

```text
UnappliedSettlement
├─ settlement_id
├─ open_amount
├─ reason
└─ classification
```

Classifications :

```text
UNAPPLIED_CASH
CUSTOMER_ADVANCE
SUPPLIER_ADVANCE
DEPOSIT
OTHER
```

Le traitement comptable dépend d'une policy explicite.

# 17. Settlement vs Posting

Un règlement crée généralement une écriture GL. Son affectation à des échéances est une opération de sous-livre.

```text
Posting
    = effet General Ledger

Allocation
    = affectation opérationnelle
```

Une allocation ne déclenche donc pas automatiquement une seconde écriture.

# 18. AccountingMatch / lettrage

```text
AccountingMatch
├─ id
├─ entity_id
├─ account_scope
├─ match_code?
├─ matched_items
├─ match_date
├─ status
├─ total_debit
├─ total_credit
├─ residual
└─ provenance
```

```text
MatchedItem
├─ journal_line_id
├─ matched_amount
├─ side
└─ source_ref?
```

Statuts :

```text
DRAFT
MATCHED
PARTIALLY_MATCHED
UNMATCHED
REVERSED
```

# 19. Settlement, Matching et Reconciliation

Ces concepts restent strictement distincts :

```text
Settlement
    = mouvement économique / règlement

Matching
    = rapprochement de mouvements comptables

Reconciliation
    = comparaison de deux sources / ensembles
```

Un paiement peut être posté mais non alloué, alloué mais non lettré, ou lettré via une credit note sans paiement.

# 20. Subledger balances

```text
SubledgerBalance
├─ entity_id
├─ partner_id?
├─ control_account_id
├─ as_of
├─ debit
├─ credit
├─ balance
├─ currency
└─ source_items
```

```text
PartnerBalance
├─ partner_id
├─ open_receivables
├─ open_payables
├─ advances
└─ net_position
```

# 21. Aging AR/AP

`AgingDefinition` :

```text
AgingDefinition
├─ reference_date
├─ buckets
├─ date_basis
├─ currency_mode
└─ version
```

Buckets exemples :

```text
CURRENT
1_30_DAYS
31_60_DAYS
61_90_DAYS
91_180_DAYS
OVER_180_DAYS
CUSTOM
```

L'aging est une projection opérationnelle. Il peut alimenter l'évaluation d'une dépréciation, mais ne contient aucune règle universelle de provisionnement.

# 22. Credit notes et write-offs

Une credit note réduit une créance/dette et produit un `JournalEntryProposal`.

```text
SubledgerWriteOff
├─ id
├─ due_item_id
├─ amount
├─ reason
├─ policy_trace
├─ journal_entry_id?
├─ approved_by?
└─ date
```

Un write-off n'est jamais une suppression ; il est explicite, tracé et comptabilisé.

# 23. SettlementAllocationPolicy

Modes :

```text
MANUAL
OLDEST_DUE_FIRST
EXACT_REFERENCE
PROPORTIONAL
CUSTOM
```

```text
SettlementAllocationPolicy
├─ mode
├─ partner_scope
├─ currency_rule
├─ tolerance
├─ effective_dates
└─ version
```

Toute auto-allocation doit être déterministe ou explicitement validée.

# 24. Allocation candidates

```text
SettlementAllocationCandidate
├─ settlement_id
├─ due_item_id
├─ proposed_amount
├─ confidence?
├─ rationale
└─ status
```

Statuts :

```text
CANDIDATE
VALIDATED
REJECTED
```

Une suggestion n'est pas une allocation active.

# 25. Tolérances, remises et résiduels

```text
SettlementTolerancePolicy
├─ absolute_tolerance
├─ relative_tolerance?
├─ currency
└─ handling
```

Handling :

```text
LEAVE_OPEN
WRITE_OFF_IF_APPROVED
ROUNDING_ADJUSTMENT
REVIEW_REQUIRED
```

Aucun résiduel n'est abandonné silencieusement.

# 26. Multi-devise

Le modèle prépare :

```text
invoice_currency
settlement_currency
functional_currency
exchange_rate_snapshot
```

```text
RealizedFXDifference
├─ source_item
├─ settlement
├─ carrying_amount
├─ settlement_functional_amount
├─ difference
└─ policy_trace
```

Un taux utilisé dans un historique reproductible doit être snapshoté.

# 27. ControlAccountBinding

```text
ControlAccountBinding
├─ subledger_type
├─ company_account_id
├─ partner_type?
├─ currency?
├─ effective_from
├─ effective_to?
└─ status
```

Une entité peut disposer de plusieurs comptes collectifs. La résolution dépend du contexte et échoue en cas d'ambiguïté.

# 28. SubledgerReconciliation

```text
SubledgerReconciliation
├─ id
├─ entity_id
├─ control_account_id
├─ subledger_type
├─ as_of
├─ subledger_balance
├─ general_ledger_balance
├─ difference
├─ status
├─ findings
└─ source_refs
```

Statuts :

```text
MATCHED
DIFFERENCE
INDETERMINATE
ERROR
```

Equation :

```text
Subledger Balance
=
General Ledger Control Account Balance
```

à scope identique.

# 29. Controls P1.4

Catalogue initial :

```text
SUBLEDGER_GL_RECONCILED
DUE_ITEM_TOTAL_RECONCILED
SETTLEMENT_ALLOCATION_RECONCILED
PARTNER_BALANCE_RECONCILED
MATCHED_AMOUNT_BALANCED
OPEN_ITEMS_TRACEABLE
CONTROL_ACCOUNT_CONFIGURED
UNALLOCATED_SETTLEMENTS_REVIEWED
OPENING_SUBLEDGER_RECONCILED
```

# 30. Closing integration

La clôture peut exiger :

```text
AR reconciled
AP reconciled
unallocated cash reviewed
aging reviewed
```

selon `ClosingPolicy`.

Le sous-livre fournit les faits ; `Closing` orchestre les gates.

# 31. Impairment integration

```text
ReceivablesAging
    ↓
ImpairmentAssessmentPort
    ↓
ImpairmentPolicy
```

Interdit :

```text
> 90 days overdue => 100% impairment
```

comme règle universelle.

# 32. FEC et reconstruction auxiliaire

Le FEC peut fournir :

```text
CompteNum
CompAuxNum
PieceRef
PieceDate
EcritureNum
EcritureDate
EcritureLet
DateLet
```

PyAccountingKit peut utiliser ces données pour reconstruire un historique auxiliaire lorsque cela est supporté, sans inventer les champs absents comme les échéances.

# 33. SubledgerCompleteness

```text
COMPLETE
PARTIAL
UNKNOWN
```

Modes de migration :

```text
FULL_DETAIL
OPEN_ITEMS_ONLY
BALANCE_ONLY
```

Une reconstruction partielle doit rester explicitement qualifiée comme telle.

# 34. Imported matching

`EcritureLet` / `DateLet` peuvent amorcer un `AccountingMatch` importé.

Statuts de validation :

```text
VALIDATED
INCONSISTENT
PARTIAL
UNVERIFIED
```

Le code de lettrage importé ne prouve pas à lui seul l'intégrité du rapprochement.

# 35. Operational idempotence

Clé recommandée :

```text
source_system
+
source_event_id
+
entity_id
```

complétée par un payload hash.

Même ID + même payload :

```text
idempotent
```

Même ID + payload différent :

```text
OperationalEventConflictError
```

# 36. Annulations opérationnelles

Avant posting, un document/subledger item draft peut être annulé.

Après posting :

```text
source cancellation
    ->
credit note / reversal / replacement
```

selon policy.

Interdit :

```text
delete posted accounting because source invoice was cancelled
```

# 37. ReverseSettlement

Workflow :

```text
lock settlement
lock affected due items
reverse JournalEntry
reverse allocations
recompute open amounts
mark settlement REVERSED
audit
commit
```

Objectif : éviter un état où le GL est extourné mais les open items restent soldés.

# 38. Concurrence d'allocation

Cas critique :

```text
DueItem open = 100

Worker A allocates 80
Worker B allocates 80
```

Le résultat total ne doit jamais dépasser 100.

Protection :

```text
DueItem revision / lock
Settlement revision / lock
atomic guard
deterministic lock order
```

# 39. Concurrence de lettrage

Deux processus ne peuvent pas sur-lettrer la même ligne.

Le moteur doit protéger le montant encore non lettré via revision/locking ou garde atomique.

# 40. SubledgerSnapshot

```text
SubledgerSnapshot
├─ id
├─ entity_id
├─ subledger_type
├─ as_of
├─ control_account_ids
├─ open_items
├─ balances
├─ aging
├─ source_watermark
├─ checksum
└─ generated_at
```

Un snapshot publié est immutable et peut servir à la clôture, au rapprochement et à l'analyse.

# 41. Relation avec Financial Analysis

Le sous-livre peut fournir :

```text
AR aging
AP aging
average balances
settlement timing
```

mais les indicateurs tels que :

```text
DSO
DPO
supplier concentration
customer concentration
```

appartiennent au bounded context `Financial Analysis`.

# 42. Relation avec PyPaymentKit / PSP

Frontière conceptuelle :

```text
Payment Framework
    emits
PaymentCaptured / Refund / Payout
    ↓
PyAccountingKit Payment Adapter
    ↓
Settlement / AccountingEvent
```

Le traitement du paiement lui-même ne devient pas une responsabilité de PyAccountingKit.

# 43. Exemple PSP

```text
Gross customer payment = 100
PSP fee = 3
Net bank = 97
```

Une policy peut générer :

```text
Dr Bank          97
Dr Fee Expense    3
Cr Receivable   100
```

puis affecter 100 à l'open item client.

# 44. Intégrations opérationnelles

Adapters possibles :

```text
billing
procurement
payments
banking
payroll future
loans future
```

Ils traduisent leur modèle vers :

```text
OperationalDocument
AccountingEvent
SettlementCandidate
```

et n'implémentent pas eux-mêmes le posting.

# 45. Provenance

Toute écriture issue d'une opération doit pouvoir conserver :

```text
source_system
source_document_id
source_event_id?
partner_id
subledger_item_id
policy_trace
```

Lineage cible :

```text
External Document
    ->
OperationalDocument
    ->
Receivable / Payable / Settlement
    ->
JournalEntry
    ->
JournalEntryLine
```

# 46. Reproducibility

```text
OperationalAccountingReproducibilityEnvelope
├─ runtime_version
├─ source_event_ref
├─ source_payload_checksum
├─ partner_binding_version
├─ control_account_binding_version
├─ operational_policy_version
├─ exchange_rate_snapshot?
├─ journal_entry_ref
└─ checksum
```

# 47. Audit Events

```text
BUSINESS_PARTNER_CREATED
PARTNER_ACCOUNT_BOUND
RECEIVABLE_CREATED
PAYABLE_CREATED
DUE_ITEM_CREATED
SETTLEMENT_CREATED
SETTLEMENT_ALLOCATED
SETTLEMENT_UNALLOCATED
ACCOUNTING_MATCH_CREATED
ACCOUNTING_MATCH_REVERSED
SUBLEDGER_WRITE_OFF_CREATED
SUBLEDGER_RECONCILIATION_RUN
```

# 48. Domain Events

```text
ReceivableRecognized
PayableRecognized
SettlementRecorded
SettlementAllocated
ReceivableSettled
PayableSettled
AccountingMatchCompleted
SubledgerReconciled
```

Ils restent distincts des `AuditEvent`.

# 49. Ports / Repositories

Write-side :

```text
BusinessPartnerRepository
BusinessPartnerAccountBindingRepository
ReceivableRepository
PayableRepository
SettlementRepository
AccountingMatchRepository
SubledgerSnapshotRepository
```

Query-side :

```text
ReceivableQuery
PayableQuery
OpenItemQuery
SettlementQuery
PartnerBalanceQuery
AgingQuery
SubledgerReconciliationQuery
```

Infrastructure transverse :

```text
JournalEntryRepository
CompanyAccountRepository
GeneralLedgerQuery
UnitOfWork
IdempotencyStore
AuditPort
Clock
```

# 50. Application Services

```text
CreateBusinessPartner
BindPartnerAccount
RecognizeReceivable
RecognizePayable
RecordSettlement
AllocateSettlement
UnallocateSettlement
ReverseSettlement
CreateAccountingMatch
ReverseAccountingMatch
WriteOffOpenItem
ReconcileSubledger
CreateSubledgerSnapshot
```

# 51. Transaction boundary - Receivable

```text
reserve idempotency
resolve partner / control account
create Receivable
create DueItems
create JournalEntry
validate / post
link entry
audit / outbox
commit
```

En mode synchrone P1, aucun `Receivable` ne doit être durable si l'écriture correspondante échoue.

# 52. Transaction boundary - Settlement

```text
create Settlement
resolve accounting policy
create/post JournalEntry
allocate if requested
update open-item state
audit/outbox
commit
```

# 53. Package cible

```text
src/pyaccountingkit/domain/subledgers/
├── partners/
├── receivables/
├── payables/
├── settlements/
├── matching/
├── reconciliation/
├── snapshots/
└── operational/

src/pyaccountingkit/application/subledgers/
├── recognize_receivable.py
├── recognize_payable.py
├── record_settlement.py
├── allocate_settlement.py
├── reverse_settlement.py
├── match_items.py
├── reconcile_subledger.py
└── create_snapshot.py

src/pyaccountingkit/adapters/subledgers/
├── in_memory/
├── django/
├── sqlalchemy/
└── integrations/
    ├── billing/
    ├── procurement/
    ├── payments/
    └── banking/
```

# 54. Public API cible

```python
receivable = accounting.subledgers.receivables.recognize(...)

payable = accounting.subledgers.payables.recognize(...)

settlement = accounting.subledgers.settlements.record(...)

accounting.subledgers.settlements.allocate(...)

accounting.subledgers.matching.match(...)

aging = accounting.subledgers.receivables.aging(...)

reconciliation = accounting.subledgers.reconcile(...)
```

Aucune surface publique n'expose `QuerySet`, `Session`, SQL ou transaction ORM.

# 55. Error taxonomy

```text
SubledgerError
├─ BusinessPartnerNotFoundError
├─ PartnerAccountBindingNotFoundError
├─ ControlAccountNotConfiguredError
├─ AmbiguousControlAccountError
├─ ReceivableNotFoundError
├─ PayableNotFoundError
├─ DueItemNotFoundError
├─ SettlementNotFoundError
├─ SettlementOverAllocationError
├─ DueItemOverAllocationError
├─ AllocationConcurrencyConflictError
├─ SettlementAlreadyReversedError
├─ AccountingMatchError
├─ MatchOverAllocationError
├─ MatchConcurrencyConflictError
├─ SubledgerReconciliationError
├─ SubledgerIncompleteError
├─ OperationalEventConflictError
└─ OperationalPolicyResolutionError
```

# 56. Fail-closed

Doivent échouer explicitement :

```text
missing control account
ambiguous partner/account binding
over-allocation
over-matching
duplicate event with changed payload
currency mismatch without policy
posted cancellation without correction policy
```

# 57. Tests unitaires

Minimum :

```text
partner != account
binding effective dates
due items reconcile to original amount
partial settlement
multi-allocation
unapplied amount
over-allocation rejection
full/partial matching
write-off explicit
subledger reconciliation
```

# 58. Property-based tests

Propriétés :

```text
sum(due_items) == original_amount

allocated + unallocated == settlement_amount

allocated_to_due_item <= due_item_original/open amount

full match => matched_debit == matched_credit

settlement + reversal => zero GL effect

rebuild(subledger events) == subledger projection
```

# 59. Tests de concurrence

Obligatoires sur DB transactionnelle réelle :

```text
double receivable recognition
double payable recognition
double settlement recording
over-allocation race
double match race
allocation vs settlement reversal
subledger snapshot during allocation
```

# 60. Golden scenarios

Scénarios initiaux :

```text
customer invoice with two due dates
partial customer payment
multi-invoice payment
overpayment / customer advance
supplier payment
credit note
small write-off
full matching
FEC auxiliary import
subledger vs GL reconciliation
historical open-items migration
payment-provider fee settlement
```

# 61. Golden - facture client

```text
Invoice = 1,200 EUR
Due items = 600 + 600

Expected:
Receivable = 1,200
2 DueItems
1 posted accounting entry
GL control account contribution = 1,200
```

# 62. Golden - paiement partiel

```text
Invoice open = 1,200
Payment = 500

Expected:
Settlement = 500
Allocation = 500
Receivable open = 700
GL control account reduced by 500
```

# 63. Golden - surpaiement

```text
Invoice open = 700
Payment = 1,000
Policy = CUSTOMER_ADVANCE

Expected:
700 allocated
300 advance/unapplied
no hidden write-off
```

# 64. Golden - reconciliation

```text
AR subledger = 25,000
GL control account = 25,000

=> SUBLEDGER_GL_RECONCILED = PASS
```

Mismatch :

```text
AR = 25,000
GL = 24,950
difference = 50
=> FAIL
```

# 65. ADRs

| ID | Décision |
|---|---|
| ADR-SUB-001 | Les sous-livres restent distincts du General Ledger |
| ADR-SUB-002 | `BusinessPartner` est distinct de `CompanyAccount` |
| ADR-SUB-003 | Les modes auxiliaires sont `SUBLEDGER`, `EXTENDED_ACCOUNT_CODE`, `HYBRID` |
| ADR-SUB-004 | `CompAuxNum` n'est jamais concaténé implicitement à `CompteNum` |
| ADR-SUB-005 | `OperationalDocument` et `AccountingEvent` sont distincts de `JournalEntry` |
| ADR-SUB-006 | Toute comptabilisation opérationnelle passe par le Posting Engine normal |
| ADR-SUB-007 | Les comptes collectifs sont résolus par binding/policy |
| ADR-SUB-008 | Receivables/Payables portent des `DueItem` |
| ADR-SUB-009 | Settlement et Allocation sont distincts |
| ADR-SUB-010 | Allocation n'implique pas un nouveau posting GL |
| ADR-SUB-011 | Settlement, Matching et Reconciliation sont trois concepts distincts |
| ADR-SUB-012 | Les surpaiements sont traités explicitement |
| ADR-SUB-013 | Aucune allocation ne dépasse le montant ouvert |
| ADR-SUB-014 | Les races d'allocation sont transactionnellement protégées |
| ADR-SUB-015 | Le lettrage complet et partiel sont supportés |
| ADR-SUB-016 | Un write-off est explicite et audité |
| ADR-SUB-017 | `SUBLEDGER_GL_RECONCILED` est un control |
| ADR-SUB-018 | Les codes nationaux de comptes collectifs ne sont jamais hardcodés |
| ADR-SUB-019 | L'aging ne définit aucune dépréciation universelle |
| ADR-SUB-020 | Les historiques importés conservent un niveau de complétude explicite |
| ADR-SUB-021 | Le lettrage FEC importé peut nécessiter revalidation |
| ADR-SUB-022 | Les événements opérationnels sont idempotents |
| ADR-SUB-023 | Une annulation postée produit reversal/credit note, jamais delete |
| ADR-SUB-024 | Le settlement reversal restaure aussi les allocations |
| ADR-SUB-025 | Les FX historiques utilisent des rates snapshotés |
| ADR-SUB-026 | Les résiduels ne sont jamais absorbés silencieusement |
| ADR-SUB-027 | Les adapters métier normalisent vers des primitives génériques |
| ADR-SUB-028 | PyAccountingKit n'est pas le master CRM/fournisseur |
| ADR-SUB-029 | Les PSP restent hors du core comptable |
| ADR-SUB-030 | Les snapshots de sous-livre publiés sont immuables |
| ADR-SUB-031 | DSO/DPO appartiennent à Financial Analysis |
| ADR-SUB-032 | Le futur bounded context Reconciliation généralisera ces rapprochements |

# 66. Critères d'acceptation P1.4

```text
[ ] BusinessPartner défini
[ ] Partner != CompanyAccount explicite
[ ] BusinessPartnerAccountBinding défini
[ ] SUBLEDGER / EXTENDED_ACCOUNT_CODE / HYBRID définis
[ ] AuxiliaryReference défini
[ ] CompAuxNum non concaténé automatiquement
[ ] OperationalDocument défini
[ ] AccountingEvent défini
[ ] OperationalAccountingPolicy défini
[ ] Receivable défini
[ ] Payable défini
[ ] DueItem défini
[ ] Settlement défini
[ ] SettlementAllocation défini
[ ] paiements partiels supportés
[ ] multi-invoice / multi-payment supportés
[ ] overpayment/advance policy-driven
[ ] Settlement != Allocation explicite
[ ] AccountingMatch défini
[ ] Matching != Settlement explicite
[ ] Matching != Reconciliation explicite
[ ] SubledgerBalance / PartnerBalance définis
[ ] Aging AR/AP défini
[ ] Aging != Impairment explicite
[ ] WriteOff explicite
[ ] SubledgerReconciliation défini
[ ] SUBLEDGER_GL_RECONCILED défini
[ ] ControlAccountBinding défini
[ ] historique FEC auxiliaire préparé
[ ] SubledgerCompleteness défini
[ ] idempotence opérationnelle définie
[ ] allocation concurrency définie
[ ] matching concurrency définie
[ ] settlement reversal atomique défini
[ ] SubledgerSnapshot défini
[ ] intégration Closing définie
[ ] frontière Financial Analysis définie
[ ] frontière PSP/PyPaymentKit définie
[ ] tests unit/property/integration/concurrency/golden définis
```

# 67. Ordre d'implémentation recommandé

```text
SUB-00 Primitives
SUB-01 BusinessPartner + bindings
SUB-02 Receivables
SUB-03 Payables
SUB-04 Operational Accounting
SUB-05 Settlements
SUB-06 Allocation Policies
SUB-07 Matching
SUB-08 Settlement Reversal
SUB-09 Open Items / Aging
SUB-10 Subledger Reconciliation
SUB-11 SubledgerSnapshot
SUB-12 FEC Auxiliary Integration
SUB-13 Operational Adapters
SUB-14 Golden / Concurrency Qualification
```

# 68. Démonstrateur P1.4

```text
1. Create customer BusinessPartner
2. Bind CUSTOMER_RECEIVABLE_CONTROL
3. Receive SalesInvoice event
4. Create Receivable and DueItems
5. Generate JournalEntryProposal
6. Validate / Post
7. Record partial payment
8. Allocate payment
9. Build AR aging
10. Reconcile AR subledger vs GL
11. Reverse payment
12. Verify allocation restoration
13. Create SubledgerSnapshot
14. Verify checksum / provenance
```

# 69. Matrice de concepts

| Concept | Signification |
|---|---|
| `BusinessPartner` | identité tiers |
| `CompanyAccount` | compte comptable entreprise |
| `ControlAccount` | compte GL représentant un sous-livre |
| `AuxiliaryReference` | identifiant auxiliaire |
| `Receivable/Payable` | créance/dette opérationnelle |
| `DueItem` | échéance |
| `Settlement` | règlement |
| `SettlementAllocation` | affectation d'un règlement |
| `AccountingMatch` | lettrage |
| `SubledgerReconciliation` | contrôle sous-livre vs GL |

# 70. Frontière avec le prochain document

Le prochain jalon recommandé est :

```text
16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md
```

Il devra stabiliser les façades :

```text
accounting.entries.*
accounting.ledger.*
accounting.references.*
accounting.policies.*
accounting.imports.*
accounting.statements.*
accounting.analysis.*
accounting.subledgers.*
```

sans exposer les détails ORM/UoW aux consommateurs ordinaires.

# 71. Conclusion

L'architecture cible est :

```text
BUSINESS EVENT
     ↓
OPERATIONAL ACCOUNTING
     ↓
SUBLEDGER
     ├─ RECEIVABLE / PAYABLE
     ├─ DUE ITEMS
     ├─ SETTLEMENTS
     ├─ ALLOCATIONS
     └─ MATCHING
     ↓
JOURNAL ENTRY PROPOSAL
     ↓
POSTING
     ↓
GENERAL LEDGER
     ↓
SUBLEDGER RECONCILIATION
```

Les règles finales sont :

```text
Subledger != General Ledger
Partner != Account
Operational Event != JournalEntry
Settlement != Allocation
Settlement != Matching
Matching != Reconciliation
No automatic auxiliary-code concatenation
No hidden write-off
No destructive cancellation after posting
No over-allocation
Every operational entry uses normal Posting
Every subledger balance is reconcilable with the GL
Every effect remains traceable to its operational source
```


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)
- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-04 — Subledgers & Financial Analysis (0.4.0)](../../plans/PLAN-04_SUBLEDGERS_FINANCIAL_ANALYSIS_0.4.0.md)
