# S2 — L03 Consolidation Candidate & Gate Reconciliation

**Date:** 2026-10-30  
**Scope:** PyAccountingKit / Company Configuration L03 (Organization & Legal Entity)  
**Status:** `S2_PREMERGE_HOLD` — **review-only**; not an approved merge, G3 GO, stable release or production IAM assurance.  
**Initial source head:** PR [#70](https://github.com/tawounfouet/pyaccountingkit/pull/70), `e8be4691b06b7bf105edba01d7a9ba3b63e96782`.  
**Initial main:** `acdee98ca2736d79e17174f510ac767defd90db8` (merged Foundation PR [#33](https://github.com/tawounfouet/pyaccountingkit/pull/33)).  
**Companion S1:** [draft PR #72](https://github.com/tawounfouet/pyaccountingkit/pull/72), **NOT included** in this candidate.  
**Security blocker:** [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN, `HOLD_SECURITY`.

## 1. Why this candidate exists

S0 found 49 open PRs before S1: **22 strict ancestors of `main`**, **5 divergent alternatives** (#3, #21, #26, #30, #32), and **22 commits/PRs in one linear L03 stack** (#35→#70). The phrase "22" here counts PRs, **not** 22 Git commits.

Direct GitHub compare, `main ... #70` on 2026-10-30: **247 commits ahead, 0 behind, 88 changed paths**. L03's source head already contains the selected Foundation ancestry. Therefore the desired integration topology is one review candidate from #70 into `main`, **never** a sequence of 22 historical merges.

This branch adds **only review/governance records** to L03; it does not rewrite the selected L03 implementation or its 29 SQL migrations. It is not a means of bypassing security gates.

## 2. Reconciled baseline and migrations

| Item | Verified fact | Consequence |
|---|---|---|
| Foundation | PR #27 and PR #33 merged; #33 merge commit equals current baseline `main` | Do not re-integrate Foundation |
| G0/G1/G2 | `docs/company_configuration/evidence/gates/decision_manifest.json` still reads `PENDING_REVIEW` and `HOLD` | Existing signatures/approvals may **not** be inferred from Git merge |
| Historical gate prose | G0/G1/G2 and INTEGRATION dossier reflect an earlier snapshot that says PR #33 was unmerged | Preserve as provenance; treat this document as **dated reconciliation**, never retrospectively falsify reviewer metadata |
| SQL `0001–0014` | Identical Git blobs on `main` and PR #70 per S0 | Preserve checksum/lineage |
| SQL `0015–0029` | Additive L03 migrations on PR #70; absent from main | Exact-head PG16, recovery, package checks required |
| SQL `0030` | Exists **only** on S1 HOLD branch PR #72; deliberately denies 15 L03 write surfaces | Not a functional L03 candidate and not part of this branch |
| PR #21 | Alternative SQL `0011_iam_revocation_ack.sql`, incompatible with selected `0011_signed_iam_revocation_receipts.sql` | No cherry-pick or SQL rename |
| Package | `0.0.0` placeholder; no public stable version | No publication |

An unmerged S2 candidate **does not implement S1's fail-closed SQL quarantine**: the seven SQL Organization issuer commands remain subject to issue #71. **The candidate is not authorized for merge, deployment or exposure to untrusted actors.**

## 3. Five divergent PRs — explicit triage

| PR | Detailed assessment | S2 disposition |
|---|---|---|
| [#3](https://github.com/tawounfouet/pyaccountingkit/pull/3) | Its only two changed paths, `effective_interval.py` and `test_intervals.py`, have **exactly identical Git blob SHAs** to current main; compare still reports old divergent commits due ancestry | `EXCLUDE_ALREADY_PRESENT`. No code to reapply, no automatic PR closure |
| [#21](https://github.com/tawounfouet/pyaccountingkit/pull/21) | Competing version of migration `0011`, different name and SQL lineage from selected main | `EXCLUDE_INCOMPATIBLE_MIGRATION`; do not blend chains |
| [#26](https://github.com/tawounfouet/pyaccountingkit/pull/26) | Three added L00 governance/history reports; no code. Snapshot predates Foundation merge and is not current gate approval | `REFERENCE_ONLY`. Review historical evidence later; do not import stale claims into active gate dossiers |
| [#30](https://github.com/tawounfouet/pyaccountingkit/pull/30) | Divergent FND-C05 dispatch, outbox/inbox tests and docs. `main` has a **different** `dispatch.py` implementation; notably current main returns an expired-lease DEAD count, unlike #30's older return type | `NO_CODE_CHERRY_PICK`. Mine genuinely unique regression scenarios only after comparing #31/main. Never overwrite selected dispatch |
| [#32](https://github.com/tawounfouet/pyaccountingkit/pull/32) | Parallel Foundation consolidation, redundant build workflow, alternate uppercase `GATES/` hierarchy and a separate gate verifier/tests absent from main; canonical dossiers use lowercase `gates/` and `check_foundation_gate_dossier.py` | `EXCLUDE_AS_WHOLE`; optional targeted gate-contract port after review, not competing gate truth |

No PRs are closed by this review. A future cleanup proposal may mark rejected branches `superseded` with maintainer authorization and link their retained evidence.

## 4. G0/G1/G2 factual reconciliation, NOT sign-off

- **G0 — Architecture / baseline:** `PENDING_REVIEW`; review package topology, role ownership, migration lineage, temporal semantics, formal ADR disposition, scope and historic-repo treatment.
- **G1 — Domain kernel:** `PENDING_REVIEW`; review tenant+entity identity/equality invariants, business/effective time versus knowledge-time model, Company ownership and API error contracts.
- **G2 — Persistence / IAM / operations:** `PENDING_REVIEW`; review RLS/SQL principals, issuer credentials, privileged control-plane, IAM live integration limits, transactional outbox/inbox, migration/restore, signed command binding and #71's open bypass.
- **G3 — L03 Organization:** `HOLD_SECURITY` and `NOT_APPROVED` until per-command signed authorization is enforced for the seven DDD SQL command paths or the entire branch to be merged is **technically fail-closed** with independent acceptance of the reduction of function.
- Gate review must cite **exact candidate HEAD** after all changes. No automatic GO from test successes. Independent reviewer names, decision URLs, approved exceptions and decision dates remain **UNRECORDED**.

**Important:** PR #33 is actually merged, despite dated gate dossiers saying otherwise. Treat that as an observable integration event, **not a retroactive G0/G1/G2 authorization**. Existing manifest fields must not be backfilled with invented approvals.

## 5. Consolidation acceptance protocol

1. **Freeze scope.** One S2 draft PR to `main`. No changes to SQL `0001–0029`, no PR #21 migration, no S1 `0030` graft, no new G3 micro-issues.
2. **Inspect exact diff.** Require `main...S2-head` to be linear/0-behind, with the selected L03 code and these governance-only additions. Verify no secret/credential bundles.
3. **Qualify exact-HEAD CI.** Python 3.11/3.12 + Ruff; PostgreSQL 16 full integration including tenant/issuer adversarial roles and 15 FORCE RLS tables; migration forward recovery/dump-restore; source/sdist/wheel 29 SQL SHA256 parity.
4. **Independent review.** G0 architecture, G1 domain, G2 security/ops, G3 L03 semantics all need written scope/exception decisions linked to current SHA. Review #71 signed command/decision handoff, current epoch at COMMIT, SQL issuer bypass.
5. **Reconcile failure conditions.** If #71 cannot be closed, default **HOLD_SECURITY**. S1 PR #72 is separately CI-qualified as a blocked-write mode, but is not a functioning L03 release and cannot silently be combined with this draft.
6. **Merge authorization (FUTURE only).** Maintainer must explicitly authorize **one** candidate after all blocker decisions. Run post-merge `main` exact-SHA CI, then make a new G3 decision. No publish before actual release qualification.

### Required decision states

- `S2_PREMERGE_HOLD` (current): integration prepared, unapproved security and gate boundaries.
- `S2_REVIEW_QUALIFIED` (possible): exact-head technical checks green, independent gate reviews still pending; **not merge authorization**.
- `G3_GO_RND` (future, if appropriately approved): explicitly bounded functionality and security controls; no automatic production claim.
- `HOLD_SECURITY` (current under #71): no approved path for the seven unpaired business writes.
- `GO_PRODUCTION`: separate production IAM/credential/key custody, revocation SLA, independent assessment and operational readiness; **not achieved here**.

## 6. Immediate deliverables and exit report

- [x] Compare selected L03 head to main: **247 ahead / 0 behind**, 88 paths at source SHA.
- [x] Explicitly triage #3/#21/#26/#30/#32, excluding blind cherry-picks.
- [x] Preserve independent G0/G1/G2 pending decisions and historical #33 pre-merge documents.
- [x] Identify S1 quarantine PR #72 as separate from functional L03 candidate.
- [ ] Exact S2 candidate SHA workflows on Python/PG16/recovery/wheel+sdist — record after opening the PR.
- [ ] Independent security and code review / signed gate decisions.
- [ ] Explicit authorizer decision; merge and exact-main CI — **not performed**.

**Exit status:** `S2_PREMERGE_HOLD`. This is the anti-loop outcome: integration topology is consolidated, residual risk is explicitly bounded, and L04 R&D can be separately planned. It is **not** permission to merge a bypassable L03 implementation.
