# L06-03 — Period Status, Orthogonal Locks & Transition Diagnostics (R&D)

**Date:** 2026-10-31  
**Status:** `L06_03_PERIOD_CONTROLS_RND_CANDIDATE` pending exact-HEAD CI. **No authoritative status/lock, closing command, posting permission or C10-Q04.**  
**Parent:** draft [L06-02 #89](https://github.com/tawounfouet/pyaccountingkit/pull/89), qualified SHA `56693940883543d533c0b8ec7af83f351a927d83`; stack #89→#88→main, **no unmerged L03/L04/L05 imports**.  
**Canonical spec:** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §7 states/transitions, §8 locks/deviations, §9 four clocks, §10 close-vs-posting TOCTOU, §11 C10-Q04 target, §12 CAL-INV-04/05/06/08/10/12, §14 proposed events, §16 CAL-SC-06..11/15/16/20, §20 ADR-CAL-02/04/05/06/07/08/09, §21 CAL-L3. **All target ADRs remain OPEN.** Also `18` temporal snapshots.

## 1. Source-aligned R&D choices (not approvals)

Source §7.1 provides statuses `DRAFT`, `FUTURE`, `OPEN`, `SOFT_CLOSED`, `CLOSED`, `LOCKED` and `ARCHIVED`. It expressly prefers `LOCKED` as an **orthogonal restriction** rather than the exclusive status, so this prototype models six **`PeriodStatusCandidate`** statuses and separate lock observations. These are **unsigned, time-bounded observations**, not published committed state or proof of a real accounting period. `PeriodLockScopeCandidate` retains four source §8 categories: `GLOBAL_BOOK_LOCK` (no target), `JOURNAL_LOCK`, `SOURCE_LOCK`, `OPERATION_LOCK` (exact canonical target code). The source's normative restrictions, operator codes, lock applicability and role policy are NOT approved.

```text
BookCalendarCandidateReadReceipt (L06-02)
   book scope, exact calendar candidate version + period ID
   business as_of + historical known_at, local digest
                    |
   +----------------+------------------------------------------+
   |                |                                          |
PeriodState       PeriodLock                      PeriodTransitionDeclaration
Observation       Observation                     Candidate (unexecuted)
  status            scope / target                  from_status / to_status
  revision          active true/false               expected/proposed revisions
  knowledge         revision, knowledge             actor_ref / reason / declared_at
  source_ref        source_ref                      source_ref
   |                |                                          |
   +----------------+----------------------+-------------------+
                                          |
                         preview_period_controls_candidate
                             full catalog consistency
                             exact scope + version + period
                             known_at state selection
                             active observed locks
                             visible declared events
                                          |
                           PeriodControlCandidateDiagnostic
                             disposition, nested digest
                             DOES NOT HAVE can_post/post/commit
```

**DDD / design:** explicit Value Objects and typed UUID identities (`PeriodStateCandidateId`, `PeriodLockCandidateId`, `PeriodTransitionCandidateId`), immutable snapshots, pure Domain Policy, original-known vs restated bitemporal reads, Query CQRS, hexagonal Protocol/Mem in-process fixture, SoC/DIP. No `PeriodStatusDTO` or published C10 contract implemented.

## 2. Refusal and diagnostic semantics

A request must reference an already verified **candidate** book calendar receipt from L06-02. Every state, lock and transition must use **the exact same** book/tenant/company/legal entity, `CalendarCandidateVersionId` and `AccountingPeriodId`. The entire supplied catalog is checked even for future/nonactive entries.

- State observations are versioned by strictly positive `state_revision` with dated `KnowledgeInterval`. Exactly **one state** must be applicable at the receipt's `known_at`. Duplicated ID/revision, overlapping knowledge and regressions are refused.
- Lock observations carry a stable lock ID, distinct positive revision, typed scope, canonical exact target if scoped, explicit boolean active flag and a knowledge window. Nonoverlapping revisions for the same ID can represent an activation then a release. Duplicate/overlapping/regressing lock revisions and target-scope changes under the same ID are refused.
- Transition declarations are **not executed**; fields include explicit state pair, expected and proposed consecutive revision, aware declared instant, actor reference, reason and provenance. Duplicated declaration IDs are refused. Declaration is visible only at or after its instant, but does **not change** observed state. Neither approval signatures, SoD, event delivery nor audit persistence is proven.
- `ObservationCompleteness.DECLARED_COMPLETE_RND` represents only an **unverified assertion** about the supplied catalog. `INCOMPLETE_RND` returns incomplete-evidence diagnostic. Neither can certify independent completeness of active locks.
- The diagnostic disposition intentionally has **no ALLOW or POSTABLE value**:
  - `NON_OPEN_CANDIDATE_STATUS`: observed period is not OPEN;
  - `LOCKS_OBSERVED_SCOPE_UNEVALUATED`: one or more active lock observations, but journal/source/operation applicability has not been evaluated;
  - `NO_OBSERVED_LOCKS_UNVERIFIED`: OPEN + none in this data, **never posting permission**;
  - `INCOMPLETE_CANDIDATE_EVIDENCE`: explicitly incomplete catalog.

No journal classification or operation is passed to the pure preview, so a scoped lock must not be interpreted as a globally applicable denial; a global lock is likewise **not a commit-time gate** in this slice.

## 3. Bitemporal and canonical integrity

`PeriodControlCandidateDiagnostic` pins L06-02 `BookCalendarCandidateReadReceipt.content_digest`, full typed state/lock/declaration rosters, exact status ID and lock IDs, business date, UTC-normalized knowledge date, visibility of declared events and candidate completeness claim. Canonical JSON and `sha256:` digest follow the L06-02 sort-key + stable UUID/lock revision convention. `verify_integrity()` rechecks nested book/calendar candidate and the entire evidence catalog; changed references, observations, locks or disposition are refused.

**Hash alone is NOT a signature or independent audit.** A privileged in-process caller could mutate structures and recompute digests. There is no durable, append-only transition store, trusted signature, or legal issuer in L06-03.

Synthetic replay example: on business date `2027-02-15`, knowledge cutoff `2027-02-01` observes `OPEN`; for `known_at=2027-03-01`, an amended observation is `CLOSED`. A lock may also transition `active=true` → `active=false` at the same boundary. Historical replay **must not** be used as an authorization for a new journal.

## 4. Query-side boundaries

`PeriodControlCandidateDiagnosticService` composes L06-02 `BookCalendarCandidatePreviewService` and untrusted `PeriodControlCandidateReader`. Before each read it calls fake `AuthorizationPort.require` on `calendar.period.controls.candidate.preview`; L06-02 additionally checks `calendar.assignment.candidate.preview`. It rejects untyped principal shapes and tenant mismatches. Test-only `MemoryPeriodControlCandidates` returns scope-filtered tuples; the **pure domain independently rejects** malicious reader leakage.

`TrustedPrincipal` is only a shape from L02, not a live verified actor or signed permission. There is **no** live book membership, ownership evidence, PostgreSQL mutation, Outbox, C10-Q04 or signed audit trail.

## 5. Source acceptance vs genuine missing guarantees

| Source scenario/invariant | Local R&D property | Production/integration gap |
|---|---|---|
| CAL-INV-04 / CAL-SC-06..08 | Distinguishes OPEN/non-OPEN and observed locks | **No posting guard**, permission or status authority; cannot claim acceptance |
| CAL-INV-05 / CAL-SC-15 | Candidate expected/proposed revision structural check | No committed CAS, concurrency race or idempotency |
| CAL-INV-06 / CAL-SC-10/11 | Transition declaration includes actor/reason but no executable reopen | No real approvals, dual-control or exception |
| CAL-INV-08 / CAL-SC-12/13 | Synthetic status/lock knowledge replay, pinned version from L06-02 | No signed published snapshot |
| CAL-INV-10 / CAL-SC-09 | Explicit STOP: historical OPEN insufficient | **No close-vs-posting COMMIT serialization/fencing** |
| CAL-INV-12 / CAL-SC-20 | Lock revision, provenance and declared event history candidate | No append-only signed audit/Outbox |
| CAL-SC-16 | Declarations do not implicitly modify state | No real delayed event processing or cache invalidation |

**TOCTOU / security STOP:** Source §10 requires an authoritative check protected against the race between a period close and a Ledger COMMIT. Neither a cached `OPEN`, a complete-looking lock catalog, nor an unsigned C10-like DTO is enough. Do not introduce `can_post`, `potentially_postable`, `close`, `reopen`, `post`, or an optimistic execution command in this slice. COMMIT guards require independent security #71 remediation and CAL ADR-CAL-07/08 resolution.

## 6. Tests, gates, next cut

`tests/unit/company_configuration/test_l06_03_period_control_diagnostics.py` covers six statuses, four lock scopes, canonical validation, duplicated/overlapping/regressing state and lock revisions, historical original vs amended, lock activation/release, event visibility without mutation, foreign tenant/book/period/version, bitemporal UTC canonicalization, nested tampering, fake grant denial and architectural SQL/HTTP isolation.

- [x] Immutable candidate status/lock/transition observation model.
- [x] Read-only candidate diagnostics with explicit **non-authorizing** dispositions.
- [x] Historical knowledge cutoff, digest-bound exact L06-02 reference and negative tests.
- [x] CQRS/hexagonal read-only service and fake memory reader.
- [ ] Exact-HEAD Python 3.11/3.12 + Ruff, PG Foundation/recovery, wheel/sdist 14 migration parity.
- [ ] Signed independent actor, published states, real SQL CAS & audit/outbox, C10-Q04, actual close-vs-posting tests, gate G6 (NOT in R&D).

**Gate truth:** G0/G1/G2 PENDING_REVIEW, G3 HOLD_SECURITY with [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN; G4/G5/G6 NOT_APPROVED. No main merge or release. ADR-CAL-01..10 all OPEN.

**Next candidate slice:** L06-04 — governed publication, audit and Outbox **contract proposals and negative proofs only** until G3/G6 approvals, or alternatively L06-03 consolidation/ADR review. Any live writer requires a separate authorized production gate, not an incremental fake.
