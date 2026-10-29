# L02-06 - Tenant Login Operational Lifecycle (candidate)

**State:** increment candidate; CI evidence pending; G0, G1 and G2 not signed off.

## Objective

Extend L02-05's `session_user`-based tenant isolation with an **owner-only administrative** proof of tenant-specific PostgreSQL role credential rotation and emergency revocation. This is **not** a production IAM, a secrets manager, a pool manager or a complete provisioning product. The authoritative role-to-tenant mapping remains protected by the schema owner.

## Delivered

- `PostgresTenantRoleOperator.rotate_password()` requires a precisely matched registered login and expected tenant, changes the login password, and drains existing server-side sessions of that login. Previously established application connections must fail and reconnect with the new credential.
- `PostgresTenantRoleOperator.revoke_login()` atomically sets `NOLOGIN` and deletes the authoritative tenant binding; then drains existing sessions. New logins must fail. If session termination cannot be confirmed, an error is returned, never a success receipt. **The account mutation may already be committed**, so operations must investigate and retry the drain rather than assume rollback.
- `TenantConnectionFactory` uses a single tenant credential and verifies the server-owned login-to-tenant binding on each new connection. Its representation redacts the DSN. This is a new-connection factory, **not a connection pool implementation**.
- Role lifecycle input is restricted to registered, unprivileged `cc_runtime_*`, `cc_dispatcher_*` and `cc_inbox_*` login roles, matching an explicit `expected_tenant`. SQL role identifiers are safely quoted and arbitrary admin roles are rejected.
- CI integration tests use disposable SQL login roles and test old-password denial, session invalidation, credential replacement, revocation, wrong-tenant rejection and factory connection isolation.

## Threat model / scope limits

- This proof assumes a trustworthy, separately protected privileged PostgreSQL operator. A superuser, schema owner or role operator with excessive privileges can bypass these protections. A stolen tenant login is still powerful within that tenant; object permissions, action grants and SoD remain application responsibilities.
- SQL `ALTER ROLE ... PASSWORD` requires a password literal. PostgreSQL **statement logging may capture credentials** depending on deployment logging configuration. The application must not log secrets; the production alternative (vault-integrated rotation + protected server logging) requires independent security review.
- A PostgreSQL login may have existing connections before rotation or revocation. This implementation tries to terminate them and verifies observed active connections, but an external connection pool must also be drained/invalidated and its old secret removed. A connection factory is not a pool.
- Role revocation in the database does not automatically revoke an authenticated application session or change any business permission. Production IAM, token/session revocation, ABAC/SoD and denial audit must be qualified separately.
- A real enterprise implementation needs protected role provisioning, durable privileged-action audit, secret rotation, dual authorization, emergency break-glass policy, credential-distribution coordination, observability, on-call alerts, and backup/restore and rolling deployment tests.
- Database-owner-level access and CI test passwords remain outside the domain and application packages. Never run `scripts/setup_postgres_ci.py` in production or reuse its credentials.

## Runbook candidate (manual approval required)

1. Verify *which* tenant, login, application and environment the change targets. Check that the operator is independently authorized and that the corresponding tenant pool is identifiable. Require separation of duties for high-impact changes.
2. Provision a **new credential using the approved secret manager**; transfer only through a protected channel. Do not paste it into shell history, issue descriptions, CI logs or command-line arguments. Ensure PostgreSQL statement logging configuration does not expose password-bearing SQL.
3. Rotate through the isolated administrative service; record the non-secret receipt and audit who approved/executed the change. If draining fails after the mutation commits, treat it as an incident and keep the change unqualified until no old sessions remain.
4. Replace the tenant-specific pool's credential, drain old pool sessions, and reconnect. Validate the bound tenant with a database handshake. Verify an old credential and old live connection cannot be used and other tenants remain unaffected.
5. For emergency revocation, stop issuing application sessions/tokens **in the identity layer**, invoke `NOLOGIN` + binding removal + termination, invalidate pools and investigate privileged access.
6. Produce an independent acceptance report with exact migration version, SHA, role permissions, security review, backup/restore and controlled rollback/recovery evidence.

## Verification matrix

| Case | Required proof |
|---|---|
| Credential rotation | Old password fails; new password works for same bound tenant; existing session terminated |
| Revocation | NOLOGIN; bound mapping removed; existing sessions terminated; new login fails |
| Wrong tenant | Administrative command refuses a mismatched tenant without mutation |
| Scope isolation | Tenant-A connection factory refuses tenant-B claim; separately bound tenant-B login succeeds |
| Unsafe role | Attempts to modify `postgres` or a nonregistered privileged account are rejected |
| Credential hygiene | No passwords in returned receipts, error strings or `repr` of connection factory |

## Gate status

**G0: pending. G1: pending. G2: pending.** Tests support this operational proof only; they do not constitute a production release, signed ADR-CC-08, full IAM/SoD approval, penetration test or backup/restore qualification. Security issue #9 remains open pending independent review.

## Verified CI evidence (implementation SHA)

Exact implementation commit `81a6506444abf6e88c6bb1f4582aca19c9be2502`:
- [PostgreSQL integration #40866069595](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40866069595): **41 tests passed** under Python 3.11 and **41 tests passed** under Python 3.12; Ruff passed.
- [Python CI #40866069487](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40866069487): **99 passed, 5 SQL-only skipped** under Python 3.11/3.12; Ruff passed.
- New L02-06 test module provides **4 PostgreSQL scenarios**. These results demonstrate ephemeral test-database behavior, **not** production credential vault/pool/IAM readiness, independent security acceptance or gate G2 sign-off.
