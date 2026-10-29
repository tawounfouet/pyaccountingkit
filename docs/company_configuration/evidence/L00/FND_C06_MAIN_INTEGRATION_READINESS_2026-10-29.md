# FND-C06 — Main integration readiness of standalone Company Configuration

**Date:** 2026-10-29  
**Repository:** `https://github.com/tawounfouet/pyaccountingkit` (RECENT repository only).  
**Classification:** **INTEGRATION CANDIDATE**, **NOT MERGED**, **NO G0/G1/G2 SIGN-OFF**.  
**Historical architecture reconciliation:** explicitly DEFERRED under ADR-CC-00A.

## 1. Lineage / baseline

Observation before creation of this integration branch:

| Subject | Evidence |
|---|---|
| Recent `main` | `cb746be7ae95146d2bd50ce1aac049ea6da2d15e` — README-only bootstrap |
| Selected full-stack source | [PR #31](https://github.com/tawounfouet/pyaccountingkit/pull/31) head `dc7936d330f1c3a5f3fee760ad70ff0e1e28b616` |
| Relative graph | `main...#31`: **107 ahead / 0 behind**, 158 changed files |
| Consolidated ancestry | `#27 -> #28 -> #29 -> #31 -> FND-C06` |
| Migration source | SQL `0001` to `0014`; exact order, #22 selected over incompatible #21 alternate `0011` lineage |
| Expected distribution | `pyaccountingkit==0.0.0` **placeholder only, NOT a published or stable release** |

**Do not merge previous drafts separately.** The FND-C06 branch already includes the selected ancestry, so merging #27 then #28 then #29 then #31 and then this candidate creates avoidable duplicate merge/review surface. Previous PRs remain development evidence and reference points.

## 2. Consolidation-specific changes

- No change to any SQL migration or published interface; no historical APIs imported.
- Source README describes real L00/L01/L02 candidate and explicitly excludes releases, Ledger posting, old package compatibility and production IAM.
- New `.github/workflows/foundation-integration.yml` builds wheel + sdist on Python 3.11 and 3.12, installs **the built wheel** in a clean virtual environment without bringing in unrelated optional dependencies, and checks Python imports and packaged migration resources.
- `scripts/qualify_foundation_artifacts.py` compares **all 14 numbered migration SQL files byte-for-byte** between source, sdist and wheel, validates contiguous inventory and distribution metadata. This is a package-content proof, **not** a release artifact provenance/signature/SBOM certification.

## 3. Required CI matrix for FND-C06 exact HEAD

| Workflow | Expected verification | Status |
|---|---|---|
| Python CI | Python 3.11/3.12, unit/property tests, Ruff | PENDING this integration SHA |
| PostgreSQL CI | Python 3.11/3.12, PostgreSQL 16 integration, SQL roles/permissions | PENDING this integration SHA |
| Migration Recovery CI | Python 3.11/3.12, `0013→0014`, checksum/rollback/restore | PENDING this integration SHA |
| Foundation Integration CI | Python 3.11/3.12, wheel+sdist, isolated install, exact 14 SQL byte-parity | PENDING this integration SHA |
| **Post-merge main CI** | Repeat full matrix on **actual merged main commit** | **NOT RUN — merge not authorized** |

Do not substitute ancestor PR CI for exact-head evidence. If CI fails, remediate on this branch and rerun.

## 4. Review and release stop conditions

**G0** (Architecture & ownership):
- [ ] Review and approve ADRs for IDs, scope, temporal boundaries, normative reference ownership, packaging/public API, DB topology.
- [ ] Explicit decision and reviewer identity, SHA and limitations.
- [x] Historical reconciliation is separate follow-up, not a standalone Foundation gate.

**G1** (Domain Kernel):
- [ ] Independent model review: entity identity/revision semantics, VO equality, DST-fold UTC handling, CFG invariant ownership and typed errors.
- [ ] Record exact-SHA decision.

**G2** (Technical Foundation):
- [ ] Independently review FND-C03 SQL privilege design and *actual separation* of recovery and approval-writer workloads, secrets and signed IAM verification.
- [ ] Review tenant RLS/client spoofing, role grants, session management, privileged SECURITY DEFINER and audit controls.
- [ ] Review FND-C04 recovery limitations: schema-scoped logical dump is **not** production DR, PITR, full roles/grants/vault or RPO/RTO.
- [ ] Review FND-C05 Outbox/Inbox at-least-once / idempotency / external producer identity, denial audit, schema C10 and external integration limitations.
- [ ] Sign a narrowly defined standalone **development Foundation G2** decision or NO-GO with blocking issues. **No production security certificate.**

**Integration GO requires ALL**:
- [ ] FND-C06 exact-head four-workflow CI green and inspectable.
- [ ] Explicit G0/G1/G2 written decisions by authorized reviewers; no inference from green CI.
- [ ] No accidental inclusion of #21 divergent migration, mutated prior SQL migrations, competing package publication or leaked SQL test secrets.
- [ ] Review and approve single PR from this full-stack branch to `main`.
- [ ] Only then perform controlled `main` merge, requalify actual main SHA and record final provenance.

## 5. Current decision

**NO MERGE / PENDING GATE REVIEW.** This integration candidate is deliberately a **draft PR**, not a release, gate approval or a substitute for external IAM, production restore, audit retention or historical compatibility.
