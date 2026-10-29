# L00 - Canonical repository baseline (2026-10-29)

Status: **OBSERVED / G0 NOT APPROVED — standalone recent-repository scope**

## Repository identity

- Canonical URL provided: `https://github.com/tawounfouet/pyaccountingkit`.
- GitHub connector repository ID: `1438070924`.
- Access: public; authenticated permission included push/admin at observation.
- Default branch metadata: `main`.
- **Before initialization**, API returned `size: 0`, no branches, no issues, and the commits API returned `409 Git Repository is empty`.
- Therefore the pre-bootstrap baseline is **`NO_INITIAL_COMMIT`**, not an invented SHA.
- Initialization commit created: `cb746be7ae95146d2bd50ce1aac049ea6da2d15e` (`README.md` on `main`).
- Foundation development branch: `feat/company-config-phase1-foundations` (based on this commit).

## Evidence boundaries

This baseline proves **only** the state of this particular GitHub repository at inspection. It does not prove that no historical PyAccountingKit code exists in another repository, PyPI distribution or local workstation.

There were no existing source files, tests or migrations to run before initial bootstrap: pre-bootstrap test baseline is **N/A - repository empty**, not passed.

## Gap matrix (observed repository, before foundation branch)

| Capability | Status | Evidence | Action |
|---|---|---|---|
| Source package and shared domain primitives | MISSING | Empty repo, no branches or commits | BUILD minimal L01 |
| Repository / Unit of Work / persistence | MISSING | Empty repo | DEFER to L02 |
| Authorization / audit / outbox | MISSING | Empty repo | DEFER to L02 |
| Organization, books, charts and calendar | MISSING | Empty repo | DEFER to L03-L06 |
| Policy, dimensions, governance | MISSING | Empty repo | DEFER to L07-L09 |
| C10 producer and consumer proof | MISSING | Empty repo | DEFER to L10 |
| UI / Configuration Explorer | MISSING | Empty repo | DEFER to L11 |
| Historical artifact reconciliation | DEFERRED / OUTSIDE STANDALONE G0 | Historical codebase separately identified; explicit [ADR-CC-00A](ADR_CC_00A_STANDALONE_FOUNDATION_SCOPE.md) sequencing | Complete recent repo Foundation first, then separate integration ADR |

## Preliminary work planned on this branch

- Package and pure Python primitives with negative tests (L01 part 1).
- Provisional ADR notes (not approved).
- CI to **run** checks; an unobserved CI run is not evidence that CI is green.

## Pending G0 sign-off (recent-repository standalone scope)

- [x] Canonical repository URL and pre-bootstrap no-commit state recorded.
- [x] Bootstrap SHA and foundation branch recorded.
- [x] First gap matrix for this GitHub repository.
- [x] Record existing historical codebase as a **separate deferred integration/release workstream** (product-owner sequencing in ADR-CC-00A). No historical reconciliation is required to qualify this repository's standalone **development Foundation**.
- [ ] Review/approve ADRs for identity, multi-tenant isolation and placement.
- [ ] Record a reviewed, reproducible CI baseline on the exact branch SHA.
- [ ] Reviewer approval of G0 decision.

**Gate verdict: PENDING.**
