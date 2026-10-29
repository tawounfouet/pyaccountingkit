# FND-C07 — Final Foundation Gate Readiness / Decision Dossier

**Date:** 2026-10-29  
**Scope:** standalone development Foundation in recent [tawounfouet/pyaccountingkit](https://github.com/tawounfouet/pyaccountingkit) only.  
**Single integration candidate:** [PR #32](https://github.com/tawounfouet/pyaccountingkit/pull/32) → `main`, still **draft/unmerged**.  
**Formal verdict:** **NO_GO for merge / G0 PENDING / G1 PENDING / G2 PENDING**.  
**This is a readiness dossier, not a certification, pen test, production release or authorized reviewer approval.**

## 1. Independently verifiable previous CI baseline

The *previous* exact-head full-stack checkpoint `098f6de80b916d0545b65c2dfec9357f854cddcd` passed on both Python 3.11 and 3.12:

| Source | Result per version |
|---|---|
| [Python #40954760622](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760622) | **289 passed / 18 skipped**, Ruff green |
| [PostgreSQL #40954760659](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760659) | **136 passed**, Ruff green |
| [Migration/Recovery #40954760543](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760543) | **6 passed**, Ruff green |
| [Wheel/Sdist provenance #40954760631](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760631) | 14 SQL migration raw bytes preserved vs frozen reference, clean installed wheel imports and SQL resources, Ruff green |

FND-C07 introduces a gate checker and tests **after** this checkpoint; the final PR SHA must run all workflows again and cannot inherit the earlier evidence without a new run. Post-merge `main` checks have **not** run.

## 2. Gate decision dossiers

- [G0 decision](GATES/G0_DECISION.md): proposed architecture decisions, identity/scope, package placement, ADR disposition, topology and independent architecture review.
- [G1 decision](GATES/G1_DECISION.md): explicit domain invariants, UTC/DST regressions, equality/key semantics (tenant+entity identity versus company scope), digest and error-publication contracts, independent domain reviewer.
- [G2 decision](GATES/G2_DECISION.md): SQL role security, independent IAM recovery approval-writer, RLS and cross-tenant attack paths, transactional Outbox/Inbox, migration restore and runtime limitations, independent security reviewer.

Source-of-truth readiness state: [`FND_C07_GATE_REGISTER.json`](FND_C07_GATE_REGISTER.json). Every gate is **`PENDING_REVIEW`**, reviewer/approved SHA **null**, and promotion flags `false`.

## 3. Deterministic preflight, with truthful semantics

`scripts/qualify_foundation_gates.py`:

- `--mode report` verifies the machine-readable schema, four unique successful workflows bound to their **recorded checkpoint SHA**, existence and path safety of G0/G1/G2 decision files, status/reviewer/SHA/known blocker consistency, and no fabricated pre-merge outcome. **Returns zero when structure is consistent, while explicitly printing `NO_GO`** if gates remain unsigned. A green report CI is NOT permission to merge.
- `--mode enforce --head-sha <PR HEAD>` must refuse missing/old approval SHAs, any unresolved gate, absent GitHub-token live evidence, draft/wrong PR, no independent **current-head** GitHub code reviews, missing exact-head live CI or unreadable branch protection. This command does **not** perform any GitHub write or merge.
- Negative tests actively inject fake reviewer/SHA, wrong workflow SHA, missing workflow/decision file, stale gate approvals and premature main/closure success. They must remain green even as `enforce` returns `NO_GO` for this candidate.
- `.github/workflows/foundation-gate-readiness.yml` runs the structural assessment and contract tests separately on Python 3.11 and 3.12. Its job name says **NOT gate approval**; do not confuse it with a protective branch rule or a formal independent signature.

## 4. Blocking review and operational evidence, by priority

| Scope | Severity for requested gate | Gap | Required human/operational next action |
|---|---|---|---|
| G0 | Required | `ADR-CC-FOUNDATIONS-PROVISIONAL` remains **PROPOSED**; package/identity/temporal/security ADR set not approved | Independent architect records decisions and exact PR SHA |
| G1 | Required | Domain identity/equality, digest and temporal ownership API have no independent contract approval | Review tenant-global entity-key vs company scope and sign explicit G1 decision |
| G2 / Security P0 | Required | Tenant SQL roles and signed recovery one-use ticket are CI candidates, not audited production authority. `cc_iam_approval_writer` credential compromise, live SoD/IdP and owner bypass remain outside proven threat boundary | Independent attacker-minded SQL/IAM review; confirm nonproduction-only envelope until real issuer, vault and topology are in place |
| G2 / Consumer | Required for external consumer claim | No trusted external broker or versioned C10 E2E beyond sample SQL projection | Either independent producer/consumer E2E qualification or explicit bounded development-only exclusion |
| G2 / Operations | Required for production claim | No full PITR/roles/secrets/cluster/DR verification, RPO/RTO, operational key rotation or live network/TLS isolation | Independent DR/deployment rehearsal before any production use |
| G2 / Migration | Required for rollout | Migration 0014 SQL signature remains, but old recovery workers lack ticket and fail closed | Approve stop/drain, protected issuer provision, cutover and rollback traffic plan |
| Integration | Required | No recorded human PR approval. GitHub `main` branch protection read returned HTTP **403**, so configuration is **unknown** | Verify actual branch rules/review approvals and current exact-head CI before deciding to merge |
| Release | Explicit exclusion | `pyaccountingkit==0.0.0` and historical distribution collision | Do not claim stable release or unified package/API compatibility |

Historical `pyaccountingkit_old` reconciliation is **deferred by product-owner instruction**, not a standalone L00–L02 requirement. This does NOT waive the recent repo's own identity, security, durability or review risks.

## 5. Controlled promotion protocol

1. Obtain independent G0, G1, G2 reviewer dispositions against current exact SHA; permit a narrowly scoped **development-only GO** only if the reviewer *explicitly* accepts specific exclusions without interpreting mocked IAM as production.
2. Confirm all CI checks, migration hashes and package imports on current PR head. Verify actual branch protection and independent PR approval; use strict gate preflight with live GitHub reads. Do not edit historical migrations to fix unknown bugs.
3. Only with authorized sign-offs and branch rules satisfied: merge **PR #32 once**, not its earlier stacked draft ancestors. If any gate is NO_GO, keep draft/no merge.
4. Run four qualification workflows plus gate report on the resulting exact `main` SHA, then record the main commit, reviewer decision refs, proof links, signed scope and residual risk register.
5. State Foundation done **only for the independently accepted scope**. No stable release, historical migration, external IAM or production readiness is inferred.

**Status at creation: BLOCKED / NO_GO. No PR merged, no gate signed, no production security claims.**
