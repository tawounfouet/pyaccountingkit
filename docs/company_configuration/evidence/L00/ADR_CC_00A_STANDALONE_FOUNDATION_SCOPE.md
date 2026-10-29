# ADR-CC-00A — Standalone-first Company Configuration Foundation

- **Date:** 2026-10-29
- **Decision level:** Product-owner sequencing instruction, acknowledged and applied for this implementation branch
- **Architecture / G0/G1/G2 gate status:** PENDING independent review and formal sign-off
- **Primary repository for Phase 1:** https://github.com/tawounfouet/pyaccountingkit
- **Historical repository:** https://github.com/tawounfouet/pyaccountingkit_old — **deferred integration**, not a requirement for closing the **standalone development Foundation**
- **Basis:** project owner's explicit direction to finish the recent repository's Foundation *before* any historical architecture reconciliation

## Context

The new repository's `main` was bootstrapped from `cb746be7ae95146d2bd50ce1aac049ea6da2d15e`. The L00/L01 and L02 implementation is currently a **stack of draft PRs #3–#25**, not a merged, released or independently approved Foundation. A separate mature PyAccountingKit tree exists at `pyaccountingkit_old`. That tree was audited and an experimental compatibility PR #96 was opened, but that does **not** override the project's requested implementation order.

A historical integration dependency was prematurely treated as an absolute G0 blocker. This ADR corrects **the acceptance scope**, not the historical facts.

## Decision: two distinct workstreams

**Workstream A — NOW: recent repository Foundation only.**

1. Treat `tawounfouet/pyaccountingkit` as the **authoritative implementation and CI target for the new Foundation during Phase 1**. This is a development-scope selection, **not** a declaration of public/PyPI package lineage.
2. Finish **L00/G0** (recent repo baseline, dependency/ADR inventory, bootstrap, tests, explicit known limitations), **L01/G1** (domain kernel, temporal and isolation invariants, tests and review), and **L02/G2** (ports, memory/PostgreSQL Unit of Work, audit, outbox/inbox, security and hardening candidates).
3. Select **PR #22**'s L02-07j migration lineage for consolidation; PR #21 is the divergent alternative and must not be merged alongside #22. Preserve non-overlapping ideas for independent review.
4. Consolidate **only** the selected PR chain, preserve migrations 0001–0013, remove dependency on divergent drafts, backport proven fixes such as G1's DST-fold correction onto the final full-stack head and qualify on its **exact SHA**.
5. Treat signing, SQL-role isolation, tenant security, privileged recovery and adverse-failure proofs as security-critical. A green CI is not production security approval; issues #5/#9 remain open until resolved or formally and narrowly excluded from a *development-only* scope. No declaration of a production-ready privilege control plane.
6. Review and record G0/G1/G2 as **separate decisions**, each with evidence, approved ADRs, reviewer and exact SHA. No automatic GO based on the product-owner sequencing decision alone.

**Workstream B — LATER: historical architecture reconciliation.**

- Preserve the old repository, existing API and previous release commitments.
- Defer merging, renaming, importing legacy code or publishing either tree under a contested distribution identity.
- Keep [historical PR #96](https://github.com/tawounfouet/pyaccountingkit_old/pull/96) as a **separate unmerged exploration**, with no need to advance it before the new Foundation.
- At the later integration stage, separately inventory identity formats, exception taxonomy, public manifests, UoW, period boundaries, migrations, packaging/distribution and consumers.

## Explicit acceptance boundaries

| Item | Required to close standalone development Foundation? | Required later before package interoperability / production use? |
|---|---|---|
| Exact canonical new-repo SHA / runnable CI | **Yes** | Yes |
| Typed domain API and temporal tests | **Yes** | Yes |
| Validated PostgreSQL migration chain 0001–0013, tenant isolation, UoW rollback and outbox/inbox | **Yes** | Yes |
| Least-privilege threat review + no known exploitable test/role bypass in claimed scope | **Yes** | Yes |
| Independent G0/G1/G2 **development Foundation** acceptance decisions | **Yes** | Yes |
| Port/rewrite old `pyaccountingkit_old` source | **No — deferred** | Depends on integration ADR |
| Historical package API parity or old public error codes | **No — deferred** | Yes before any unified package/consumer cutover |
| Historical release/consumer migration | **No — deferred** | Yes before cutover |
| Real external IAM, live vault, production mTLS/network and DR | **Not automatically covered by a development-only Foundation** | **Yes** before production-ready/security claims |
| Publish a stable `pyaccountingkit` release from the new repo | **No** | Requires separate packaging/release decision |

**Important:** This does not permit silently removing G2's tenant security/atomicity requirements, re-labeling negative tests as successful security qualification, or approving risky production functionality based on mocks. A missing external dependency is documented as an explicit deployment limitation.

## Consequences and next actions

1. No more historical integration work until **standalone Phase-1 Foundation** acceptance review.
2. Create an integration consolidation PR rooted in the current #25 stack, backport tested L01 corrections, then check exact-head Python/PostgreSQL workflows.
3. Record the remaining local blockers and rationalize migrations/branch ancestry; use the standalone gate checklist.
4. Obtain authorized architecture/security review decisions and controlled integration into **recent repo `main`**. Only then mark Foundation complete for its explicitly bounded development scope.
5. Keep the mature historical repo audit as a **deferred risk record**, not an impediment to today's scoped development work.

## Non-claims

No G0/G1/G2 sign-off, package/public compatibility, real external IAM, release stability or main-branch merge is claimed by this sequencing ADR.
