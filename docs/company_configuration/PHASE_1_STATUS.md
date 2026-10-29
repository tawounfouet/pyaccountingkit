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

## L02-07i - Pinned signed IAM evidence and hardened startup settings (CI PENDING)

- New optional `iam` dependency uses `cryptography` for pinned-key **Ed25519/EdDSA compact JWS** signatures, separate trusted operator/approval issuers, exact issuer/audience/kid/claims/time checks, no key URL fetch, algorithm confusion or client-side approval claims. Approval source is a separate trusted port, not a live external IAM.
- `SignedControlPlaneSettings.from_environment()` requires distinct dedicated SQL credentials, no inherited owner or runtime DB credentials, explicit remote PostgreSQL TLS `sslmode=verify-full` and distinct public-key trust material. It is a startup configuration guard, not a deployed process/network isolation.
- `build_signed_restricted_privileged_service()` integrates verified signed identities and approvals with L02-07h's restricted audit and delegated SQL fence, plus live current-grant policy port.
- Pure tests cover tamper, expiry, bad algorithms and broken settings. PostgreSQL integration uses CI-generated Ed25519 keys and a local **trusted fake approval store** for an end-to-end restricted SQL role action, plus forged signature and wrong approval scope denials.
- No production IdP/approval provider, anti-replay store/mTLS binding, external revocation ACK, actual isolated workload, WORM evidence, G0/G1/G2 acceptance or release. This remains a draft candidate.
- **Implementation SHA `2b6aafe1ef8bf5fc5599502b900531c9920e8c6b`**: [PostgreSQL CI #40922185351](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40922185351) **101 passed per Python 3.11/3.12**, Ruff green; [Python CI #40922185433](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40922185433) **206 passed and 13 PostgreSQL-only skipped per version**, Ruff green. Approval signing keys and evidence source are ephemeral CI fixtures. **No real IdP, external IAM approval contract, workload isolation or G0/G1/G2 approval.**

## L02-07j - Signed IAM revocation receipts (CI PENDING)

- The optional signed-evidence verifier now accepts a distinct pinned Ed25519 `kind=revocation` key and exact revocation claims. The SQL-first `SignedIamRevocationProcessor` reads evidence from a trusted independent source and only calls its remote acknowledge callback after a durable PostgreSQL commit.
- Migration `0011` adds an owner-only immutable request-revocation journal and BEFORE INSERT fence tombstone guard; issuance and SQL acknowledgment serialize by request advisory lock. For ACTIVE fences, the receipt and local REVOKED state commit atomically. A consumed fence is explicitly `ALREADY_CONSUMED`, never claimed prevented.
- CI-only `cc_iam_revocation` has just EXECUTE on `cp_ack_iam_revocation`, no DDL, audit or fence table privileges. Negative/unit and PostgreSQL race tests included. No actual external IAM connector, remote delivery/ACK scheduling, mTLS workload isolation or production IAM guarantees. G0/G1/G2 remain unsigned.

### L02-07j - Signed IAM event receipt (exact-SHA CI-qualified candidate)

- Implementation `cfe46cacd0f5b0190b554e5c7eede75941f47175`: [PostgreSQL CI #40926615545](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40926615545), **109 passed per Python 3.11/3.12**, Ruff; [Python CI #40926615439](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40926615439), **224 passed, 14 skipped** per Python version, Ruff.
- Migration `0011` protects fence issuance against earlier signed revocation receipt, uses transaction-level advisory locking and permanent tombstones. Separate restricted SQL IAM capability, exact signed scope/TTL, receipt and ACK/retry tested.
- **Still blocked:** real provider source/remote ACK queue, JWS key lifecycle, SQL receiver secret compromise, external IAM-to-SQL latency, physical workload/network isolation, incident response for `ALREADY_CONSUMED`, owner bypass, vault/mTLS/WORM/audit and independently accepted ADR/G0/G1/G2. PR #22 remains draft/unmerged.

## L02-07k - HTTPS Provider Contract + Durable ACK Outbox (CI PENDING)

- HTTPS revocation source uses pinned provider origin, CA/hostname verification, no redirects, bounded JWS, explicit bearer credential and event-UUID idempotency key. Transport is faked in CI; this is not an installed vendor connector or production source.
- SignedIamRevocationProcessor.ingest() verifies and commits locally **without immediate remote ACK**; legacy process() continues to ACK for compatibility but should not be used in the durable pipeline.
- Migration 0012 stages every SQL IAM revocation receipt in a **same-transaction ACK outbox**, including backfill for earlier receipts. Separate nonprivileged `cc_iam_delivery` can claim/complete/fail via owner-managed functions with SKIP LOCKED, 30-second leases, bounded retry/backoff and DEAD status.
- `IamAckDeliveryWorker` performs at-least-once ACK with upstream Idempotency-Key. Failure to confirm SQL completion leaves a lease for a safe duplicate retry.
- Tests cover provider transport violations, failed ACK, transactional rollback, stale lease, competing claims, 5-attempt DEAD and SQL capability denial. Production scheduling, metrics, real IAM provider, verified upstream dedup, DLQ incident handling, network isolation, G0/G1/G2 remain open.

### L02-07k - HTTPS IAM Source + Durable ACK Outbox (exact-SHA CI qualified, G2 pending)

- Implementation `e336cdb92d57229d5f4bd181214075e8b5c7d20e`: [PostgreSQL CI #40930190602](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40930190602) **116 passed per Python version (3.11/3.12)** and Ruff; [Python CI #40930190535](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40930190535) **240 passed, 15 PostgreSQL-only skipped per version** and Ruff.
- New HTTPS revocation GET/ack POST adapter with event-key idempotency; `SignedIamRevocationProcessor.ingest()` verifies/persists without immediate remote ACK (legacy `process()` still sends immediate ACK for compatibility).
- Forward-only migration 0012 ensures a revocation receipt and queued ACK commit together. Dedicated `cc_iam_delivery` has no DDL or raw table grants. Worker uses `SKIP LOCKED`, lease tokens, capped retries and DEAD state; concurrent claims test qualified on real PostgreSQL 16.
- **Open G2 blockers:** no connected IAM provider or demonstrated provider-side idempotency, no running worker/scheduler/alerting or independently approved DLQ handling, no workload network isolation/secret vault/mTLS/owner bypass closure, no externally signed independent audit, no G0/G1/G2 or ADR-CC-08K sign-off. PR #23 draft/unmerged.

## L02-07l - IAM ACK operational telemetry and manual DEAD-letter re-drive (CI pending)

- Forward-only migration `0013` introduces aggregate-only SQL metrics for `cc_iam_delivery`, a separate nonprivileged `cc_iam_recovery` login with scoped DEAD inspection and re-drive function EXECUTE only. Redrive history uses an immutable append-only table and a maximum of **two** independently approved re-drives per event.
- `IamAckRecoveryService` requires a verified tenant-specific actor, current permission, independently verified exact event/request approval with TTL, distinct approver identity and a final policy/approval recheck. It relies on trusted port adapters, not actual live IAM integration.
- `IamAckOperationsRunner.tick()` runs a bounded delivery batch and emits aggregate alert flags. The foreground `delivery_runner` CLI supports --once and bounded polling for an **external** process supervisor; no service deployment or alerting platform is claimed.
- Unit and PostgreSQL integration tests include denied tenant/SoD/replay, append-only decisions, cap-two redrives, independent role privileges and concurrent re-drive. Exact-SHA CI proof pending.
- Remaining G2 blockers: no real signed re-drive approval adapter, actual supervisor/alert channels, controlled production deployment or mTLS, operator audit custody, external IAM provider / dead-letter runbook approval, owner-secret bypass closure or signed G0/G1/G2.

### L02-07l - Supervised IAM delivery and approved DLQ re-drive (exact-SHA CI green, G2 pending)

- Implementation `5097d3c6c7c67a655dcb6e19522b9aee27f76137`: [PostgreSQL CI #40935848609](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40935848609) **122 passed per Python 3.11/3.12**, Ruff; [Python CI #40935848623](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40935848623) **257 passed, 16 SQL-only skipped per version**, Ruff green.
- Migration `0013` adds no-PII aggregate metrics and separate scoped `cc_iam_recovery` capability. Manual DEAD re-drive needs independent exact-scope approval at the application port, append-only SQL decision and a transactionally atomic reset; max two re-drives per event, replay/tenant/collision guarded.
- Delivery CLI provides bounded foreground polling and aggregate JSON alert flags for an external scheduler; **not** actual deployed monitoring or automated DLQ closure.
- **Open G2:** real signed approval adapter/IdP, independently protected recovery SQL secret, production supervisor and alert sink, incident resolution/approval, provider idempotency and mTLS, owner-DSN bypass, vault/WORM/DR, signed ADR and G0/G1/G2. PR #24 remains draft/unmerged.

## L02-07m - Pinned signed recovery approvals and guarded composition (CI PENDING)

- A new `recovery_approval` Ed25519 JWS kind binds approval reference, event/request UUIDs, tenant, exact incident evidence, reason and independent checker, separate from the operator identity signer. The signing verifier reads trusted independent evidence and validates strict expiry; service double-checks current authorization before SQL.
- `SignedRecoverySettings.from_environment()` refuses owner/runtime/delivery/control-plane credentials and requires pinned separate issuer/key roots plus a dedicated remote `cc_iam_recovery` PostgreSQL TLS `verify-full` URI. Composition checks actual SQL session_user, restricted grants and lack of raw outbox access.
- New pure tests verify forged/wrong-scope/expired/revoked cases and unsafe deployment settings; real PostgreSQL tests prove valid signed evidence and denial before SQL mutation. Previous migration 0013 stays unchanged.
- **Not a real independent IAM approval service, deployed isolation or security sign-off.** Source and signers in tests are ephemeral fixtures. G0/G1/G2 remain unsigned and PR stays draft/unmerged. Exact-SHA CI evidence pending.
