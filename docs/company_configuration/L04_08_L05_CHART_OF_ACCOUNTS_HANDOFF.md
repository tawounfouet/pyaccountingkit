# L04-08 → L05 Handoff — Chart of Accounts Domain R&D Cut

**Date:** 2026-10-30  
**Status:** `L05_BOOTSTRAP_PROPOSED_NOT_STARTED`  
**Source authority:** `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md` §2–7, §11, §21–22, with `12` Accounting Books, `14` Fiscal Calendar, `10` C10 and `18` bitemporal governance.  
**Immediate precondition:** no live G3/G4 approval exists; [security issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) is open. This cut is **pure R&D**.

## 1. Narrow next deliverable: L05-01 Chart and Account Domain Kernel

Target examples for next *design/implementation*, **not already implemented**:

```text
ChartCode / AccountCode              canonical VOs; preserve codes as strings
CompanyChartDraft                    typed identity, Company/Entity scope intent,
                                     chart code/name, effective period, revision
CompanyAccountDraft                  typed account identity, parent chart identity,
                                     account code, label, classification, posting flag,
                                     effective period
AccountHierarchyEdgeCandidate        directed child→parent relation, explicit time
pure policy: unique account code      within exact chart/version/effective overlap
pure policy: hierarchy                no cycles, no cross-chart edges
pure policy: posting candidates        parent/summary account cannot be posted
```

Do not pre-decide whether `CompanyAccount` is embedded in a giant Chart aggregate versus independently versioned small aggregates: **ADR-COA-02 OPEN**. The spec states both as candidates because whole-chart aggregate locking may be too large.

## 2. Enforced boundaries

- `CompanyChart` and `CompanyAccount` are **Company Configuration** concepts; they do **not** implement journal entries, account balances, Ledger posting or Normative Layer content.
- `AccountCode` must retain leading zeroes, textual classification and any approved jurisdiction conventions; do not parse to integer or silently coerce a PCG/IFRS/SYSCOHADA classification.
- IFRS is not a universal mandatory chart of accounts; the L05 model must support **company charts and versioned normative links** without making IFRS chart code a universal rule.
- `AccountMapping` and its 1:1, N:1, 1:N, N:M authorization and conditional priority are **separate** from account identity and must not create implicit balanced journal entries. Start with a pure mapping candidate only after approved cardinality/priority ADR and negative tests.
- Real `BookChartBinding` must be dated and refer to a **published** `CompanyChartVersion` at runtime; the L04-07 `BookDependencyRef(CHART)` is only an opaque, unverified source claim, **never proof of account eligibility**.
- L05 may implement a separate **in-memory R&D preview** without SQL migrations or company ownership assertions; a successful draft chart resolution is not `GetAccountEligibility` C10-Q05.
- L06 controls actual fiscal period status; neither a Calendar reference nor an L05 account flag authorizes posting.
- Stable merged code must not depend on unmerged stacked L04 PRs for public APIs; isolate foundational VOs and explicitly document any temporary integration stubs.

## 3. Source canonical ADRs to carry forward unchanged

| Source `13` §21 | Decision | Review owner |
|---|---|---|
| ADR-COA-01 | Chart owned by entity/book or shared + binding | Accounting / Architecture |
| ADR-COA-02 | Chart/Account aggregate granularity | DDD / Persistence |
| ADR-COA-03 | Published version strategy | Governance / Data |
| ADR-COA-04 | Single tree vs multiple reporting hierarchies | Accounting / Reporting |
| ADR-COA-05 | 1:N mappings and provider specialization | Projection / Accounting |
| ADR-COA-06 | Mapping priority/specificity | Accounting / Runtime |
| ADR-COA-07 | Optional vs mandatory normative references | Normative Layer / Legal |
| ADR-COA-08 | Total vs explicitly partial mapping coverage | Accounting / Risk |
| ADR-COA-09 | Publication and cross-domain manifests | Governance |
| ADR-COA-10 | Temporal persistence | Data / Security |

These owners are review-role proposals, not signed assignments. The decisions remain **OPEN**.

## 4. L05-01 acceptance matrix (R&D only)

| ID | Given | Then |
|---|---|---|
| L05-RND-01 | Account code with leading zeroes | Preserved exactly as a string |
| L05-RND-02 | Two account codes overlapping in same chart | Reject deterministically |
| L05-RND-03 | Account code reused in distinct chart or nonoverlapping period | Allowed if spec/ADR permits |
| L05-RND-04 | Parent-child edge creates graph cycle | Reject even for indirect cycle |
| L05-RND-05 | Cross-tenant/company/entity/chart edge | Reject |
| L05-RND-06 | Summary/nonpostable account selected as posting candidate | Reject (R&D local policy only) |
| L05-RND-07 | Wrong revision on draft edit | Optimistic conflict; no mutation |
| L05-RND-08 | Missing Normative reference | Do not invent eligibility or standard code |
| L05-RND-09 | Attempt to use draft chart in C10 or SQL issuer | No such production adapter |
| L05-RND-10 | Python 3.11/3.12, Ruff and Foundation regressions | Exact HEAD CI evidence |

## 5. Cut order

```text
L04-08 static closure / ADR register       [this PR, R&D]
                    |
                    v
L05-01 Domain VOs + draft chart/accounts   [next isolated R&D PR]
                    |
L05-02 hierarchy + bookability candidates  [R&D]
                    |
L05-03 chart/version/binding previews      [R&D]
                    |
L05-04 mappings and conflict policies      [ADR-gated R&D]
                    |
              [STOP: G3/G4/HOLD]
                    X
  No SQL writers / signed publication / live C10 / posting
```

### Completion status

- [x] Source inventory and ADR enumeration.
- [x] Cut boundaries against L04-07 R&D references and Ledger.
- [x] Negative acceptance criteria for L05-01.
- [ ] L05-01 code or tests (**not part of this L04-08 milestone**).
- [ ] Approved chart ownership, aggregation, normative applicability and production integration ADRs.
- [ ] #71 security blocker resolved with independent live evidence before any SQL authorization.

**Recommended next PR:** `L05-01 Chart of Accounts Domain Kernel (R&D)` from `main` if possible, without importing L04 drafts. Do not assume L05 has passed G5.
