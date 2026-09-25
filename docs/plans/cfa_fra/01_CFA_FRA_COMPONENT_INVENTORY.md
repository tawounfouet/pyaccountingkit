# 01 — CFA FRA Component Inventory

## Frozen oracle

LOT-25 uses the bundled CFA FRA Django MVP Sprint 7 snapshot as a **behavioral oracle**, never
as a runtime dependency.

```text
resources/cfa_fra_django_mvp_sprint_7/
tree SHA: 07d4880534d2e2239e19fd4ef4139de70b56773a
manifest version: 0.8.0
implemented sprints: 0,1,2,3,4,5,6,7
```

## Taxonomy

| Classification | Meaning |
|---|---|
| EXTRACT | Keep behavior/invariant in framework-neutral PyAccountingKit form |
| REWRITE | Reimplement behavior without copying Django implementation |
| ADAPTER | Keep framework/database concern behind a port or optional adapter |
| GOLDEN | Preserve as executable evidence for parity |
| CONSUMER | Remains CFA FRA application responsibility |

## Inventory

| CFA FRA area | Main evidence | Classification | PyAccountingKit owner |
|---|---|---|---|
| Organizations / fiscal years / periods | `apps/organizations` | EXTRACT + GOLDEN | domain entity / periods |
| Chart / Account / Journal | `apps/accounting/models.py` | EXTRACT + GOLDEN | charts / ledger |
| Entry validation | `apps/accounting/services.py::validate_entry` | EXTRACT + GOLDEN | domain/application |
| Draft creation/edit | `create_draft_entry`, `update_draft_entry` | REWRITE + GOLDEN | public entries facade |
| Validation workflow | `validate_journal_entry` | EXTRACT + GOLDEN | ledger application |
| Posting | `post_journal_entry` | EXTRACT + GOLDEN | PostingOrchestrator |
| Reversal | `reverse_journal_entry` | EXTRACT + GOLDEN | ReversalOrchestrator |
| Django atomicity | `transaction.atomic` | ADAPTER | Django/SQLAlchemy UoW |
| Row locking | `select_for_update` | ADAPTER | production persistence adapters |
| AuditEvent | `apps/audit` | EXTRACT semantics / ADAPTER storage | audit/outbox |
| FEC upload/idempotence | Sprint 4 + `apps/imports` | REWRITE + GOLDEN | imports/FEC |
| FEC parser 18 columns | Sprint 4 | ADAPTER + GOLDEN | FEC adapter |
| FECRawLine provenance | `apps/imports/models.py` | EXTRACT + GOLDEN | raw import records |
| FEC mapping | `apps/imports/services.py` | REWRITE + GOLDEN | import mappings |
| Journal report | Sprint 5 / `apps/reporting` | REWRITE + GOLDEN | ledger queries |
| General ledger | Sprint 5 | REWRITE + GOLDEN | ledger queries |
| Trial balance variants | `TrialBalanceVariant` | EXTRACT + GOLDEN | TrialBalanceSnapshot |
| SQL Window running balance | reporting selectors | ADAPTER implementation | DB query adapter |
| Statement configuration | Sprint 6 | REWRITE + GOLDEN | statements |
| Account→statement mapping | Sprint 6 | EXTRACT semantics + GOLDEN | statement mappings |
| Income statement | Sprint 6 | REWRITE + GOLDEN | statements |
| Balance sheet | Sprint 6 | REWRITE + GOLDEN | statements |
| Cash flow | Sprint 6 | REWRITE + GOLDEN | statements |
| Ratios | Sprint 6 | GOLDEN where semantically equivalent | financial analysis |
| Regulatory profile/mapping | Sprint 7 | REWRITE; certification deferred | regulatory reporting / LOT-27 |
| Regulatory snapshots/exports | Sprint 7 | GOLDEN for traceability only | reporting; LOT-27 certification |
| Controls | `apps/controls` + Sprint 7 | REWRITE + GOLDEN where executable | controls |
| Closing models | `apps/closing/models.py` | EXTRACT model intent | closing |
| Closing package/service | planned Sprint 8 | NOT EXECUTABLE ORACLE | LOT-25 gap / later migration |
| HTMX/views/forms | Django UI | CONSUMER | CFA FRA |
| RBAC | memberships/permissions | CONSUMER | CFA FRA |
| Local regulatory authority | referentials | RETIRE/REPLACE | reference provider / LOT-27 |

## Critical implementation facts captured from the oracle

### Posting

The oracle requires:

```text
DRAFT -> VALIDATED -> POSTED
```

A DRAFT cannot be posted directly. Validation checks at least two lines, exact debit/credit
equality, non-zero totals and an open period.

### Reversal

Only POSTED entries are reversible. The oracle creates a new reversal entry, swaps debit and
credit line by line, posts the reversal, then marks the original REVERSED. The `REV-`
numbering convention is oracle-specific and is not promoted to a universal PyAccountingKit rule.

### FEC

The Sprint 4 oracle preserves:

- original file identity and SHA-256;
- all 18 source columns;
- raw line JSON;
- source line number;
- row hash;
- normalized entry key;
- blocking validation vs warnings;
- full rollback on import failure;
- source-to-ledger lineage.

Direct creation of POSTED FEC history is treated in PyAccountingKit as a specialized trusted
history import semantics, not a general posting bypass.

### Ledger

The oracle defines:

```text
signed_balance = debit - credit
```

and three balance variants:

- BEFORE_ADJUSTMENTS: OPENING + NORMAL + REVERSAL;
- ADJUSTED: OPENING + NORMAL + ADJUSTING + REVERSAL;
- POST_CLOSING: adds CLOSING.

The Sprint 4 convention `JOD -> ADJUSTING` is explicitly non-universal.

### Statements

Sprint 6 provides executable behavior for income statement, balance sheet, cash flow, mapping
coverage, ratios and drill-down. `CFA_FRA_MVP` is an internal presentation framework and is
not an official regulatory standard.

## Gaps intentionally recorded

1. Sprint 7 announces Sprint 8 for regulatory controls & closing package. Closing parity is
   therefore not yet backed by a complete executable legacy service in this snapshot.
2. Regulatory SYSCOHADA/IFRS nomenclature is not hard-coded in the oracle; official regulatory
   qualification belongs to LOT-27.
3. UI, RBAC and HTMX behavior are consumer responsibilities and are not copied into the kit.
