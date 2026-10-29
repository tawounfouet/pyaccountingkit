# L02-07g - Least-privilege PostgreSQL delegated control plane

**Status: technical candidate, not security/deployment acceptance.** L02-07f qualified the *normal application service* path through a mandatory SQL fence, but it still required a PostgreSQL owner DSN to execute privileged DDL. This increment removes that need **from the delegated fencing adapter**, not from all administrative processes.

## Boundary

- The separately provisioned `cc_control_plane` **LOGIN** has `NOSUPERUSER NOCREATEROLE NOCREATEDB NOINHERIT NOREPLICATION NOBYPASSRLS` and no direct grants on tenant bindings, fence tables or audit rows.
- Migration `0009` installs three narrow `SECURITY DEFINER` functions, each with explicit fixed `search_path`, revoked PUBLIC EXECUTE, strict target role name allowlist, tenant mapping, actor/approval and fence-state constraints, and target `pg_roles` privilege checks. Only the trusted provisioner grants EXECUTE to `cc_control_plane`.
- `DelegatedPrivilegedControlPlane` implements the application fenced execution contract using **only** that limited SQL credential. It calls `cp_issue_fence`, `cp_revoke_fence` and `cp_execute_fence` rather than importing the unrestricted role operator or opening a schema-owner DSN. The owner controls the SQL routine definitions, grants and migration.
- `cp_execute_fence` locks the fence row, verifies its scope, updates the PostgreSQL login, records CONSUMED and attempts to terminate target sessions in one SQL transaction. A failure aborts the transaction. Remote clients can still observe session termination even on SQL rollback; this is not a cross-system atomicity guarantee.
- Runtime, dispatcher, Inbox and even the control-plane login cannot directly `ALTER ROLE`, query the fence ledger or query the tenant role binding table.

## Verification

Run the same migration/CI role setup as L02, with the new `CC_PG_CONTROL_PLANE_DSN` **test-only** credential. Integration tests prove: denied direct DDL, denied table access, function permission errors for runtime, exact-scoped issuance and consumption, replay refusal, wrong tenant/actor/approval, local revocation, and tenant binding removal on NOLOGIN.

Record exact GitHub Actions SHA and runs after observed success. Preserve checksums 0001-0008; migration 0009 is additive.

## Residual G2 security gaps

- **Owner bypass still exists:** DB superusers/schema owner and the legacy `PostgresTenantRoleOperator(admin_dsn)` remain available to privileged infrastructure. This increment does not delete that Python class or make it uncallable for an admin, and an owner can redefine the security-definer function. Production must restrict owner credentials, migrations, extension ownership and privileged deployment/network access separately.
- This is an **in-database capability grant**, not real cloud network segmentation, mTLS, a service mesh, Vault or a production-isolated control-plane process. A compromised `cc_control_plane` can call all three functions with **claimed** operator and checker identifiers and allowed target logins. It has broad delegated power within that allowlist until a real IAM/PAM boundary enforces each request.
- `PrivilegedRoleService` still uses a separately owner-configured `PostgresPrivilegedAudit` in test composition; the audit/incident owner DSN separation is unresolved. A production composition must use a restricted audit write capability and independent append-only evidence review.
- SQL role password is still present as a PostgreSQL statement parameter and inside dynamic SQL; protect database logging and telemetry, use a secret vault, enforce TLS, and do not log credentials.
- SQL-local revocation does not atomically fence remote IAM changes; no external IAM approval signatures, revocation propagation ACK, immutable WORM attestation, cross-service transactional audit or formal G0/G1/G2 signoffs.

**No claim of full tenant isolation in a deployed production system, no stable release, no ledger posting.**
