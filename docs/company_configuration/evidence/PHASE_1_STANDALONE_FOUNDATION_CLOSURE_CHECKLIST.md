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
- [x] Unit and property suite qualified at consolidated PR #32 code+docs checkpoint `098f6de80b916d0545b65c2dfec9357f854cddcd` (289 passed, 18 skipped per Python 3.11/3.12, Ruff green); FND-C07 changes will require **new exact-head CI**. Independent G1 review still pending.
- [ ] Review entity identity/equality, typed errors, digest canonicalization, temporal ownership, and CFG-01..CFG-10 responsibility traceability.
- [ ] Approved G1 ADRs and independent G1 gate decision with reviewer / SHA.

**G1 verdict:** CODE CANDIDATE, PENDING REVIEW.

## 3. G2 — Technical Foundations

- [x] Ports, memory UoW/repositories, scoped commands and idempotency candidate (#4).
- [x] PostgreSQL migrations, UoW, rollback, tenant role policies, audit, Outbox and Inbox candidates (#6–#10).
- [x] Credential/pool boundaries and scoped privileged audit, policy and control-plane candidates (#11–#20).
- [x] Signed revocation receipt with pre-issuance tombstone (#22), durable ACK / DLQ / manual re-drive (#23–#24) and independent signed approval candidate (#25).
- [x] Historic per-increment CI for PR #25, PostgreSQL and Python on Python 3.11/3.12 successful; **not** an approved security or G2 gate.
- [x] **FND-C06 pre-merge technical CI** on implementation checkpoint `662679ad014436300e40b86a3ec4ef0e2d42b7ce`: Python 289 passed/18 skipped, PostgreSQL 136 passed, FND-C04 migration 6 passed per Python 3.11/3.12; all Ruff green. New wheel/sdist qualification proves 14 pinned, byte-identical SQL migrations and clean wheel imports. See [FND-C06 evidence](L02_10_FND_C06_MAIN_INTEGRATION_QUALIFICATION.md). **This is not post-merge CI or G2 approval.**
- [x] **FND-C04 development qualification:** exact-head CI proves fresh install, `0013→0014` upgrade, immutable source checksums, unknown/gapped applied history denial, injected transaction rollback, concurrent migration serialization and isolated `pg_dump/pg_restore` of selected domain evidence. See [FND-C04 evidence](L02_08_FND_C04_MIGRATION_RECOVERY_QUALIFICATION.md); no existing migration file was edited.
- [ ] **Production restore and rollout gate still open:** actual backup/PITR/roles/grants/vault restoration, N/N-1 rollout contract and graceful drain of old recovery workers, RPO/RTO evidence and independent operator approval. `0014` intentionally changes recovery authorization semantics.
- [ ] Security review with direct SQL abuse paths (especially recovery `cc_iam_recovery` credential calling SECURITY DEFINER re-drive), role separation, stolen-credential scenario, signature source authenticity and revocation races. Review [#9](https://github.com/tawounfouet/pyaccountingkit/issues/9).
- [x] **FND-C05 CI proof:** closed expired Outbox lease ACK and exhausted-crash republish defects, added negative/fault-injection PostgreSQL tests and durable Inbox replay + Domain/Application dependency contracts. Verified Python/PostgreSQL/Migration CI on implementation SHA `eb9c9f9f62bef37418c42308058ea386e57804a1`. See [FND-C05 contract evidence](L02_09_FND_C05_RELIABILITY_CONTRACT_QUALIFICATION.md). Existing denial-audit fail-closed and concurrent Inbox tests also pass in the full suite.
- [ ] **G2 operational/independent acceptance still open:** real broker + C10 consumer contract E2E, production clock/lease and DLQ governance, authenticated source/handler trust, adversarial security reviewer, signed exact-SHA evidence.
- [ ] Review architecture boundaries (Domain → no ORM/IAM imports, Application ports, Infrastructure adapters), package/API/error contracts and no demo-only functionality misrepresented.
- [ ] Approve/reject outstanding L02 ADRs, explicit production-only limitations, audit data protection and disaster-recovery caveats.
- [ ] Independent G2 gate decision with exact SHA and allowed use scope.

**G2 verdict:** FULL-STACK CI-QUALIFIED DEVELOPMENT CANDIDATE, NOT APPROVED. See machine-readable [FND-C07 register](FND_C07_GATE_REGISTER.json) and separate [G0](GATES/G0_DECISION.md), [G1](GATES/G1_DECISION.md), [G2](GATES/G2_DECISION.md) decision dossiers. A passing register validation prints **NO_GO** by design, and is **not** a signature.

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
      → #27 standalone Foundation → #28 FND-C03 security
      → #29 FND-C04 recovery → #30 FND-C05 reliability
      → #32 FND-C06 unified main-integration draft (this lineage; no merges yet)
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

## 6. FND-C07 readiness controls

- [x] Document separate G0/G1/G2 reviewer decision dossiers and explicit unsigned, exact-SHA machine-readable status; do not treat green CI as approval.
- [x] Add a fail-closed CLI and negative contract tests for fake approvals, stale SHA, missing workflows and incomplete evidence.
- [ ] Obtain signed independent reviewer decisions naming the current candidate SHA, ADR dispositions and explicitly accepted development-only scope.
- [ ] Verify branch protection and valid independent GitHub PR approval; GitHub API previously returned HTTP 403 when reading main protection, so it is **UNKNOWN**.
- [ ] Confirm four full-stack jobs **on the final PR SHA**, controlled merge, then four jobs again on the post-merge main SHA.

## 7. Stop/Go decision

The Foundation can be called **DONE for the recent repository's explicitly scoped development use** only when the selected stack is integrated into its `main`, G0/G1/G2 are independently reviewed and signed, and CI/SQL proofs pass on the integrated SHA.

**This document does not declare the Foundation finished.** No production IAM, stable version or external compatibility is claimed.
