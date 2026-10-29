# L02-05 - PostgreSQL tenant-bound login security proof

**Status**: candidate implementation; no G0/G1/G2 sign-off. Invariant SEC-03 (tenant isolation) has a narrowed SQL proof, not a full enterprise authorization proof.

## Motivation and threat model

Prior policies used `current_setting('app.tenant_id')` as the RLS tenant authority. A holder of a shared, unprivileged database login could call `set_config()` to read another tenant's rows. FORCE RLS by itself did not prevent this. Issue #9 is an explicit P0 security blocker.

The proposed security boundary binds a dedicated PostgreSQL **login role** to **exactly one tenant** in a schema-owner-managed lookup table. RLS derives its tenant exclusively from the authenticated `session_user`, resolved by a `SECURITY DEFINER` function with fixed search_path. App-provided tenant parameters and session custom GUCs are not security authorities. All eight existing scoped tables have their RLS policies replaced atomically by migration `0004`.

`SET ROLE` does not change `session_user`; login roles are deliberately not granted membership in other tenant roles. The runtime/dispatcher/inbox roles hold only the operations required by their respective responsibilities. The DB owner administers bindings; runtime roles cannot inspect or mutate the binding table. Any unregistered login resolves to NULL and is denied access to scoped rows.

The Python adapters (`PostgresUnitOfWork`, `PostgresOutboxDispatcher`, `PostgresInboxConsumer`, `PostgresDenialAudit`) fail early with a typed `TenantConnectionMismatch` if the requested tenant does not equal the authenticated database binding. Independently, RLS enforces that same binding on raw SQL, even if the adapter is bypassed.

## Scope and limitations

This is a **role-per-tenant** proof. Credentials are disposable fixtures in `setup_postgres_ci.py`; **never** deploy the CI passwords or script. Production role provisioning, secret rotation, pooling segmentation, authorization decisions, revocation, monitoring and emergency access are still design and operational work.

The database administrator / superuser / schema-owner and tenant role provisioning automation are **trusted**. A compromised admin, stolen tenant-specific credentials, cross-tenant credential sharing, privilege escalation outside PostgreSQL, or a broken authentication gateway remain separate concerns. RLS controls tenant only; **company, entity, accounting book, SoD and action-level authorization remain the responsibility of the application policy layer** (see Security Model 19). No claim is made about C10 production integrations, WORM, releases or Ledger posting.

## Negative proof matrix (real PostgreSQL 16)

- Caller sets `app.tenant_id` to another tenant: **must not** change rows visible through RLS.
- Caller attempts cross-tenant INSERT with spoofed GUC: rejected by RLS WITH CHECK.
- Unregistered login with broad read permission but no binding: sees no rows (fail closed).
- Tenant login attempts `SET ROLE` or `SET SESSION AUTHORIZATION` into another tenant login: denied.
- Application role reads or modifies the protected login-to-tenant binding registry: denied.
- `search_path` changes, transaction boundaries and connection reuse: cannot alter the login-derived binding.
- User passes a mismatched requested tenant to runtime/inbox/dispatcher adapter: rejected before database operations.
- Dispatcher and Inbox role cannot read forbidden producer audit records.
- CI includes all previous create/read/rename, lease/retry/outbox and dedup Inbox regression tests.

## Qualification

To verify, use the dedicated PostgreSQL GitHub Actions workflow (Python 3.11 and 3.12) with the role-setup script executed as the schema owner after applying migrations. The `0001` through `0003` migration files remain immutable and checksum-stable. Record **exact commit SHA and job URLs only after CI is green**.

## Open decisions before G2

1. Approve ADR-CC-03/05/08 including role-per-tenant choice and scoped connection pool/credential lifetime.
2. Demonstrate production provisioning/revocation and no cross-tenant secret sharing; verify IAM integration, actor-level policy, SoD, denial audit.
3. Model security-review adversarial cases for privileged functions, owner bypass, role membership, pool reuse and operational recovery; perform independent review.
4. Reconcile historical repository provenance and obtain prior G0/G1 approvals.

G2 and issue #9 are **not automatically closed by green CI**.
