# L03-03 / ORG-4a — Organization membership application commands

**Status:** R&D implementation candidate, **not full ORG-4 or G3 closure**  
**Source:** [L03-01 PR #35](https://github.com/tawounfouet/pyaccountingkit/pull/35) → [L03-02 PR #37](https://github.com/tawounfouet/pyaccountingkit/pull/37) → this increment.  
**Date:** 2026-10-29.

## Implemented use cases

- `AssignOrganizationMembership`: typed entity-level scope, membership id, affiliation kind, exclusivity and effective interval; explicit provenance, reason, correlation and request keys.
- `EndOrganizationMembership`: immutable revision of a membership through an effective end date, expected revision (optimistic concurrency) and provenance. Never reparents the identity or infers legal control.
- `OrganizationMembershipService`: **Application layer** orchestrates `AuthorizationPort`, trusted `TrustedPrincipal` (externally verified; never constructed from a caller's JSON), explicit clock, `OrganizationMembershipUnitOfWork`, digest-based idempotent replay and typed Domain entities.
- `PostgresOrganizationMembershipRepository` participates in the **same `PostgresUnitOfWork` transaction** as membership insertion, L02 append-only audit, Outbox and idempotency receipt. No direct repository-level commit.
- Full command path uses tenant-scoped DB role and existing L02 tenant-bound, transaction advisory lock before request replay or write. Existing 0015 company FK, legal-parent check, SQL revision and exclusivity guards still apply.

## Verified invariants to qualify in CI

1. Authorized assign → exactly one membership revision, idempotency receipt, audit record and Outbox event, with identical correlation.
2. Exact replay (same request id and digest) → identical receipt and no duplicate side effects; mismatched payload rejects.
3. End → version 2 with the prior version preserved; as-known temporal query returns different evidence before/after amendment.
4. Stale expected revision and duplicate membership id reject without additional evidence.
5. Rejected principal or tenant mismatch does not write.
6. Injected precommit crash rolls back all four writes atomically.
7. Concurrent identical request is serialized at tenant transaction lock and returns same receipt.

**Not implemented:** RegisterCompany/RegisterEstablishment/RegisterLegalIdentifier command flows with full transactional evidence, arbitrary membership transfer, signed actor/claim verification, per-event C10 schema, production-level audit integrity, external publisher integration or real roles/vault provisioning. No schema changes in this incremental command PR. Full ORG-4/G3 remains **IN PROGRESS**.

## Patterns & design concepts

DDD Application Service and immutable Domain entities; CQRS command boundary; Hexagonal ports with Dependency Inversion; Unit of Work for atomic commit and rollback; Repository for scoped history; Optimistic Concurrency and tenant advisory lock; Transactional Outbox; canonical digest-based Idempotency Key; fail-closed authorization; explicit effective/knowledge bitemporality.

**Important:** the existing L02 `audit_records` and `outbox_events` use `entity_id` to identify the *legal entity*, while `revision` in these ORG-4 events represents the **organization membership revision**. This is an internal proof contract; publishing events externally must define a distinct membership entity id and schema, to avoid downstream confusion.
