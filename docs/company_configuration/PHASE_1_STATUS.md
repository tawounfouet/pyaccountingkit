# Phase 1 - Implementation status

Date: 2026-10-29

| Gate | Status | Evidence |
|---|---|---|
| G0 - Audit/baseline | PENDING REVIEW | `evidence/L00/repository_baseline.md`; historical repository/package reconciliation still open; issue #1 |
| G1 - Domain kernel | IN PROGRESS | L01 shared VOs + first `LegalEntity` aggregate; `L01_INVARIANT_TRACEABILITY.md`; `evidence/L01/increment_02.md`; issue #2 |
| G2 - Ports/technical foundations | NOT STARTED | No durable storage, security, audit or outbox implemented |

## Prior verified increment

Commit `cbd0936d6bfcf869baff6f1c4cddd008c55ff34e`: GitHub Actions run #6 succeeded on Python 3.11/3.12 with 44 local tests from the initial increment. This is **not** a G0/G1 sign-off.

## Current candidate increment

Adds minimal identity-stable `LegalEntity`, `JurisdictionCode`, negative tests, Hypothesis temporal properties, and traceability. **CI evidence and exact SHA must be appended only after run completion.**

**Scope warning:** no complete CFG-01..CFG-10 implementation, production deployment, posted entries or stable release. Cross-context invariants remain with their rightful owners.

## L02 increment 01 (in progress; not qualified)

Added application ports and an in-memory, staged unit-of-work vertical proof for create/read/rename of a `LegalEntity`. A default-deny authorizer is a **fake**, not IAM or production enforcement. Local tests and injected failure prove only same-process in-memory behavior. See `evidence/L02_increment_01.md` for caveats and open ADRs. **G2 remains unapproved**, as do G0 and G1; SQL, durable migration, object-level DB isolation, production audit and C10 are pending.
