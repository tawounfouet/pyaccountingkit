# Phase 1 — Standalone Foundation closure plan (recent PyAccountingKit repository)

**Date:** 2026-10-29. **Status:** ACTIVE IMPLEMENTATION PLAN, NOT CLOSED.  
**Scope:** only `https://github.com/tawounfouet/pyaccountingkit`.  
**Sequencing:** [ADR-CC-00A](L00/ADR_CC_00A_STANDALONE_FOUNDATION_SCOPE.md) — historical `pyaccountingkit_old` reconciliation deferred; not a development-gate blocker.  
**Reference:** `COMPANY_CONFIGURATION_IMPLEMENTATION_BOOTSTRAP_PLAN.md`, sections 4, 5, 7, 8, 10, 12.

## 1. G0 — Repository baseline and architectural scope

- [x] Identify the recent repo, bootstrap initial `main` SHA `cb746be7ae95146d2bd50ce1aac049ea6da2d15e` and baseline.
- [x] Record known historical repo separately as a **deferred** integration/release risk, not a standalone G0 dependency.
- [x] Record owner sequencing decision and explicit L00–L02 development limits in ADR-CC-00A.
- [x] Map selected PR chain #3,#4,#6,#7,#8,#10,#11,#12,#13,#14,#15,#16,#17,#18,#19,#20,#22,#23,#24,#25.
- [x] Select #22's tombstone-compatible L02-07j lineage provisionally, avoiding incompatible #21 migration 0011; preserve #21's unique semantics for review.
- [ ] Approve package topology, identity, tenant and book scope, temporal bounds, normative references, security and publication ADRs *for this repo*.
- [ ] Record an exact-SHA clean-checkout test reproducibility baseline **after consolidated code is on main**, distinct from per-PR green CI.
- [ ] Independent G0 architecture reviewer signs `GO` or `NO_GO` with scoped exceptions and exact SHA.

**G0 verdict:** PENDING REVIEW (not blocked by historical reconciliation anymore).

## 2. G1 — Domain Kernel

- [x] Runtime-distinct typed UUID identifiers and strict scope boundaries in L01.
- [x] Local Value Objects for half-open effective/knowledge intervals, currency, normative reference and content digest.
- [x] Minimal immutable `LegalEntity` candidate with revision and guarded name mutation, *not* full L03 organization.
- [x] Negative and property-based tests; GitHub Actions Python 3.11/3.12 success on PR #3.
- [x] Fix DST-fold UTC ordering on PR #3 at `885410195ac2e08bfd9f2854114c146af07ca614`; backport same source/test content onto latest stacked Foundation candidate.
- [ ] Verify exact-head unit and property suites against the **consolidated** stack, not just PR #3.
- [ ] Review entity identity/equality, typed errors, digest canonicalization, temporal ownership, and CFG-01..CFG-10 responsibility traceability.
- [ ] Approved G1 ADRs and independent G1 gate decision with reviewer / SHA.

**G1 verdict:** CODE CANDIDATE, PENDING REVIEW.

## 3. G2 — Technical Foundations

- [x] Ports, memory UoW/repositories, scoped commands and idempotency candidate (#4).
- [x] PostgreSQL migrations, UoW, rollback, tenant role policies, audit, Outbox and Inbox candidates (#6–#10).
- [x] Credential/pool boundaries and scoped privileged audit, policy and control-plane candidates (#11–#20).
- [x] Signed revocation receipt with pre-issuance tombstone (#22), durable ACK / DLQ / manual re-drive (#23–#24) and independent signed approval candidate (#25).
- [x] Historic per-increment CI for PR #25, PostgreSQL and Python on Python 3.11/3.12 successful; **not** an approved security or G2 gate.
- [x] **Current full-stack candidate CI proof:** PR #31 implementation `703331ae70352ea0577af749fb0cc0f09964a32b` passed Python 3.11/3.12 (**289 passed / 19 skipped per version**), PostgreSQL 16 (**133 passed per version**), migration/recovery (**6 passed per version**) and Ruff. A subsequent documentation commit needs independent exact-head CI.
- [ ] Re-run **full** Python+PostgreSQL+Ruff against the **merged `main` SHA** after review/controlled integration; branch-only green is insufficient.
- [x] **FND-C04 development qualification:** exact-head CI proves fresh install, `0013→0014` upgrade, immutable source checksums, unknown/gapped applied history denial, injected transaction rollback, concurrent migration serialization and isolated `pg_dump/pg_restore` of selected domain evidence. See [FND-C04 evidence](L02_08_FND_C04_MIGRATION_RECOVERY_QUALIFICATION.md); no existing migration file was edited.
- [ ] **Production restore and rollout gate still open:** actual backup/PITR/roles/grants/vault restoration, N/N-1 rollout contract and graceful drain of old recovery workers, RPO/RTO evidence and independent operator approval. `0014` intentionally changes recovery authorization semantics.
- [ ] Security review with direct SQL abuse paths (especially recovery `cc_iam_recovery` credential calling SECURITY DEFINER re-drive), role separation, stolen-credential scenario, signature source authenticity and revocation races. Review [#9](https://github.com/tawounfouet/pyaccountingkit/issues/9).
- [x] **FND-C05 automated local contract proof:** leased dispatcher refuses expired acknowledgements, expired final claims dead-letter, handlers cannot commit independently, exceptions atomically roll back Inbox receipt + projection, and Domain/Application import boundaries are tested. See [FND-C05 evidence](L02_09_FND_C05_RELIABILITY_AND_CONTRACTS.md) and PR #31.
- [ ] **Independent G2 contract audit still open:** tenant and actor trust; external broker/producer authenticity; review of denial audit and C10 schema by a reviewer; load/fault testing and SLO policy.
- [ ] Review architecture boundaries (Domain → no ORM/IAM imports, Application ports, Infrastructure adapters), package/API/error contracts and no demo-only functionality misrepresented.
- [ ] Approve/reject outstanding L02 ADRs, explicit production-only limitations, audit data protection and disaster-recovery caveats.
- [ ] Independent G2 gate decision with exact SHA and allowed use scope.

**G2 verdict:** MULTIPLE CI-QUALIFIED IMPLEMENTATION CANDIDATES, NOT APPROVED.

## 4. Selected branch chain and consolidation protocol

```text
main (README bootstrap)
  #3 L00/L01  ← contains G1 DST bug fix on its current HEAD
   #4 L02-01 → #6 L02-02 → #7 L02-03 → #8 L02-04
    → #10 L02-05 → #11 L02-06 → #12 L02-07a → #13 L02-07b
    → #14 L02-07c → #15 L02-07d → #16 L02-07e
    → #17 L02-07f → #18 L02-07g → #19 L02-07h
    → #20 L02-07i → #22 L02-07j → #23 L02-07k
    → #24 L02-07l → #25 L02-07m
      → standalone Foundation consolidation PR (backports G1 fix + gate scope)
      → #27 standalone main-integration candidate
         → #28 FND-C03 SQL recovery grant hardening
            → #29 FND-C04 migration / logical restoration
               → #31 FND-C05 Outbox/Inbox reliability
```

**IMPORTANT:** Branch ancestry was created before PR #3's later DST fix. Do not assume the fix is in the original #4–#25 branches. The consolidation child branch explicitly backports the same source and tests for CI. Before any merge to main, use a consistent integration strategy that prevents duplicated changes and preserves the applied migration order; verify with `git merge-base`, `git diff`, `git log` and GitHub compare results. Do not merge the incompatible #21 alternative.

## 5. Minimum exact-SHA evidence dossier

| Evidence | Needed | Acceptance |
|---|---|---|
| `G0_DECISION.md` | Explicit standalone scope, architecture signoff, repo SHA and exception list | Written reviewer GO |
| `G1_DECISION.md` | Pure domain tests, Python 3.11/3.12 property+negative, DST-fold regression, invariant ownership | Written reviewer GO |
| `G2_DECISION.md` | All SQL migrations, role/tenant attack tests, isolation, UoW/outbox/inbox, audit, security review | Written reviewer GO for defined development/production scope |
| Controlled integration evidence | `main` SHA + manifest/diff + CI workflows, package integrity | No unreviewed or divergent commits |
| Deferred historical reconciliation dossier | Old repo status and future cutover requirements | **Not prerequisite for standalone Foundation; remains prerequisite before unified package publication** |

## 6. Stop/Go decision

The Foundation can be called **DONE for the recent repository's explicitly scoped development use** only when the selected stack is integrated into its `main`, G0/G1/G2 are independently reviewed and signed, and CI/SQL proofs pass on the integrated SHA.

**This document does not declare the Foundation finished.** No production IAM, stable version or external compatibility is claimed.
