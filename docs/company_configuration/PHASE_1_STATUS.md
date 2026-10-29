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

## L02-07c - Privileged reconciliation and late approval checks (candidate)

- Privileged role action policy and approval verified **again after durable INTENT and immediately before DDL**; changed/expired/revoked state cancels the action and appends terminal `CANCELLED` without mutation.
- Migration `0006_privileged_reconciliation.sql`: append-only owner-only `privileged_reconciliation_reviews` with `OUTCOME_MISSING` and explicitly `UNKNOWN` DDL outcome; no automatic inference or replay.
- Tenant-scoped `PrivilegedReconciliationService` requires verified reviewer identity and independent current review grant. PostgreSQL repository uses bounded age cutoff, `FOR UPDATE SKIP LOCKED`, and unique per-request review evidence.
- Unit tests: 28 passed locally for old+new privileged services (Python 3.13). Implementation `23cdb621363ac9876b5e46f911a8199e78b4a599`: [PostgreSQL CI #40879514472](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40879514472) **63 passed per Python 3.11/3.12**, Ruff green; [Python CI #40879514299](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40879514299) **136 passed and 8 skipped per version**, Ruff green. This is not G2 or security approval.
- **Not G2**: no external IdP/approval, no IAM fencing across DDL, no incident closure/replay, no admin DSN isolation, no signed ADR, no G0/G1/G2 sign-off.

## L02-07d - Privileged Incident Control Plane (IN PROGRESS / NO G2)

- Append-only owner-only incident decision records and independent denied-decision stream, SQL migration `0007` (prior checksum-preserving migrations untouched).
- Trusted AuthN and current-grant/independent approval **ports**, with four distinct effective actors (original SQL actor, orphan reviewer, incident investigator and checker).
- A decision may be only `ESCALATED`, `REMEDIATION_REQUIRED` or `INVESTIGATION_DOCUMENTED`. Historical DDL result always remains **UNKNOWN**, with no role mutation, credential rotation or automated replay.
- SQL row locking, unique review decision, late-terminal exclusion, tenant boundary checks and append-only audit tests. Local unit slice: 28 passed. CI PostgreSQL evidence pending exact SHA.
- Implementation `8cf191cdefba3fb17c79f828f271ebd95cb6817b`: [PostgreSQL CI #40886773797](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40886773797) **73 passed per Python version** and Ruff; [Python CI #40886773793](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40886773793) **153 passed, 9 skipped per version**, Ruff. Pending real IAM/IdP, protected control-plane deployment, leased permission fencing, evidence signature and retention, independent security review and G0/G1/G2 approval. This is a code candidate only.

## L02-07e - PostgreSQL-local authorization fencing (technical CI proof)

- Implementation SHA `e37ebddcf836416d18dedcc97623010772bfaa30`: [PostgreSQL CI #40911217987](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40911217987) **81 passed per Python 3.11 and 3.12** with Ruff green; [Python CI #40911218005](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40911218005) **166 passed, 10 SQL-only skipped per Python version** and Ruff green.
- Migration 0008 adds per-request owner-only ACTIVE/REVOKED/CONSUMED fences and append-only evidence; row lock serializes SQL-side revocation against role DDL and shares one commit with its CONSUMED evidence.
- **Not full IAM fencing**: a remote IAM revocation must be propagated to PostgreSQL; real IdP, production control-plane admin DSN isolation, connection drain, credential log policy, and integration into all existing privileged role use cases remain pending.
- Exact-scope issue port, SQL owner-role denial and transaction rollback on evidence failure tested. All G0/G1/G2 and ADR-CC-08E approvals remain unsigned. Draft PR #16, no release.

## L02-07f - Mandatory fenced privileged service (CI PENDING)

- `PrivilegedRoleService` no longer accepts a direct `roles` operator. Its required `fence` port ties verified actor, tenant, request, operation and approval to the PostgreSQL SQL-local fence, issued after the second current grant/approval check.
- Previous and new unit / PostgreSQL tests updated to use fenced composition; additional proof for legacy composition denial, issue failure and end-to-end consumed evidence.
- **Not production-qualified:** owner-DSN direct infrastructure bypass, remote IAM revocation propagation, operator/approval provider, control plane deployment, post-DDL drain and outcome audit, G0/G1/G2 and ADR remain open.
- **Implementation SHA** `f832e523869df5373637d921900f0a0bcf04e945`: [PostgreSQL CI #40913070187](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40913070187), **81 passed per Python version**, Ruff green; [Python CI #40913070382](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40913070382), **169 passed, 10 skipped per version**, Ruff green. **No G0/G1/G2 sign-off or production qualification.**

## L02-07g - Narrow delegated SQL privilege boundary (candidate)

- PostgreSQL migration `0009_delegated_control_plane.sql` installs owner-controlled SECURITY DEFINER issue/revoke/execute routines with explicit search_path and PUBLIC grants revoked.
- CI-only `cc_control_plane` LOGIN has **no CREATEROLE, SUPERUSER or private-table privileges**, only EXECUTE on three narrowly constrained routines. Normal runtime/dispatcher/Inbox roles cannot call them.
- `DelegatedPrivilegedControlPlane` implements the fenced execution port without needing a schema-owner/admin DSN. Owner-only migrations, privileged audit and existing legacy raw role operator are **not** eliminated.
- Automated PostgreSQL adversarial qualification is required before candidate acceptance. Production network segregation, signed IAM/SoD approvals, secret vault/logs, independent audit owner and G0/G1/G2 remain unapproved.

### L02-07g - Delegated control-plane proof (exact-SHA CI qualified, G2 open)
- Commit `7a4e644069848a3a59fa560505bf8927af7e389e`: [PG CI #40915755895](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40915755895), **90 passed per Python version** (3.11/3.12), Ruff green; [Python CI #40915756033](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40915756033), **169 passed, 11 SQL-only skipped per version**, Ruff green.
- SQL migration `0009` adds owner-controlled SECURITY DEFINER issue/revoke/execute functions. `cc_control_plane` in CI has neither SUPERUSER/CREATEROLE nor direct table access, only EXECUTE grants; runtime and other roles cannot invoke them.
- `DelegatedPrivilegedControlPlane` implements required fenced operations **without a schema-owner DSN**, tested from `PrivilegedRoleService` through role DDL, CONSUMED evidence and existing owner-only audit (owner audit path still a blocker).
- **Still not G2**: deploy isolated privilege and migration process, protect owner and legacy operator, external IAM/SoD and revocation acknowledgment, independent audit writer, vault/TLS/SQL logging, restore and penetration review, approved G0/G1/ADR. PR #18 is draft and unmerged.

## L02-07h - Restricted privileged audit writer (CI PENDING)

- New migration 0010 adds a narrow owner-managed SECURITY DEFINER append endpoint, restricting privileged audit writer to an independent `cc_privileged_audit` database LOGIN. PUBLIC grants revoked; runtime, dispatcher, Inbox and the DDL control-plane role are not granted audit EXECUTE.
- `DelegatedPrivilegedAudit` writes durable INTENT, DENIED, and terminal phases without owner credentials. Server derives approver for outcomes from INTENT and rejects SUCCEEDED without an exact CONSUMED fence.
- `build_restricted_privileged_service()` validates the *two distinct, nonprivileged* SQL session identities and role privileges; rejects owner/runtime and swapped credentials.
- Real PostgreSQL CI test fixture and adversarial scenarios are provided, including integrated service execution with restricted audit and control-plane DSNs; exact GitHub Actions qualification remains pending.
- **Not deployment qualification**: separate SQL roles are not separately deployed services, no external signed IAM approval or WORM audit, privileged owner/raw operator still available, no G0/G1/G2 approvals or stable release.

### L02-07h - Dedicated privileged audit (exact-SHA CI-qualified candidate)

- Implementation `3025731bdacb2b833291930141ce7322fd9eb7fa`: [PG CI #40918911563](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40918911563), **98 passed per Python version (3.11/3.12)** and Ruff; [Python CI #40918911446](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40918911446), **169 passed, 12 skipped** per version, Ruff.
- Migration 0010: restricted audit-only SQL `SECURITY DEFINER` endpoint, server-side phase consistency and original approver attribution; **SUCCEEDED** requires matching **CONSUMED** fence. Previous migrations remain checksum-verified and untouched.
- Independent `cc_privileged_audit` LOGIN has no access to audit tables or role DDL; `cc_control_plane` cannot invoke audit writes; runtime/Inbox/dispatcher have neither capability.
- `build_restricted_privileged_service` refuses admin, runtime and switched DSNs; integrated PrivilegedRoleService execution uses only `cc_privileged_audit` and `cc_control_plane` DSNs, with owner credentials needed solely for migrations and CI evidence inspection.
- **Still G2 BLOCKED:** schema owner/legacy operator, no real external IAM/SoD/approval signature, no physically segregated deployment/network, no externally attestable audit, vault/TLS/SQL statement logs and post-DDL recovery unqualified. ADR-CC-08H proposed only. PR #19 stays draft/unmerged.
