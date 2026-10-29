# Phase 1 - Implementation status

Date: 2026-10-29

| Gate | Status | Evidence |
|---|---|---|
| G0 - Audit/baseline | PENDING REVIEW | `evidence/L00/repository_baseline.md`; historical repository/package reconciliation still open; issue #1 |
| G1 - Domain kernel | IN PROGRESS | L01 typed VOs, `LegalEntity` aggregate and property tests; issue #2 |
| G2 - Technical foundations | IN PROGRESS / NOT APPROVED | L02-01 memory, L02-02 PostgreSQL, L02-03 Outbox/denial, L02-04 Inbox and L02-05 tenant-role security candidate; issue #5 and security blocker #9 |

## Previously verified exact-SHA checkpoints

- L01 `a4d8d7e572d2d72fde1878b095ba6de4c057c173`: [CI #10](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40838129260), 82 tests and Ruff on Python 3.11/3.12.
- L02-01 `dea2cbd4c1a85ece13df663e6bb47a19cbeb6fc8`: [CI #14](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40839316434), 94 tests and Ruff green.
- L02-02 `fb207bc1570b5efb19a4bf8d34629f430cab26f2`: [PostgreSQL CI #40841545574](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40841545574), 9 DB tests per Python version; Ruff green.
- L02-03 `13c6f7b3af823d9f0a5db38ba1834001f306dc47`: [PostgreSQL CI #40844094545](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40844094545), 17 DB tests per version; [Python CI #40844094557](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40844094557), 99 passed + 2 skipped per version; Ruff green. Documentation head `816dbec99edbc84426f509b7e67436b3a832f0a6` passed two workflows.

## Current candidate

- L02-04: PostgreSQL Inbox, deduplication per producer/event identity, single transaction with an illustrative read-model effect, concurrent replay tests, malicious replay refusal, limited SQL role and **explicit negative evidence that session-tenant spoofing remains unresolved**.
- L02-04 implementation SHA `1599c53a21d5fcf50f46a448c1ed6e0de3c4b18e`: [PostgreSQL CI #40858788493](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40858788493) **28 tests passed per Python version**; [Python CI #40858788521](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40858788521) **99 passed and 3 skipped per version**; Ruff green. This does **not** approve G2 or independent tenant security. See `evidence/L02_increment_04_transactional_inbox.md`.

## Non-claims

G0/G1/G2 are **not signed off**. No stable release, real IAM, independently secure tenant-bound SQL connections, C10 contract E2E, authoritative published configuration governance, standardized norm engine, or Ledger posting. Producer delivery is at-least-once. SQL effects of the demo handler are atomic and idempotent only under the documented trust and database boundaries.

## L02-05 - Tenant role hardening (CI qualified candidate, G2 still pending)

- **Implementation** `80c394572beeecde25cc5339af976da84706a038` passed [PostgreSQL CI #40863980633](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40863980633) (**37 passed per Python 3.11/3.12**) and [Python CI #40863980690](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40863980690) (**99 passed, 4 skipped per version**), Ruff green.
- Enforces schema-owner-controlled login-to-tenant binding with `session_user`; client-set GUCs do not change RLS scope. All 8 Company Configuration tenant-scoped SQL tables converted in migration 0004; adapters fail before touching data on mismatched DB credentials.
- 9 adversarial tests cover direct GUC spoof, cross-tenant inserts, missing binding, SET ROLE/SESSION AUTHORIZATION, protected registry, search_path and session reuse, DB role mismatches for UoW/Outbox/Inbox.
- **Security P0 #9 remains open for independent review**, operational secret rotation/pooling, actor/SoD policy and privileged role review; G0/G1/G2 not signed off. No production-ready release.

## L02-06 - Credential rotation/revocation operational candidate (IN PROGRESS)

- New owner-only `PostgresTenantRoleOperator` and tenant-checked fresh connection factory; disposable-role integration tests for rotation, NOLOGIN revocation, terminated sessions, wrong-tenant and unsafe-target denial.
- Candidate ops runbook and ADR-CC-08A for segregated tenant pools, credentials, SQL privileged operator and incident response.
- **No G2 sign-off:** real secret vault, production pool driver, IAM/SoD, audit of privileged changes, live restoration and architecture review still pending.
- Implementation `81a6506444abf6e88c6bb1f4582aca19c9be2502` passed [PostgreSQL CI #40866069595](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40866069595) (**41 passed per Python 3.11/3.12**, Ruff), and [Python CI #40866069487](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40866069487) (**99 passed, 5 skipped per version**, Ruff). **No G2 sign-off.**

## L02-07a - Tenant-scoped Secret Provider and physical pool boundary

- Candidate implementation SHA `8a286b757aacba81511bc5b11876060c02b54d6d`: [PostgreSQL CI #40871381836](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40871381836), **46 passed** per Python version, Ruff; [Python CI #40871381720](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40871381720), **108 passed, 6 skipped** per version, Ruff.
- `TenantSecretProvider` protocol, versioned/secret-redacted credentials and a distinct physical `psycopg_pool` per tenant+role kind; trusted secret lookup and database identity validation before checkout; fail-closed upon secret outage, drift or epoch regression.
- Candidate [ADR](evidence/L02_07_ARCHITECTURE_DECISION_CANDIDATE.md) unapproved. Not implemented: real vault, production IAM/SoD and audit, integration into application UoW/outbox/inbox construction, bounded production connection budgets, TLS/restore/failover. No G0/G1/G2 sign-off, no release.

## L02-07b - Privileged IAM/SoD port and append-only audit (candidate)

- Implementation `e2414cca16b8c175abba70de5820962a7c4e418b`: [PostgreSQL CI #40874962870](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40874962870) **53 passed** per Python version (3.11/3.12), Ruff green; [Python CI #40874963079](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40874963079) **125 passed, 7 skipped** per version, Ruff green.
- Ports for verified operator identity, exact operation approval, current permission check, strict effective-ID SoD; separate append-only denied/intended/outcome evidence. Migration 0005 protects owner-only privileged audit; no secret stored.
- **Not implemented:** external IdP/policy/approval provider, atomic role-DDL/outcome audit, in-flight approval revocation fencing, privileged control-plane deployment isolation, reconciliation of incomplete intents, production vault/IAM, operational SoD attestation or G0/G1/G2 sign-off. Draft PR #13, issue #5.
