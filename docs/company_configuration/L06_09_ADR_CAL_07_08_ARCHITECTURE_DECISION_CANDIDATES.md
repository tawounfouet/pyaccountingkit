# L06-09 — ADR-CAL-07/08: Architecture decision candidates

**Date:** 2026-10-31  
**Status:** PROPOSED / OPEN / UNSIGNED — NOT ACCEPTED, NOT G6 GO.  
**Sources:** source 14 (period management) §§3,10,20; draft #95 L06-08 ADR register; source 10 C10-Q04; security #71.

## ADR-CAL-07 — Authoritative period status and posting guard

**Recommended target, pending independent decision:** Company Configuration owns calendar definitions, assignments and published configuration provenance. One separately governed **period-control authority** owns the current (tenant, entity, book, period) status and applicable locks. Execution/Ledger enforces the final signed posting predicate in a commit-critical section. This authority is a *proposed role/port*, not an existing proven production service.

A read-only C10-Q04 response or historical ConfigurationSnapshot MUST NOT authorize posting. The L06-05 response is an explicitly untrusted simulation. The owner and deployable transaction topology require an approved cross-domain decision.

**Alternatives examined:** (a) single authoritative control + Ledger enforcement (preferred for review); (b) Ledger itself owns period state (requires changing domain ownership); (c) distributed state/commit coordinator (requires real correctness proof). Reject disconnected read-based dual authority and caller-injected identity strings.

**Required acceptance:** accountable owners and signatures; explicit legal entity/book/period scope and lock semantics; independent signed-command/IAM decision pairing; revocation/fencing checks at SQL COMMIT; receipt linking authenticated decision to committed Ledger effect; concurrent close/post tests.

**Identifier correction required:** source ADR-CC-007 describes period control, but global roadmap ADR-CC-07 describes safe Policy/RuleSet language. Propose canonical ADR-CAL-07 with explicit alias/migration record; do NOT silently equate the two.

## ADR-CAL-08 — Close-vs-post linearization

**Candidate A (preferred only if same transactional DB proven):** ClosePeriod and PostJournalEntry acquire the **same** scoped period-control row lock (e.g. SELECT FOR UPDATE) in their SQL transactions. Under the lock, revalidate period status, applicable locks, monotone revision/fencing epoch and authenticated one-use issuer capability. Ledger rows plus authorization/audit/outbox persist atomically with posting. Closure persists its state change, epoch, audit and outbox atomically. If close commits first, posting must deny; if posting commits first, closure may follow.

**Candidate B (separate stores):** the shared lock is unavailable. Require a separately reviewed protocol with owner-issued fencing epochs, one-use authorization, failure recovery and Ledger COMMIT enforcement. Fail closed until race proofs are completed. An event bus is not a transaction coordinator.

| Scenario | Mandatory result |
|---|---|
| Close commits first | Posting denied, no Ledger effect |
| Post commits first | Post valid before subsequent close |
| OPEN preflight goes stale | Read does not override CLOSED control |
| IAM revocation during SQL wait | Current grant/epoch fails closed |
| Signed request replay | One-use enforcement, no duplicate entry |
| Crash, rollback and retry | Correct durable business/evidence outcome |
| Journal/source/operation locks | Only affected scope denied |
| Same event, two books | Isolation, no accidental double post |

**Mandatory proof:** real concurrent PostgreSQL/Execution writers, signed issuer, revocation adversarial cases, timeout/recovery, exact-head CI, accounting/security review. L06-06 symbolic races DO NOT satisfy CAL-SC-09 or CAL-INV-10 in production.

### Decision state

ADR-CAL-07: OPEN / PROPOSED / UNSIGNED.  
ADR-CAL-08: OPEN / PROPOSED / UNSIGNED.  
G3: HOLD_SECURITY (#71 OPEN); G4/G5/G6: NOT_APPROVED. No SQL guard, posting, merging or production approval implied.
