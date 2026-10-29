# G0 — Standalone repository / architecture gate decision

**Decision:** PENDING_REVIEW (no architecture GO / NO_GO signed)  
**Project:** recent `tawounfouet/pyaccountingkit`; historical integration explicitly deferred.  
**Target integration PR:** [#32](https://github.com/tawounfouet/pyaccountingkit/pull/32), baseline qualified SHA `098f6de80b916d0545b65c2dfec9357f854cddcd`.  
**Reviewer:** NOT ASSIGNED / **Approved SHA:** NONE.

## Evidence established

- Ownership scope and historical deferral: [ADR-CC-00A](../L00/ADR_CC_00A_STANDALONE_FOUNDATION_SCOPE.md), reflecting product-owner sequencing only.
- Package: `src/pyaccountingkit/company_configuration`; distribution `pyaccountingkit==0.0.0` is a non-release scaffold. FND-C06 wheel and source archive import checks are green.
- L01 domain: explicit runtime UUID wrappers for company/legal entity/book/draft/version, mandatory tenant/company/legal-entity scope, separate effective/knowledge half-open intervals.
- L02: application ports and SQL adapters with tenant-bound login policies; operations and IAM source authority are **not** inferred from untrusted event strings.
- CI checkpoint [#40954760622](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760622) Python, [#40954760659](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760659) PostgreSQL, [#40954760543](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760543) recovery, [#40954760631](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760631) packaging: all SUCCESS on 3.11/3.12 for **the earlier SHA**, not approval of later commits.

## Architecture choices still requiring authorized disposition

| Decision | Proposed contract | Remaining independent review |
|---|---|---|
| Repository/packaging | Recent repo is the **development source** through standalone Foundation, historical API/package cutover deferred | Confirm no unintended public distribution/canonical package promotion |
| Domain identity and entity scope | UUID VO runtime types, tenant/company/legal entity, optional book for scope; no membership claim | Explicit identity/equality/SQL unique-key cardinality and tenancy model sign-off |
| Effective/knowledge time | date vs aware instant, both half-open; aware instants compared in UTC across DST fold | Approve temporal ADR/ownership and versioning contract |
| Normative references / digest | Versioned framework reference, local canonical JSON SHA256 | No claim of standards truth or cross-language canonical wire format until ADR |
| Persistence and publication | Unit of Work + audit + outbox/inbox; immutable SQL migrations, forward-only | Agree schema/topology and future aggregate/organization layering |
| Security boundary | Distinct SQL session roles and conditional privilege controls; development only | Approval of privilege/identity threat boundaries is G2, not implied by G0 |

The older `docs/adr/ADR-CC-FOUNDATIONS-PROVISIONAL.md` remains **PROPOSED**. ADR-CC-01/02/03/04/05/06/08 are referenced as future architecture decisions, but there is no evidence here that the corresponding authoritative approvals have occurred. Do **not** infer approval from implementation.

## Required sign-off

A named independent architecture reviewer must confirm the listed scope/topology/ADR dispositions, examine PR #32 diff and constraints, and record explicit **GO** or **NO_GO** against its **current exact HEAD**. Until then G0 remains pending; CI alone cannot sign this decision.
