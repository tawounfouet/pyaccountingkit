# LOT-19 — Settlements, Allocations, Matching & Aging Implementation Plan

> **Projet** : PyAccountingKit  
> **Lot** : LOT-19 — Settlements, Allocations, Matching & Aging  
> **Target line** : `0.4.0a2`  
> **Baseline** : `0.4.0a1` / LOT-18 (`42b21fa2b65ce3e342850eba4e6d53bf5ca6255b`)  
> **Branche** : `feat/lot-19-settlements-matching-aging`

---

## 1. Objectif

LOT-19 transforme le socle auxiliaire de LOT-18 en un sous-livre opérationnel capable de suivre les règlements, leurs affectations, le lettrage/matching, les échéances et l'aging, puis de rapprocher le solde auxiliaire avec le compte collectif du General Ledger.

La chaîne cible reste :

```text
Receivable / Payable
        |
        v
      DueItem
        |
        +------------------+
        |                  |
        v                  v
   Settlement          Matching
        |
        v
SettlementAllocation
        |
        v
 updated Open Items
        |
        +------------------+
        |                  |
        v                  v
 AgingSnapshot    SubledgerReconciliation
                           |
                           v
                 General Ledger control account
```

Principes structurants :

```text
Settlement != Allocation
Settlement != Matching
Matching != Reconciliation
Allocation != new GL posting
Aging != impairment
```

---

## 2. Sources d'autorité

1. `docs/ROADMAP.md`, LOT-19 ;
2. `docs/specs/01_core-accounting/15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md` ;
3. ADR `ADR-SUB-009` à `ADR-SUB-026` ;
4. LOT-18 domain contracts ;
5. existing `PostingOrchestrator`, reversal and ledger query contracts ;
6. `AGENTS.md`.

The roadmap scope wins over broader historical P1.4 examples.

---

## 3. Scope LOT-19

### Included

```text
Settlement
SettlementAllocation
partial/full settlement
many-to-many allocation
matching candidates
validated matching
PaymentTerm
DueDateRule
AgingPolicy
AgingSnapshot
SubledgerReconciliation
```

LOT-19 also introduces the minimum immutable transition helpers needed to update LOT-18 due/open amounts safely.

### Explicitly out of scope

- full billing/procurement adapters ;
- payment-provider orchestration ;
- FX settlement engine ;
- generic bank reconciliation bounded context ;
- Financial Analysis / DSO / DPO (LOT-20) ;
- automatic impairment rules ;
- production SQL/Django repositories ;
- silent write-off or tolerance absorption ;
- changing the General Ledger posting source of truth.

---

## 4. Non-negotiable invariants

### 4.1 No over-allocation

For every allocation:

```text
amount > 0
amount <= settlement.open_amount
amount <= due_item.open_amount
```

After a valid allocation:

```text
new settlement.open_amount = previous - allocation
new due_item.open_amount = previous - allocation
```

Neither value may become negative.

### 4.2 Allocation does not post

A `SettlementAllocation` is operational subledger state. It must never call the posting engine by itself.

The settlement economic event may have its own posted accounting reference, but allocation of that settlement to due items does not create a second GL effect.

### 4.3 Settlement accounting effect remains explicit

A settlement is accounting-effective only with an explicit `PostedAccountingReference`.

Operational allocation status remains distinct from accounting-effect status.

### 4.4 Many-to-many is first-class

One settlement may allocate to many due items; one due item may receive allocations from many settlements.

Allocation identity is explicit and immutable.

### 4.5 Reversal restores operational state

A settlement reversal must be traceable and must restore the open amounts affected by its active allocations.

The reversal operation requires an explicit accounting reversal reference when the settlement had a posted accounting effect.

No delete-based reversal is permitted.

### 4.6 Matching is distinct

Matching/lettering operates on explicit accounting-item references and matched amounts. It does not imply economic settlement and does not silently mutate settlement allocations.

Candidates are non-executable until explicitly validated.

### 4.7 Payment terms are deterministic

A `PaymentTerm` owns one or more `DueDateRule` definitions. Allocation fractions must sum exactly to `Decimal("1")`.

Generated due-item amounts must sum exactly to the source amount; rounding residue is assigned deterministically to the final rule.

### 4.8 Aging basis is explicit

`AgingPolicy` must declare its date basis. Initial supported bases:

```text
DUE_DATE
ACCOUNTING_DATE
```

Buckets must be ordered, non-overlapping and collectively partition all eligible open items.

Aging contains no implicit impairment rule.

### 4.9 Reconciliation is scoped

A `SubledgerReconciliation` compares:

```text
subledger open balance
vs
normalized GL control-account balance
```

at the same entity, control account, currency and `as_of` scope.

The reconciliation engine receives a normalized GL balance; it must not guess debit/credit semantics from national account-code prefixes.

### 4.10 Write-off fail-closed

LOT-19 must not expose a path that silently removes residual open amount. Any write-off representation must require explicit accounting proposal/policy evidence.

---

## 5. Domain model target

### 5.1 DueItem evolution

LOT-18's `DueItem` evolves from creation-only fully-open state to immutable settlement transitions:

```text
DueItem
+ allocate(amount) -> DueItem
+ restore(amount) -> DueItem
+ status derived from open/original
```

Valid range becomes:

```text
0 <= open_amount <= original_amount
```

Construction helpers for initial due schedules still start fully open.

### 5.2 Parent aggregates

`Receivable` / `Payable` gain an immutable helper to replace exactly one due item by id while preserving entity/currency/parent/sum invariants.

The sum of `original_amount` stays constant; only `open_amount` changes.

### 5.3 Settlement

```text
Settlement
|-- settlement_id
|-- entity_id
|-- subledger_id
|-- party_id?
|-- settlement_date
|-- accounting_date
|-- amount
|-- open_amount
|-- source_reference
|-- status
|-- accounting_status
|-- accounting_reference?
|-- revision
|-- reversed_by?
```

Suggested statuses:

```text
OPEN
PARTIALLY_ALLOCATED
FULLY_ALLOCATED
REVERSED
```

### 5.4 SettlementAllocation

```text
SettlementAllocation
|-- allocation_id
|-- entity_id
|-- settlement_id
|-- due_item_id
|-- source_item_id
|-- amount
|-- allocation_date
|-- status
|-- provenance?
```

Statuses:

```text
ACTIVE
REVERSED
```

### 5.5 Allocation service

Pure domain/application service:

```text
allocate(settlement, parent, due_item_id, amount)
  -> updated settlement
  -> updated parent
  -> allocation
```

It checks expected revisions before mutating immutable copies.

### 5.6 Settlement reversal

```text
SettlementReversal
|-- reversal_id
|-- settlement_id
|-- reversed_at
|-- reversed_allocations
|-- accounting_reversal_reference?
|-- reason
```

Service restores each allocation amount to the corresponding due item and marks allocations reversed.

### 5.7 Matching

```text
MatchingCandidate
AccountingMatch
AccountingMatchItem
MatchStatus
```

A candidate never becomes active implicitly. Validation requires balanced matched debit/credit totals for a full match or explicit residual for partial matching.

### 5.8 PaymentTerm / DueDateRule

Initial deterministic model:

```text
DueDateRule
|-- rule_id
|-- days_after_document_date
|-- allocation Decimal
|-- order

PaymentTerm
|-- payment_term_id
|-- code
|-- version
|-- rules
```

No national terms are hardcoded.

### 5.9 Aging

```text
AgingDateBasis
AgingBucketDefinition
AgingPolicy
AgingBucketResult
AgingSnapshot
```

Snapshot pins:
- entity ;
- subledger ;
- as_of ;
- currency ;
- policy id/version/checksum ;
- source open-item ids ;
- bucket totals ;
- deterministic checksum.

### 5.10 Reconciliation

```text
SubledgerReconciliationStatus
SubledgerReconciliation
SubledgerReconciliationService
```

Statuses:

```text
MATCHED
DIFFERENCE
```

No tolerance is introduced silently in LOT-19.

---

## 6. Concurrency strategy

LOT-19 uses immutable revisioned objects for allocation transitions.

`Settlement` and `DueItem` expose monotonically increasing `revision` values. Allocation/reversal services accept expected revisions and reject stale writes with dedicated conflict errors.

This is the reference-domain concurrency contract. A future production persistence adapter must map it to transactional locking/optimistic concurrency.

Required tests:
- stale settlement revision rejected ;
- stale due-item revision rejected ;
- two competing allocations cannot both consume the same open amount ;
- reversal of a stale allocation state rejected.

---

## 7. Error taxonomy

Add stable codes only after implementation names are fixed:

```text
SETTLEMENT_INVALID
SETTLEMENT_NOT_ACCOUNTING_EFFECTIVE
SETTLEMENT_OVER_ALLOCATION
DUE_ITEM_OVER_ALLOCATION
ALLOCATION_CONCURRENCY_CONFLICT
SETTLEMENT_ALREADY_REVERSED
MATCHING_INVALID
MATCHING_NOT_EXECUTABLE
MATCHING_OVER_ALLOCATION
PAYMENT_TERM_INVALID
AGING_POLICY_INVALID
AGING_SOURCE_INVALID
SUBLEDGER_RECONCILIATION_FAILED
WRITE_OFF_POLICY_REQUIRED
```

---

## 8. Implementation sequence

1. evolve `DueItem` and parent replacement helpers ;
2. settlement model and accounting reference guard ;
3. allocation model/service + revision conflicts ;
4. reversal model/service ;
5. payment terms/due-date generation ;
6. matching candidate/validation model ;
7. aging policy/snapshot engine ;
8. subledger reconciliation ;
9. write-off fail-closed guard ;
10. unit/property/concurrency/golden qualification ;
11. manifests/README/CHANGELOG/version `0.4.0a2` ;
12. final CI/Security/merge.

---

## 9. Required tests

### Unit

- partial allocation ;
- full allocation ;
- multi-due allocation ;
- multiple settlements on one due item ;
- settlement and due-item over-allocation rejection ;
- currency/entity mismatch ;
- candidate matching not executable ;
- validated matching ;
- payment-term exact total after rounding ;
- aging boundaries ;
- reconciliation matched/difference ;
- settlement reversal restores open amounts.

### Property

```text
allocated + settlement.open == settlement.amount
sum(active allocations to due) + due.open == due.original
payment-term due totals == original amount
sum(aging buckets) == sum(eligible open items)
settlement + complete reversal => original open state
```

### Concurrency

Stale expected revisions fail before state transition.

### Golden

At least:

```text
invoice 1,200 EUR, due 600 + 600
settlement 500 EUR
allocation 500 EUR to first due
remaining due = 100 + 600
settlement open = 0
aging partitions 700 EUR
reconciliation against normalized GL control balance 700 EUR => MATCHED
```

and an overpayment scenario where unapplied settlement amount remains explicit.

---

## 10. Definition of Done

```text
[ ] no over-allocation
[ ] partial/full settlement represented
[ ] many-to-many allocation supported
[ ] allocation never posts GL by itself
[ ] settlement reversal traceable
[ ] reversal restores due-item open amounts
[ ] stale allocation state rejected
[ ] matching candidate != validated match
[ ] payment-term generation deterministic
[ ] aging basis explicit
[ ] aging buckets partition eligible items exactly once
[ ] aging contains no impairment rule
[ ] write-off cannot bypass accounting proposal/policy evidence
[ ] subledger/control-account reconciliation green
[ ] no account-code-prefix heuristics
[ ] entity/currency scope fail-closed
[ ] Ruff / format / mypy green
[ ] unit / property / concurrency / golden green
[ ] Python 3.11 / 3.12 / 3.13 green
[ ] package qualification green
[ ] Security green
[ ] manifests/docs/version aligned to 0.4.0a2
```

---

## 11. Merge policy

The PR remains Draft until every LOT-19 DoD item and the canonical CI/Security gates are green on the final `0.4.0a2` HEAD.

No LOT-20 Financial Analysis implementation is allowed in this branch.
