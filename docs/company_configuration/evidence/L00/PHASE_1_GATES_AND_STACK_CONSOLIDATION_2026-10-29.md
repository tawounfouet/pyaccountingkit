# PyAccountingKit / Company Configuration — Phase 1 gate readiness and stacked-PR consolidation

**Observation date:** 2026-10-29 UTC  
**Status:** OBSERVED / CANDIDATE ACTION PLAN — **NO G0, G1 OR G2 APPROVAL**  
**Source of evidence:** live GitHub repository/PR/commit-compare/Actions metadata and existing repository evidence. This document is **not** a new test run, independent security certification, acceptance decision, or assertion of a live IAM deployment.

## 1. Verified repository anchor and provenance

| Item | GitHub observation |
|---|---|
| Repository | [tawounfouet/pyaccountingkit](https://github.com/tawounfouet/pyaccountingkit), ID `1438070924` |
| Default branch | `main` |
| `main` HEAD at observation | `cb746be7ae95146d2bd50ce1aac049ea6da2d15e` |
| `main` tracked content | Only `README.md` at the default-branch root |
| Pre-bootstrap state | Existing L00 evidence records `NO_INITIAL_COMMIT`, not a passing pre-bootstrap test baseline |
| Development head | `feat/company-config-l02-signed-recovery-approval`, commit `b36bbef75c037f1e8ae9e2f4bee6ed695b6bf2f4` |
| Compare `main...development head` | **ahead by 73 commits; behind by 0; 148 changed files** at observation |
| Open review state | 21 open **draft** pull requests observed; none is a production gate |
| Last selected implementation PR | [#25 — Signed Recovery Approval](https://github.com/tawounfouet/pyaccountingkit/pull/25), unmerged, base = #24's branch |

**Historical caveat:** The initially empty canonical GitHub repository does **not** establish that prior PyAccountingKit code, published distributions, local branches or releases never existed elsewhere. Reconcile the historical framework before G0 approval. See the existing [L00 repository baseline](../L00/repository_baseline.md) and [issue #1](https://github.com/tawounfouet/pyaccountingkit/issues/1).

## 2. Exact-SHA qualification observed (not reproduced locally)

- **L01:** [PR #3](https://github.com/tawounfouet/pyaccountingkit/pull/3) head `08b3d0ff017db624dbd4cf4ad072b045d03a2b50`. Existing [Python Actions run #40838240096](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40838240096) documents **82 passing tests and Ruff on Python 3.11/3.12**. No independent G1 approval.
- **L02-07l:** [PR #24](https://github.com/tawounfouet/pyaccountingkit/pull/24) head `f608fa4e91a428649844bfc59d2ef54b3317590f`, CI-reported 257 Python and 122 PostgreSQL tests per version, without G2 approval.
- **L02-07m:** [PR #25](https://github.com/tawounfouet/pyaccountingkit/pull/25) implementation SHA `60c46d8e34e6a4ed9a7e54b831a7de502eff8b65`; documentation head `b36bbef75c037f1e8ae9e2f4bee6ed695b6bf2f4`. Its [PostgreSQL workflow #40938839643](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40938839643) and [Python workflow #40938839645](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40938839645) both report **success for 3.11 and 3.12**. PR evidence reports **125 PostgreSQL passed** and **282 Python passed / 17 SQL-only skipped** per version. This review did not rerun tests and must not be represented as independent execution.
- PR #25 has **no submitted PR reviews** at the observation point.

A GitHub Actions green result is evidence of those test jobs, **not** evidence of deployed service controls, cryptographic key custody, backup restoration or gate sign-off.

## 3. Canonical stacking map (selected delivery lineage)

```text
main: cb746be7
  #3 L00/L01
  #4 L02-01
  #6 L02-02
  #7 L02-03
  #8 L02-04
  #10 L02-05
  #11 L02-06
  #12 L02-07a
  #13 L02-07b
  #14 L02-07c
  #15 L02-07d
  #16 L02-07e
  #17 L02-07f
  #18 L02-07g
  #19 L02-07h
  #20 L02-07i
  #22 L02-07j (selected by downstream #23)
  #23 L02-07k
  #24 L02-07l
  #25 L02-07m
```

This is **20 dependent draft PRs**, not 20 independently mergeable changes. There is also a distinct **draft [PR #21](https://github.com/tawounfouet/pyaccountingkit/pull/21)** with base #20. GitHub comparison between #21 and #22's heads reports **diverged: 2 commits ahead / 3 behind** from the #21 perspective, touching migration 0011, revocation adapters, tests and workflow material. **Do not silently close #21 or merge both branches**: first examine the semantic diff, migration lineage and any non-overlapping tests/capabilities; select a single supported implementation (the current #23–#25 lineage uses #22).

## 4. Required gate decisions

| Gate | Evidence available | Blocker before sign-off | Current decision |
|---|---|---|---|
| **G0 / L00** | Initial empty-repository proof, bootstrap SHA, provisional gap matrix, present branch/CI inventory | Reconcile historical PyAccountingKit implementation/distributions; review REUSE/REFACTOR/BUILD decisions and blocking ADRs; named reviewer signs exact evidence scope | **NO_GO / PENDING** |
| **G1 / L01** | Typed IDs, immutable VOs, scope and interval model, minimal LegalEntity, positive/negative/property tests in #3 | G0 disposition, independent domain/API/ownership review, explicit approved ADRs, signed G1 decision on an exact head | **NO_GO / PENDING** |
| **G2 / L02** | Ports/UoW, PostgreSQL migrations, outbox/inbox, tenant role binding, signed IAM proofs, ACK and re-drive candidates with successful CI on branch | Independent security review; approved signed ADRs; production IAM/approval/key custody and revocation policy; SQL credential bypass; isolated workload/network; restore/DR; live provider ACK/idempotence and audit; authorized gate sign-off | **NO_GO / NOT APPROVED** |

**Significant live-security caveat:** PR #25's Ed25519 application verifier does not prevent a caller possessing the `cc_iam_recovery` SQL credential from invoking the SQL SECURITY DEFINER re-drive function with unverified actor/checker claims. Production key and approval sources in the tests are ephemeral in-memory fixtures. Neither successful signature tests nor role capability checks resolve the stolen-credential bypass. [Issue #9](https://github.com/tawounfouet/pyaccountingkit/issues/9) remains relevant.

## 5. Controlled consolidation protocol — proposed, not executed

1. **Freeze the stack:** no additional L02-07 lettered feature until the selected ancestry, blocker inventory and decision owners are recorded. Preserve existing branches and SHAs; do not force-push or rewrite evidence branches without an explicit controlled plan.
2. **Disambiguate #21 versus #22:** compare complete patches, migration 0011 compatibility and negative tests; document a single choice. Do not merge mutually divergent alternatives by accident.
3. **Close provenance risk before G0:** identify any earlier PyAccountingKit repositories/packages/tags/local code and decide `REUSE / REFACTOR / BUILD / DEFER` with evidence. Existing zero-commit baseline covers only this repository.
4. **Review #3 for G0/G1:** independent reviewer validates typed domain kernel, invariant boundary and candidate ADR register, then records explicit gate decisions on exact commits. A draft status should not be changed automatically.
5. **Plan one integration route:** after written approvals, integrate the selected chain **in ancestry order** and retarget/rebase subsequent PRs onto the new target base as needed; avoid duplicate stacked commits, unreviewed migrations and blanket bulk merges. Do not treat PR numbers as standalone branches.
6. **At each integration checkpoint:** record pre/post merge SHA, review decision, final diff against target, migration checksums, test results, PostgreSQL 3.11/3.12 matrix, Ruff and rollback behavior. Rerun CI on the **resulting exact `main` SHA**, not only PR heads. Halt on regression, drift, unexpected migrations or invalid dependency.
7. **G2 remains separate:** real credential containment, external IAM and independently approved recovery workflow, production-grade audit/telemetry/restore, and adversarial penetration review require their own evidence and authorized sign-off. A merged branch is not automatically accepted for production.
8. **Only then evaluate L03:** explicit `GO / CONDITIONAL_GO / NO_GO` with owner, risk register and decisions. No v1.0/stable/release or Ledger posting claim from the present work.

## 6. Evidence checklist before a gate or merge

- [ ] GitHub current SHA and ancestry verified; no unexpected changed files.
- [ ] Historical code/provenance reconciliation documented or formally risk-accepted.
- [ ] ADR ownership and decision recorded (candidate != approved).
- [ ] Correct #21/#22 implementation selected with diff evidence.
- [ ] Independent PR reviews and unresolved review threads resolved.
- [ ] Python 3.11 + 3.12, lint, PostgreSQL integration and security-negative tests on the exact target SHA.
- [ ] Migration 0001–0013 checksum/upgrade review; recovery/restore rehearsal as applicable.
- [ ] Least-privilege roles, secret custody, IAM approval revocation, DLQ and ACK operational runbooks tested against live-approved counterparts.
- [ ] Clear G0/G1/G2 decision, signatory and residual risks attached to GitHub issues #1, #2, #5 and #9.

## 7. Explicit non-claims

This is a **read-only GitHub readiness inventory plus a proposed protocol**, not source-code implementation, a reproduced local test run, a completed stack merge, a production IAM integration, an approved ADR, a security sign-off, or the passage of G0/G1/G2. The present report PR must remain **draft** until reviewed.

*References: [G0 issue #1](https://github.com/tawounfouet/pyaccountingkit/issues/1), [G1 issue #2](https://github.com/tawounfouet/pyaccountingkit/issues/2), [G2 issue #5](https://github.com/tawounfouet/pyaccountingkit/issues/5), [Security issue #9](https://github.com/tawounfouet/pyaccountingkit/issues/9), [Phase 1 plan](https://github.com/tawounfouet/pyaccountingkit/tree/feat/company-config-phase1-foundations/docs/company_configuration).*
