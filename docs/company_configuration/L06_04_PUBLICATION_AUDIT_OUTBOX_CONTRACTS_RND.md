# L06-04 — Calendar Publication, Audit & Outbox Contracts (R&D only)

**Date:** 2026-10-31  
**Status:** `L06_04_PUBLICATION_AUDIT_OUTBOX_CONTRACTS_RND_CANDIDATE` (exact-HEAD CI pending).  
**Stack:** [L06-03 draft PR #90](https://github.com/tawounfouet/pyaccountingkit/pull/90) @ `4762b5d218275dbf29d1b674a4ba8d54f20f8f12` → #89 → #88 → `main@acdee98ca2736d79e17174f510ac767defd90db8`. No import of L03/L04/L05 unmerged drafts.  
**Primary source:** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §5 (CalendarVersion), §7.2 (authorized transitions + atomic audit/Outbox), §9–10 (clocks, COMMIT race), §12 (`CAL-INV-05/06/07/08/10/12`), §13 (SQL constraints), §14 (events), §16 (CAL-SC-12/13/15–17/20), §18–20 (audit, ADR).  
**Governance source:** `17_COMPANY_CONFIGURATION_CONFIGURATION_LIFECYCLE_AND_GOVERNANCE.md` §§4, 7–10, 12–14 (approval validity, SoD, publication/Outbox atomicity, idempotency, conflict exclusion), `18` (temporal version truth), `19` (security) and `20` (persistence).

> **Explicit scope change versus the source's CAL-L4 target:** the source describes a real publication, audit, and transactional Outbox. This L06-04 PR **cannot** create them while G3 is blocked. It delivers an **unapproved non-executing proposal and a gap diagnostic**, not `CAL-L4` completed.

## 1. Architectural boundary

```text
CalendarVersionCandidate (L06-02, not published)
   └── full structural manifest + candidate content digest
                         |
                         v
CalendarPublicationRequestCandidate (unapproved immutable intent)
  CalendarPublicationIntentId
  calendar candidate exact version ID/digest
  entity scope, effective interval
  expected prior candidate version? (not authoritative head)
  idempotency_key, correlation_id, requested_at
  reason + source_ref
  PublicationRoleClaimCandidate[]  (UNVERIFIED, never signed ApprovalEvidence)
                         |
               pure preview, no I/O
                         v
CalendarPublicationContractDiagnostic
  + CalendarAuditIntentCandidate   (not a committed AuditRecord)
  + CalendarOutboxIntentCandidate  (not an emitted/committed event)
  + missing_role_claims
  + six UnverifiedPublicationGate values
  + full deterministic SHA-256 digest
  + committed=false, event_emitted=false, signed=false
  + EXTERNAL_GOVERNANCE_AND_COMMIT_GATES_UNVERIFIED

THERE IS NO PATH to:
 SQL COMMIT | PublishCalendarVersion | CalendarVersionPublished
 authoritative C10-Q04 | Ledger | SignedActor | actual transaction Outbox
```

These objects are **not new authoritative domain entities**. They are ephemeral, in-memory draft intents to help reason about future interfaces and negative tests.

### Design conventions used

- **DDD / Value Object:** distinct typed IDs `CalendarPublicationIntentId`, `CalendarAuditIntentId`, `CalendarOutboxIntentId`; immutable candidate request and role claims.
- **SoC / Hexagonal:** pure domain preview separate from read-only CQRS service (`CalendarPublicationContractPreviewService`) and `CalendarPublicationIntentsReader` Protocol; `MemoryCalendarPublicationIntents` is a non-authoritative test fixture.
- **Fail closed:** reject missing or invalid version, bad digest, foreign tenant/company/entity, noncanonical idempotency key, overlapping local intents, duplicated roles/actors, future or expired role claims, mixed identity catalogs.
- **Idempotency key:** the key is **proposed only**. No durable uniqueness guarantee or idempotent publication is established. Colliding keys in the visible candidate catalog cause a typed conflict.
- **Separation of Duties:** role claims use enum `PREPARER/REVIEWER/APPROVER/PUBLISHER`; duplicated role or actor rejected *in the supplied catalog*. User-supplied actor references are NOT authenticated identities and this does not prove independent approvers.
- **Integrity:** canonical JSON/UTF-8 sorted serialization, UTC-normalized instants and deterministic local SHA-256. Event-intent and audit-intent UUIDv5 values are derived from the publication request ID for **reproducibility**, not from any signed or committed transaction.
- **No circular authority:** unlike the source §14's real `CalendarVersionPublished`, the only event-intent type is `CALENDAR_VERSION_PUBLICATION_PROPOSED`; no public event bus, consumer, live Ledger or downstream cache should consume it as a real published version.

## 2. What the diagnostic can prove locally

| Check | Candidate behavior | Production proof it DOES NOT provide |
|---|---|---|
| Exact version identity | Content digest precondition + full nested L06-02 validation | Existence of an approved and durably published `CalendarVersion` |
| Business validity | Intent interval contained by candidate version interval | Independently authorized effective-date publication |
| Recorded time | `requested_at` is aware and within candidate knowledge | SQL transaction timestamp / attested recording |
| Canonical identifiers | Typed request, audit, Outbox intent IDs | Durable audit/event IDs, non-repudiation |
| Local collision detection | Duplicate ID, idempotency key or overlapping candidate validity rejected | Serializable uniqueness across writers, retry correctness |
| Role claim consistency | Distinct unverified roles/actors, bounded claim dates | Signed IAM actor, independent approver, legal authority, verified SoD |
| Audit intent | Deterministic correlation/digest/action proposal | Append-only AuditRecord committed with publication |
| Outbox intent | Deterministic correlated unpublished event proposal | Row inserted with version/audit under one transaction, eventual delivery/replay |
| Pinned digest | Detects in-process tampering when verified | Cryptographic signature/trust anchor or immutable storage |
| Read permissions | Fake `AuthorizationPort` + tenant check | Authorized production reader or issuer |

### Six external hard blockers (all always reported)

`SIGNED_ACTOR_AND_ISSUER`; `INDEPENDENT_APPROVAL_AND_SOD`; `NORMATIVE_AND_DEPENDENCY_VALIDATION`; `AUTHORITATIVE_CURRENT_HEAD_AND_IDEMPOTENCY`; `ATOMIC_VERSION_AUDIT_OUTBOX_COMMIT`; `PUBLISHED_SCOPE_AND_TEMPORAL_EXCLUSION`.

There is **no method, enum, boolean, or status meaning READY, APPROVED, COMMITTED, POSTABLE or LIVE**. The preview's `committed=false`, `event_emitted=false`, `signed=false` flags are non-authorizing statements, not runtime state.

## 3. Temporal and concurrent correctness

The source distinguishes business date, accounting posting date, recorded/published instant, and SQL commit instant. Here `effective` is only a proposed business-date interval, `requested_at` is an **unverified** client-supplied aware timestamp, and the candidate version has an as-known `KnowledgeInterval`. None of these represents an actual COMMIT or authorized `published_at`.

`preview_calendar_publication_contract(request,competing_intents)` verifies **the entire caller-provided catalog** (including unrelated effective windows). It refuses:
- any duplicate request ID, even with the same content;
- any matching idempotency key in that local catalog, even if different request ID;
- any overlapping effective-date publication proposals for the same calendar/scope;
- any cross-tenant/company/entity intent in the supposedly scoped read results.

It **cannot** prove global absence of contenders or race freedom in SQL. A real implementation requires compare-and-swap against current published head, uniqueness/exclusion constraints at COMMIT, stable idempotency receipts and rollback/retry tests.

## 4. Security, audit and Outbox are intentionally NOT implemented

The following source requirements remain open and unproven:
- **`CAL-INV-07` / `CAL-SC-17`**: independently authorized, durably immutable published version; a draft digest is not a published immutability guarantee.
- **`CAL-INV-05/06/12` / `CAL-SC-10/11/15/20`**: real authorized period transitions, expected-version CAS, approved reopenings, immutable audit and Outbox atomic persistence. This PR has no transition executor.
- **`CAL-INV-08` / `CAL-SC-12/13`**: actual bitemporal published historical snapshots and consumer truth, beyond R&D candidate replay.
- **`CAL-INV-10` / `CAL-SC-09`**: close-vs-posting **TOCTOU** serialization/fencing at the authoritative Ledger COMMIT boundary, not simulated by review intents.
- **GOV-05/10/11/18** (source `17`): valid approved review, publication+audit+Outbox one transaction, idempotency and concurrent publication exclusion.

Any future live `PublishCalendarVersion` writer must be a **separate, gated implementation**, with an independently signed actor/issuer decision at COMMIT, signed approvals and SoD, audit + Outbox persistence in one transaction, exact version pinning, transactional idempotency, concurrency and restart recovery, and real consumer contract tests. **No source spec equates an in-process SHA-256 digest with a signature.**

## 5. Explicit open decisions / gates

`ADR-CAL-01..10` remain **OPEN**, especially ADR-CAL-02 (publication vs period-state aggregate), ADR-CAL-07/08 (authoritative period guard, COMMIT fencing), ADR-CAL-09 (temporal publication and replay), ADR-CAL-10 (jurisdiction). Ownership and publication granularity remain additionally subject to governance source `17`.

G0/G1/G2 `PENDING_REVIEW`; **G3 `HOLD_SECURITY`**, security [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) open; G4/G5/G6 `NOT_APPROVED`. No main merge, no new migration, no publisher API, no release. Package `0.0.0` remains an unpublished placeholder.

## 6. Test plan and next cut

`tests/unit/company_configuration/test_l06_04_publication_audit_outbox_contracts.py` tests original vs fabricated digests, role claim expiry and SoD, missing claims, deterministic identifiers, UTC normalization, duplicate requests, idempotency collisions, concurrent effective windows, exact scope leaks, forged committed event claims, fake-gated read-only service and unchanged historical SQL migration count.

- [x] Typed version-pinned publication request and untrusted role claims.
- [x] Deterministic audit/Outbox **intent** contracts, always non-executing.
- [x] Read-only query service and candidate memory adapter.
- [x] Structural conflicts and negative security cases.
- [ ] Exact-HEAD Python 3.11/3.12 + Ruff, PostgreSQL/recovery, wheel/sdist 14-migration parity.
- [ ] Authorized independent IAM and governance, SQL publication/audit/outbox, real concurrency/fencing tests, stable release and G6 gate; **outside R&D**.

**Next safe scope after CI:** L06-05 **C10-Q04 contract shape and consumer compatibility simulations only**, not a live authoritative `GetPeriodStatus`. Alternatively, close remaining CAL ADRs and security blocker #71 before starting live release features.
