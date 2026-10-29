# FND-C06 — Standalone Foundation main integration dossier

**Repository:** `tawounfouet/pyaccountingkit` (recent repository only).  
**Date:** 2026-10-29.  
**Status:** **DRAFT PRE-MERGE QUALIFICATION — NO G0/G1/G2 SIGN-OFF**.  
**PR:** [#31](https://github.com/tawounfouet/pyaccountingkit/pull/31) targeting `main`, integrated candidate derived from FND-C05 #30.

## Provenance and controlled branch strategy

- New-repository `main` baseline observed: `cb746be7ae95146d2bd50ce1aac049ea6da2d15e`.
- Full-stack baseline and latest independently CI-qualified code+docs before FND-C06: [PR #30](https://github.com/tawounfouet/pyaccountingkit/pull/30), `70593b9a7ac08683f2776a18c15988d2ddbaf9a6`.
- At that baseline, GitHub `main...#30` compared **103 commits ahead / 0 behind** and 156 changed files; these are **ancestry measurements**, not code/review acceptance.
- Historical `pyaccountingkit_old` reconciliation is explicitly postponed under ADR-CC-00A, not an L00–L02 standalone development dependency.
- Selected L02-07j lineage is PR #22, not the divergent PR #21 with an incompatible `0011` migration; do not merge both branches or duplicate stacked changes.
- Previous draft PRs #3–#30 remain provenance/review references. **PR #31 is the intended single integration candidate.** Merging #31 should supersede individual stacked merges *only after independent approval*.

## Package and migration integrity

**Frozen review reference:** `70593b9a7ac08683f2776a18c15988d2ddbaf9a6`  
**Tool:** `scripts/qualify_foundation_artifacts.py`  
**CI:** `.github/workflows/foundation-integration.yml`, Python 3.11/3.12, clean Git checkout, full history, build wheel and sdist.

Must prove:
1. Exactly 14 SQL migration files named `0001` through `0014` with no missing, duplicate or extra SQL scripts.
2. Every migration's **raw bytes** are the same as `git show <frozen reference>:<migration path>`; SHA256 calculated from those bytes, not inferred from Git blob IDs.
3. The wheel and source distribution contain *exactly the same original migration bytes*, not just names.
4. Distribution metadata remains `pyaccountingkit==0.0.0` **development scaffold** (no stable release claim).
5. Wheel imports work from a fresh virtual environment **outside the source checkout**, including the installed SQL migration resources.
6. Code style and existing full Python/PostgreSQL/migration suites remain green on **the exact FND-C06 head**.

This pre-merge qualification is not permission to edit immutable migrations in a later follow-up; new schema changes must use new sequential filenames with a documented migration contract and reviewed manifest update.

## Existing tested behavior

| Scope | Current code checkpoint evidence | New candidate requirement |
|---|---|---|
| L01 / DST folded timezone intervals | PR #3 fix backported into #27 | Exact-head Python unit/property regressions |
| FND-C03 IAM SQL recovery | #28; independent SQL grant writer and one-use recovery tickets | Exact-head PostgreSQL negative security tests; external production SoD remains open |
| FND-C04 database continuity | #29; `0013→0014`, synthetic failure, isolated logical `pg_dump/pg_restore`, concurrency | Exact-head migration CI; full production PITR/DR remains open |
| FND-C05 durable Outbox/Inbox | #30; stale lease ACK and bounded retry; transactional Inbox and Hexagonal tests | Exact-head Python and PostgreSQL integration |
| FND-C06 distribution package | This PR | Immutable SQL source, wheel/sdist resource parity and clean wheel import |

## Review blockers — not waived by green CI

- **G0** — explicit ADR disposition (identity/tenant/book scope, time/versioning, package topology, deployment/trust assumptions), independent reviewer identity and written decision.
- **G1** — independent domain contract/API review, named invariants, security ownership, written decision referencing exact SHA.
- **G2** — independent SQL/tenant/privileged recovery attack review, production IAM signer and approval-writer secret isolation, role grants/rotation, consumer C10/broker trust and audited operational limitations; explicitly approved scope and decision.
- **Operational** — migration `0014` is **behaviorally breaking** for old IAM recovery workers despite preserving SQL signature; drain/controlled cutover mandatory. Live backup/roles/secrets/PITR/RPO/RTO, TLS/proxy/real IAM are not validated by CI.
- **Delivery semantics** — Outbox is at-least-once with a bounded attempt budget, Inbox exactly-once *local SQL effect* under scoped idempotency, **not globally exactly-once event transport or Ledger posting**.
- **Release** — `pyaccountingkit==0.0.0` is a scaffold; neither a stable package nor unified historical package lineage is claimed.

## Promotion protocol (proposal, not executed)

1. Verify PR #31 exact-head Python, PostgreSQL, Migration Recovery and Artifact/Package workflows **all SUCCESS** on Python 3.11/3.12.
2. Review changed files, migration checksums, divergence and branch protections; resolve security/architecture findings or narrowly document explicitly accepted nonproduction limitations.
3. Obtain independent G0/G1/G2 reviewer decisions and code review; capture approver identity, date and exact PR SHA. **Automated green checks are necessary but not sufficient.**
4. Merge **only PR #31** to recent repo `main`, not all ancestor drafts, once gates allow it. Do not rewrite public release history or touch the historical repository.
5. Re-run all CI on the resulting exact `main` SHA; verify installed distribution and migration checksums again.
6. Record the post-merge SHA, workflow run links, proof hashes, accepted risk/register, reviewer decisions and signed gate status; only then report Foundation closure for the explicitly qualified standalone development scope.

**Current disposition:** NO MERGE / REVIEW REQUIRED. This file is evidence of integration preparation, not a G0/G1/G2 decision.
