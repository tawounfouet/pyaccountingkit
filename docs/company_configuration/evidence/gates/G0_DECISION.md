# FND-C07 — G0 Architecture / baseline decision dossier

**Status: PENDING_REVIEW — NO G0 APPROVAL.**  
**Review reference:** recent `tawounfouet/pyaccountingkit`, standalone Company Configuration Foundation (L00–L02).  
**Observed integration candidate:** [draft PR #33](https://github.com/tawounfouet/pyaccountingkit/pull/33), SHA `272d85f319219597abec845929038573b4712203` (2026-10-29, prior to this dossier).  
**Authority:** decision must be entered by an **independent authorized architecture reviewer**; authoring this document is not approval.

## Verified observations

- Recent `main` SHA at review preparation: `cb746be7ae95146d2bd50ce1aac049ea6da2d15e`, initial README bootstrap; no merged Foundation.
- [PR #33](https://github.com/tawounfouet/pyaccountingkit/pull/33) was **113 commits ahead / 0 behind**, 161 changed files, mergeable, **draft/unmerged**; no submitted GitHub reviews observed.
- [ADR-CC-00A](../L00/ADR_CC_00A_STANDALONE_FOUNDATION_SCOPE.md) records the product-owner's **standalone-first sequencing**, deferring `pyaccountingkit_old` reconciliation. This does not approve technical ADRs or public package identity.
- `docs/adr/ADR-CC-FOUNDATIONS-PROVISIONAL.md` explicitly states **PROPOSED, NOT APPROVED** and predates L02; its historical-reconciliation-as-G0-task wording is superseded for sequencing by ADR-CC-00A, **not** a signoff or waiver of other architecture decisions.
- [Python CI #40955190292](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190292), [PG #40955190201](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190201), [restore #40955190187](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190187) and [package #40955190309](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190309) all completed SUCCESS on Python 3.11/3.12 at the PR #33 observation SHA.
- The wheel and sdist include byte-identical SQL migrations `0001`–`0014`. Distribution version `0.0.0` is a **non-release placeholder**, with no public API/release claim.

## Architectural decisions required

| Ref | Required reviewer decision | State |
|---|---|---|
| G0-A | Package topology, import path, naming and `pyaccountingkit` distribution collision / publication boundary | PENDING |
| G0-B | Identity: CompanyId / LegalEntityId / tenant uniqueness and optional book scope | PENDING |
| G0-C | Temporal ownership: effective date vs UTC knowledge instant, no implicit now fallback | PENDING |
| G0-D | Normative reference ownership vs L03+ organization/book and L10 C10 contracts | PENDING |
| G0-E | Persistence admin topology, versioned migrations, privilege separation and documented FND-C04 N/N-1 breaking behavior | PENDING |
| G0-F | ADR dispositions for proposed L02 security/operations records and explicit development-only exclusions | PENDING |
| G0-G | Confirm selected PR #22 migration 0011 lineage, do **not** combine divergent PR #21 | PENDING |
| G0-H | External enterprise production and historic API reconciliation remain OUTSIDE this standalone development acceptance, with named future owner | PENDING |

## Decision criteria

**GO** only after the reviewer explicitly approves or documents bounded exceptions for G0-A..H on the **current, exact CI-qualified SHA** and records an attributable GitHub review / decision URL. A green CI or this author's analysis is insufficient. **NO_GO** if fundamental topology/ownership contradictions remain unresolved. Otherwise **PENDING_REVIEW**.

## Reserved review fields — intentionally unsigned

- Decision: **PENDING_REVIEW**
- Independent architecture reviewer: **UNASSIGNED**
- Review date: **NOT RECORDED**
- Reviewed exact SHA: **NOT RECORDED**
- Signed decision / GitHub review URL: **NOT RECORDED**
- Exceptions approved: **NONE RECORDED**
- G0 integration gate: **NOT SATISFIED**
