# L06-05 — C10-Q04 Period Status Contract Shape & Consumer Simulation (R&D)

**Date:** 2026-10-31  
**Status:** `L06_05_C10_Q04_SIMULATION_RND_CANDIDATE`; exact-head CI pending.  
**Parent:** [L06-04 DRAFT #91](https://github.com/tawounfouet/pyaccountingkit/pull/91), exact qualified SHA `8356d756accc580e5f4b81313a318edd54b34eba` → #90 → #89 → #88 → unchanged `main@acdee98ca2736d79e17174f510ac767defd90db8`. **No import from unmerged L03/L04/L05.**  
**Source of truth:** `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` §2–4 `C10-Q04 GetPeriodStatus (QRY-05)`, §5–6 immutable snapshots/events; `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §§9–12 (four clocks, C10-Q04 and guard), §11.3 illustrative DTO, §16 (CAL-SC-06/07/08/09/12/13/15/16), §20–21 ADR-CAL-07/08/09 and CAL-L5; `18` bitemporality, `19` security and `17` governance.

## 1. Source C10 contract versus what is *not* implemented

Canonical source C10-Q04:
- **Operation:** `GetPeriodStatus` (`QRY-05`) owned by **Company Configuration**.
- **Query:** exact `book_id`, `posting_date` and optionally `known_at`.
- **Expected authoritative output:** period state, **applicable** locks, **authoritative control version**, provenance; target §11.3 includes `PeriodStatusDTO`, `has_blocking_lock`, `state_version`, `calendar_version_id`, `observed_at`, and an illustrative `potentially_postable`.
- **Critical source qualification:** `potentially_postable` is *only a staleable read* and **never authorizes COMMIT**. Source §10 explicitly requires a close-vs-posting fence at Ledger COMMIT, not a mere check-then-insert.

**This PR does not implement C10-Q04**. No real route/method `get_period_status`, no provider registration, no published CalendarVersion, independent book proof, signed actor, authoritative lock applicability/coverage, control version, current `observed_at`, status release, or Ledger commit guard is present. It implements **only a non-authoritative wire-shape simulation and a negative consumer contract**.

We intentionally **do not expose** `has_blocking_lock`, `potentially_postable`, `can_post`, `posting_eligible`, `control_version`, or `published_at`. These fields would falsely imply validation of a real journal/source/operation and live authority. Instead, a typed set of observed locks and an unverified diagnostic disposition are returned.

## 2. Strict R&D-only wire schema

`SCHEMA_VERSION = "l06-05-c10-q04-simulation-v0"` (intentionally **NOT** `1.0`); `AUTHORITY = "UNTRUSTED_CANDIDATE_SIMULATION"`. Wire examples may be produced only by `simulate_period_status_contract` or `FiscalC10Q04SimulationService.simulate` using an exact L06-03 `PeriodControlCandidateDiagnostic` already pinned to an L06-02 `BookCalendarCandidateReadReceipt`.

| R&D wire field | Meaning | Status |
|---|---|---|
| `schema_version` | `l06-05-c10-q04-simulation-v0` | Not production schema |
| `authority` | `UNTRUSTED_CANDIDATE_SIMULATION` | Never authoritative |
| `eligible_for_posting` | **Always JSON false** | Never proof of eligibility |
| `tenant_id/company_id/legal_entity_id/book_id` | Exact claimed book scope | NOT signed/verified book ownership |
| `posting_date`, `known_at` | Exact explicit date + UTC-normalized aware as-known time | Not SQL COMMIT time |
| `calendar_candidate_version_id`, `period_id`, `period_code` | Exact L06-02 candidate relationship | NOT published calendar/control version |
| `observed_status`, `state_revision` | L06-03 *candidate* observation | Not authoritative state |
| `diagnostic_disposition` | Unverified L06-03 classification | No ALLOW or postable state |
| `observed_lock_observations` | Sorted ID/scope/target, **not applicable lock evaluation** | No `has_blocking_lock` |
| `calendar_candidate_digest`, `period_control_candidate_digest` | Links to local source receipts | SHA-256 **not signature** |
| `content_digest` | Canonical wire checksum | Tamper-detection only |

Canonical wire: JSON UTF-8-equivalent text, alphabetic object keys, compact separators, ISO business date, timezone-aware `known_at` normalized to UTC 6 digits and `Z`; no extra fields, no missing fields, no duplicate JSON keys accepted (strict canonical serialization on consumption). Typed UUIDs are lower-case canonical strings. Consumers reject noncanonical input even if values could otherwise be parsed.

`SimulatedPeriodStatusResponse` is frozen and self-checks disposition consistency with observed status and lock presence. Lock objects are typed `ObservedLockWireCandidate` and are **never classified as applicable/blocking** without explicit journal/source/operation input, a normative lock policy and an independently complete data source.

## 3. Producer simulation and consumer compatibility

```text
 L06-02 BookCalendarCandidatePreviewService  [fake read grant #1]
          |
 L06-03 PeriodControlCandidateDiagnosticService [fake read grant #2]
          | L06-03 exact book/version/period + as_of/known_at + checksum
          |
 FiscalC10Q04SimulationService.simulate     [fake read grant #3]
          |
 simulate_period_status_contract(...)
          └── SimulatedPeriodStatusResponse.to_wire() (UNTRUSTED)
                         |
             inspect_simulated_period_status_wire(
               wire, SimulatedPeriodStatusQuery(book, posting_date, known_at)
             )
                         |
         Strict schema/canonical/checksum/typed value/scope/date validation
                         |
            reject_simulated_status_for_posting(...)
                         |
              ALWAYS raises UNTRUSTED_PERIOD_STATUS_FOR_POSTING
                        (including OPEN + no observed locks)
```

The producer **must** reject mismatched book scope, `posting_date` vs `as_of`, or `known_at` vs exact L06-03 receipt. It re-verifies L06-03 nested candidate digests. The consumer rejects foreign book/tenant/company/entity, wrong posting date or knowledge instant, invalid UUID, invalid lock scope/target, unknown status/disposition, elevated authority flags and tampered JSON.

**Key property:** even a completely valid simulated response never satisfies posting authority. `reject_simulated_status_for_posting` returns **no success value** and always raises the typed `UntrustedPeriodStatusForPosting`. This is a **negative simulation contract**, not a security reference monitor: no caller is forced to invoke it; a future real Ledger guard needs architectural enforcement at COMMIT.

## 4. Design patterns & explicit gaps

- **DTO / Anti-Corruption Layer:** separate immutable wire objects from L06-03 domain candidate observations, no accidental substitution for real C10 `PeriodStatusDTO`.
- **CQRS / DIP / Hexagonal:** read-only simulation service composes L06-02 and L06-03 query services, backed only by fake test-granted readers. There are three separate fake preview actions; they are not signed IAM.
- **Value Objects / temporal modeling:** typed UUID, `posting_date`, `known_at`, version ID, revision, observed scoped locks, canonical JSON digest.
- **Fail closed / defensive parsing:** no fallback to current version, no optional implicit `known_at`, no operation scope-to-lock inference, no unknown/new schema fallback, no error-to-allow transition.
- **Security:** integrity checksum does not prove provenance, availability, authenticity, durable snapshots, external complete lock inventory, or caller authorization.

**Unimplemented canonical source acceptance:** `CAL-INV-04` (real status+lock posting), `CAL-INV-07` (published CalendarVersion), `CAL-INV-08` (signed/persisted historical replay), `CAL-INV-10` and `CAL-SC-09` (actual concurrent close-vs-commit serialization), `CAL-INV-12` (audited lock changes), `INT-AT-08` live C10 consumer validation. No real multi-book PCG/IFRS/SYSCOHADA legal confirmation.

## 5. Qualification and handoff

`tests/unit/company_configuration/test_l06_05_c10_q04_simulation.py` covers six statuses, OPEN/no-lock refusal, journal lock not treated as universally blocking, incomplete evidence, schema/authorization flag attacks, malformed or duplicate-key JSON, mismatched scope/posting/knowledge time, tampered digest and source receipt, fake separate grants, no SQL/write/real API imports.

- [x] R&D-only versioned DTO shape with strict canonical wire.
- [x] Historical candidate source provenance and immutable status/lock observations.
- [x] Strict simulated consumer compatibility and always-denied posting adapter.
- [x] Read-only compositional producer simulator.
- [x] Adversarial tests including known unsafe `OPEN` and staleable reads.
- [ ] Exact-HEAD Python 3.11/3.12 + Ruff, PostgreSQL + recovery, wheel/sdist original 14 migrations parity.
- [ ] Real publisher/Outbox, signed IAM/SoD, validated normative calendar/book ownership, C10-Q04 provider, atomic Ledger COMMIT fence and gate G6; **not included**.

**Gates remain:** G0/G1/G2 `PENDING_REVIEW`; G3 `HOLD_SECURITY`, [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN; G4/G5/G6 `NOT_APPROVED`; ADR-CAL-01..10 OPEN; no merge/release.

**Next:** L06-06 — atomic close-vs-posting **design, linearizability model, negative race harness contracts and blocker proofs only** until independent signed SQL authority and governance are approved. A test that compares two local function calls without real transactions **cannot qualify** actual fencing or posting safety.
