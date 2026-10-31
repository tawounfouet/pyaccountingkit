# L06-06 — Close-versus-Posting Fencing, Ordering & Concurrency Model (R&D)

**As of:** 2026-10-31  
**Status:** `L06_06_SYMBOLIC_RACE_MODEL_RND_CANDIDATE`, exact-HEAD CI pending. **NOT an atomic posting guard, authorized COMMIT, SQL lock or proven production linearizability.**  
**Stack:** [L06-05 draft PR #92](https://github.com/tawounfouet/pyaccountingkit/pull/92) @ `b1fc7014afe040b7f34de06f09823a233046cd10` → #91 → #90 → #89 → #88 → `main@acdee98ca2736d79e17174f510ac767defd90db8`. No unmerged L03/L04/L05 runtime/import dependency.  
**Canonical source:** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §9 (four dates), §10 (anti-TOCTOU), §11 (C10-Q04), §12 `CAL-INV-04/05/10`, §13 (SQL constraints), §15 `STALE_PERIOD_STATE`, §16 `CAL-SC-06/07/08/09/15/16`, §17 mandatory concurrent qualification, §20 `ADR-CAL-07/08`, §21 `CAL-L6`. Integration source `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` §6 (delayed notifications not a fence), §8 (final dynamic check). Security source `19` and governance source `17`.

## 1. Exact risk described by the source

The source §10.1 permits the following race **unless** the check and Ledger COMMIT are serialized or fenced by an independently verified authority:

```text
Execution                    Calendar Authority             Ledger
   | GetPeriodStatus -->        |                           |
   | <-- OPEN, revision=17      |                           |
   | plan a journal             |                           |
   |                            | <-- ClosePeriod COMMIT     |
   |                            |     CLOSED, revision=18   |
   | -- (stale) insert ------------------------------------> X
   |       MUST NOT COMMIT under the old observation        |
```

A separate `check()` then `insert()` is unsafe. A delayed `AccountingPeriodClosed` event does **not** prevent an already racing Ledger insert. Merely comparing a candidate checksum cannot prove authoritative current status. Source §10.2 lists implementation alternatives (one DB transaction, shared lock, verified fencing token, coordinated protocol), but **does not select or approve a strategy**. `ADR-CAL-07` and `ADR-CAL-08` remain OPEN.

## 2. What this R&D cut really implements

`src/pyaccountingkit/company_configuration/application/fiscal_fencing_race_model_rnd.py` contains a pure **symbolic abstract state machine**. It reuses only the `UNTRUSTED_CANDIDATE_SIMULATION` L06-05 response, never a live C10-Q04 provider.

```text
SimulatedPeriodStatusResponse (L06-05)
  book scope + candidate version/period
  observed_status / state_revision
  observed locks and unverified completeness
  local checksum, explicitly eligible_for_posting=false
                       |
SymbolicPeriodControl (abstract; user-constructed)
  exact book/period/version, revision, fence_epoch, status
                       |
SymbolicPreflightObservation (unsigned; no lease)
  pinned book/period/version, read_revision, read_epoch,
  source L06-05 response digest
                       |
simulate_symbolic_close_post_race(steps)
  MODEL_CLOSE
       └── symbolic CLOSED; revision+1, epoch+1
  MODEL_POST_ATTEMPT
       ├── mismatched revision/epoch -> MODEL_REJECTED_STALE_STATE
       ├── non-OPEN -> MODEL_REJECTED_NON_OPEN
       ├── incomplete evidence -> MODEL_REJECTED_INCOMPLETE_EVIDENCE
       ├── any observed lock -> MODEL_REJECTED_UNVERIFIED_LOCKS
       └── OPEN/unchanged/no observed locks
              -> MODEL_ORDERED_PRE_CLOSE_ONLY
                 NEVER "POST_ALLOWED", never a write
  MODEL_DELAYED_CLOSE_NOTIFICATION
       └── ignored; not a synchronization primitive
                       |
SymbolicFenceRaceDiagnostic
  source receipt pinned, exact ordered trace, final abstract state
  SHA256, six always-unverified external gates
  posting_authorized=false, journal_entry_created=false,
  sql_committed=false, signed=false
                       |
refuse_symbolic_fence_for_posting()  -> ALWAYS typed exception
```

**A symbolic step is an input label, not a factual event or an SQL result.** The model's `MODEL_ORDERED_PRE_CLOSE_ONLY` means that, *in that supplied total order*, the abstract post attempt precedes the abstract close. It does not mean a physical posting happened or could safely happen. No method returns a token usable as an authorization.

### Canonical R&D design concepts

- **State machine / linearization model:** explicitly ordered artificial events, one abstract control row.
- **Fencing epoch:** a proposed monotonic counter that would invalidate a stale observation **if verified at actual Ledger COMMIT**; no live fencing token is issued.
- **Optimistic concurrency:** candidate revision comparison and simulated advance, not real SQL CAS, lock or isolation guarantee.
- **Fail closed:** mismatched version/period/book/tenant, forged receipt digest, stale revision/epoch, missing/duplicate model operations or contradictory trace rejected.
- **CQRS separation:** L06-05 response remains a read DTO; this modeling function is a test/simulation helper, not the Execution command path.
- **Proof-carrying R&D diagnostic:** deterministic canonical JSON SHA256 with step order preserved, local consistency only; a checksum is **not** a signature or audit record.

## 3. Bounded abstract race scenarios

| Source case | Input ordering | Symbolic expected outcome | Real source acceptance |
|---|---|---|---|
| CAL-SC-09 | `MODEL_CLOSE → MODEL_POST_ATTEMPT` | `MODEL_REJECTED_STALE_STATE` due revision+epoch | **NOT PROVEN** at SQL COMMIT |
| CAL-SC-09 | `MODEL_POST_ATTEMPT → MODEL_CLOSE` | `MODEL_ORDERED_PRE_CLOSE_ONLY` | **NOT an authorized posting** |
| CAL-SC-15 | `MODEL_CLOSE → MODEL_CLOSE → MODEL_POST_ATTEMPT` | First close changes abstract row; second no-op; posting stale | **NOT a real two-writer CAS test** |
| CAL-SC-16 | `MODEL_CLOSE → MODEL_DELAYED_CLOSE_NOTIFICATION → MODEL_POST_ATTEMPT` | Notification does not alter safety outcome | **No actual Outbox/Inbox** |
| CAL-SC-07 | Source observed status already CLOSED | `MODEL_REJECTED_NON_OPEN` | **Not a COMMIT guard** |
| CAL-SC-08 | Observed scoped locks or incomplete inventory | `MODEL_REJECTED_UNVERIFIED_LOCKS` / `MODEL_REJECTED_INCOMPLETE_EVIDENCE` | **No normative lock applicability or complete inventory** |
| CAL-SC-06 | Source observed OPEN / no locks, no close before model attempt | `MODEL_ORDERED_PRE_CLOSE_ONLY` | **No actual accounting eligibility or posting** |

There is no concurrency scheduler, DB transaction, network actor or independent clock. Tests permuting two abstract actions are **not parallel execution**, and must never be cited as source §17 anti-TOCTOU or `CAL-L6` exit proof. A true source `CAL-SC-09` acceptance requires **real two-writer races** against the authorized persistence+Ledger protocol, with COMMIT order recorded and no forbidden journal surviving.

### Six always-unverified production dependencies

1. `SIGNED_ISSUER_ACTOR_AT_COMMIT`
2. `VERIFIED_PUBLISHED_PERIOD_AND_BOOK`
3. `AUTHORITATIVE_LOCK_APPLICABILITY`
4. `ATOMIC_LEDGER_COMMIT_FENCE`
5. `DURABLE_CLOSE_CAS_AND_AUDIT_OUTBOX`
6. `REAL_CONCURRENT_LINEARIZABILITY_PROOF`

The model never sets these gates to true. `refuse_symbolic_fence_for_posting` always raises `UNTRUSTED_PERIOD_STATUS_FOR_POSTING`, including traces containing `MODEL_ORDERED_PRE_CLOSE_ONLY`. It is an **advisory negative contract**, not a security reference monitor all callers must traverse.

## 4. Design of the eventual real protocol (PROPOSED, not chosen)

A qualified candidate implementation would need to choose and document **one** of the source §10.2 strategies, prove the authorization and scope of actors at SQL COMMIT (security blocker #71), and make period close and Ledger journal insertion mutually serialized against the **same authoritative current version**. An example *non-binding design sketch* is:

```text
BEGIN write transaction:
  - verify independently signed actor/issuer/approval and allowed book/journal
  - obtain lock or transactional fence for exact book/calendar_version/period
  - resolve current published period status and applicable locks
  - compare expected control revision and fencing generation with current
  - deny on unavailable/ambiguous/closed/stale, fail closed
  - atomically write allowed Ledger journal + idempotency under guard
COMMIT; cannot let close win between final guard and Ledger write

ClosePeriod BEGIN:
  - verify independent close authority and expected control revision
  - serialize against same fence/lock used for Ledger write
  - advance revision+fence epoch, persist CLOSED and audit+Outbox atomically
COMMIT
```

**This is only a possible same-store outline.** In a two-store architecture, a cross-service `check()` followed by a Ledger `INSERT` is **not** equivalent; a verified cross-store fencing protocol must be specified and tested separately. Publication timing, read snapshots, exact period identities, lock granularity, exception approvals and commit semantics are unresolved source ADRs.

### Mandatory future proving harness (not implemented here)

- Concurrent DB connections with controlled barriers after `GetPeriodStatus`, before lock/fence acquisition, during `ClosePeriod`, and before Ledger COMMIT.
- Both possible commit orders; verify **journal row state and durable close status** after both complete.
- Stale/duplicated fencing token and old ledger transaction after a successful close.
- Two independent close transactions against one `expected_revision`; one succeeds or returns an explicitly qualified idempotent result.
- Scoped locks by book/journal/source/operation; default deny for unavailable status or partial lock evidence.
- Worker kill, transaction rollback, retry, timeout, failover, and delayed Outbox/Inbox events.
- Signed issuer/actor authority and SQL ACL bypass-resistance at **COMMIT**, linked to issue #71; independent security, accounting, legal/IFRS/PCG and architecture approvals.

## 5. What remains absolutely not implemented

`CAL-INV-04/05/10`, `CAL-SC-06/07/08/09/15/16` are **not satisfied as production requirements**. There is no real `GetPeriodStatus` (source `C10-Q04`), published `CalendarVersion`, signed/approved `ClosePeriod`, durable Outbox or AuditRecord, PostgreSQL period state CAS, Ledger writer, COMMIT-atomic fence, or concurrent E2E acceptance. Source `ADR-CAL-07/08` OPEN; all `ADR-CAL-01..10` OPEN. G0/G1/G2 `PENDING_REVIEW`, **G3 `HOLD_SECURITY`** with [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN, G4/G5/G6 `NOT_APPROVED`.

`tests/unit/company_configuration/test_l06_06_fencing_race_model.py` validates abstract ordering, stale epoch+revision refusal, candidate source scope/version/period mismatch, forged tokens, two symbolic close attempts, delayed notifications, immutable trace, checksum and permanent rejection of posting. It does **not** run actual concurrent SQL transactions.

## 6. Next steps

- [x] Source-aligned TOCTOU attack/linearization requirements documented.
- [x] Pure symbolic fence-epoch + revision trace model with fail-closed diagnostics.
- [x] Negative ordering/adversarial tests, deterministic unsigned trace receipt.
- [x] Six production gates permanently UNVERIFIED; no SQL/Journal/writer introduced.
- [ ] Exact-head Python 3.11/3.12 + Ruff, PG foundation/recovery, wheel/sdist 14 SQL hashes.
- [ ] Production close-post fencing, real concurrency suite, gate/security approval — **blocked and not delivered**.

**Next safe R&D cut:** L06-07 multi-book *candidate* isolation, historical replay, qualification inventory and migration parity. Do not confuse source CAL-L7's production E2E exit with these R&D tests. Actual live L06-06 and CAL-L6 remain blocked pending signed IAM authority, ADR decisions and proper Ledger/period persistence.
