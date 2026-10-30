# L03-17 — G3-C02b1 Durable, Tenant-Bound Command Nonces (PostgreSQL)

**Status:** bounded R&D slice of [G3-C02b #59](https://github.com/tawounfouet/pyaccountingkit/issues/59); not independent human IAM or deployed issuer isolation. Depends on signed gateway [PR #58](https://github.com/tawounfouet/pyaccountingkit/pull/58), SQL posture [PR #56](https://github.com/tawounfouet/pyaccountingkit/pull/56), and migrations 0001–0025.

## Confirmed problem

Before G3-C02b1, `DurableNoncePort` was a required protocol but had only a **local, process-memory test double**. Concurrent gateway instances or gateway restarts could not be shown to reject a previously consumed signed `jti`; a signed request could thus be replayed before token expiry even though the application-layer request idempotency prevented duplicate rows in many ordinary cases. An issuer/nonce replay is a distinct security concern from business request idempotency.

## 0026 additive SQL authority and storage

`0026_org_signed_command_nonce_authority.sql`, appended without editing **any** 0001–0025 historical migration, adds:

- `organization_command_nonces`: `tenant_id`, `issuer`, `nonce UUID`, `expires_at`, `consumed_at` and global **`PRIMARY KEY(issuer,nonce)`** across every tenant. No bearer token, human name, database password or signed payload is stored.
- PostgreSQL `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`, tenant-bound owner-managed RLS policy, no PUBLIC table privileges, immediate SQL issuer guard on direct INSERT, immutable UPDATE/DELETE guard. No SQL `TRUNCATE` to untrusted logins.
- An independent owner-managed `organization_nonce_consumers` login→tenant+enabled table. No application, domain issuer, registry, lifecycle or membership SQL login has access to mutate policy or directly INSERT nonces.
- `SECURITY DEFINER` `consume_organization_command_nonce(tenant,issuer,uuid,expiry) -> bool` with pinned `search_path` and **PUBLIC EXECUTE revoked**. It requires original `session_user` to match an enabled owner-managed consumer and `bound_tenant()`, validates the issuer/non-null UUID and PostgreSQL-server-clock expiry (strictly in the future and within 10 minutes), then performs an atomic `INSERT ... ON CONFLICT (issuer,nonce) DO NOTHING`. First committed consumer wins; duplicate returns `false`.
- No automatic deletion/reuse of expired nonces in this slice. A later approved retention operation must delete only expired records *beyond* the chosen replay/audit retention, separately from untrusted app credentials. Availability/capacity monitoring is still to be implemented; unbounded growth is not an approved production retention policy.

## Adapter & gateway contract

`PostgresDurableCommandNonceStore` implements `DurableNoncePort.consume(tenant_id,issuer,nonce,expires_at)` with a **dedicated nonce-only DSN**. `require_tenant_connection()` checks that SQL original-login binding corresponds to the authenticated command's signed tenant before invoking the SQL authority function.

The `OrganizationTrustedIssuerGateway` forwards its **derived typed command tenant**, never a caller-set or SQL-GUC value. The adapter commits its transaction *before returning True* and *before* the DDD service begins its distinct SQL transaction.

**Burn-on-attempt contract:** a command that passes signed verification, live grant and nonce acceptance consumes that JTI permanently, even if its subsequent DDD SQL transaction fails. Clients retry with a **new independently issued signed attestation** and the same business `request_id` and digest; the existing application-layer idempotency receipt prevents duplicate business changes. There is no distributed atomic transaction spanning IAM, nonce storage and DDD SQL; the system must not claim distributed exactly-once.

A PostgreSQL outage, invalid/wrong-tenant connection, disabled consumer or duplicate nonce results in a negative or exception. The gateway catches these and rejects the command **before** business SQL side effects.

## Executable CI coverage

- 2 independent test-only nonce SQL consumer identities (`cc_org_nonce_consumer_a/b`) created by `setup_postgres_ci.py`: one tenant each, `NOINHERIT`, `NOBYPASSRLS`, `NOSUPERUSER`, `NOCREATEROLE`, only SQL controlled command `EXECUTE`, zero direct table INSERT, no SQL role impersonation.
- Durable replay across **new adapter/new PostgreSQL connection**, concurrent identical nonce requests with exactly one winner, global `issuer+jti` uniqueness across tenant-a/tenant-b, and separate issuer namespace.
- Invalid expiry on PostgreSQL server clock, tenant mismatch, revoked issuer binding, ordinary runtime direct EXECUTE denied, `SET ROLE` denied, direct INSERT denied, independent nonce transaction rollback, unavailable PostgreSQL backend fail-closed.
- Previously added signed Ed25519 Company gateway integration now uses the **real PostgreSQL nonce store** rather than the in-memory fake, asserting no consumed JTI after invalid claims and no duplicated business/evidence rows after fresh-attestation request replay.
- Exact-head Python 3.11/3.12, PostgreSQL 16, forward-only migration/recovery, source/wheel/sdist **26 migrations** SHA256 parity. No change to `0001..0025`.

## Explicit production blockers

- The test-only SQL consumer credentials are static fixtures, **not** independently issued, rotated or securely stored production credentials. Distinct SQL login != distinct process/host/secret manager.
- `LiveIssuerAuthorizationPort` still uses an in-memory test double; there is no real external grant revocation or independently authenticated human actor.
- Key custody and trust-anchor rotation for an independent IdP, separately deployed gateway, network/secret isolation, and cryptographically linked external actor provenance/audit remain open.
- SQL nonce retention, capacity alarms, untrusted issuer namespace abuse, regional/global disaster recovery and production threat exercises are not demonstrated. Storing nonces in the same PostgreSQL cluster also couples availability/backup to that cluster; database schema owner can bypass restrictions.
- A failure in the SQL command after a nonce was consumed still burns that nonce. This is intentional: obtain a new signature rather than reusing a spent one.
- **G3-C02b #59 and G3 #36 remain OPEN**. L03 stacked PRs remain unmerged, `main` unchanged and package `0.0.0` placeholder unpublished. No production security certification or stable release claim.
