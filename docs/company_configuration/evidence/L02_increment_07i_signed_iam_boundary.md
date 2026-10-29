# L02-07i - Pinned signed IAM evidence and hardened control-plane configuration

**Status:** candidate implementation, not production IAM integration or approved G2.

## Goal and explicit scope

L02-07h restricted the privileged audit and fence SQL credentials. The external-identity ports remained abstract, so arbitrary Python stubs could return `VerifiedOperator` and `VerifiedApproval` without cryptographic proof. This increment introduces *optional* Ed25519 compact-JWS **verification adapters** and a strict candidate startup-configuration guard. It does **not** connect to an independent live IdP, retrieve a remote approval, install a network boundary or guarantee revocation freshness.

## Implemented application adapters

- `SignedOperatorIdentity` verifies a compact JWS signed with a **pinned operator public key**. It enforces the exact `EdDSA` protected header, trusted `kid`, `iss`, `aud`, `kind=operator`, `sub`, `tenant_id`, integer `iat/nbf/exp`, a UUID `jti`, bounded maximum lifetime, active time window and canonical encoding. Only after verification is `VerifiedOperator` constructed.
- `SignedApprovalVerifier` obtains the signed approval from `TrustedApprovalEvidenceSource.read(reference)`. It does not accept client-supplied approval claims as facts. The **separate approval signing root** verifies `kind=approval`, exact approval reference, subject/checker, target request UUID, tenant, login role, operation and times. Only after verification is `VerifiedApproval` constructed.
- `PinnedSignedEvidenceVerifier` rejects `alg=none`, HMAC/algorithm substitution, untrusted or embedded keys, malformed/duplicated JSON claims, unknown fields, payload tampering, expired/future assertions, wrong audience/issuer and mismatched evidence kind. It never retrieves or trusts a `jwk`, `jku` or `x5u` from an incoming token.
- The application service **still performs** SoD, exact approval matching, current-grant policy checks before and after INTENT, a mandatory PostgreSQL fence and an independent audit. A valid signature is not itself an authorization grant.

## Startup boundary

- `SignedControlPlaneSettings.from_environment(explicit_env)` accepts *only* dedicated `cc_control_plane` and `cc_privileged_audit` SQL credentials; it rejects any inherited `CC_PG_ADMIN_DSN`, common runtime DB credentials, generic `DATABASE_URL` or `PGPASSWORD`.
- Each SQL connection URI must name the correct restricted login, a remote database, an explicit database name and `sslmode=verify-full`, without arbitrary PostgreSQL `options`/session overrides. The settings object redacts DSNs from its representation.
- Separate pinned Ed25519 public-key material, `kid` and `iss` for operators and approvers are required. `build_signed_restricted_privileged_service` composes the verified adapters with the existing L02-07h restricted SQL composer.

## CI acceptance evidence

- Pure unit tests: valid signed operator and independently signed approval, forgery, algorithm confusion, bad `kid`, duplicate signed JSON claims, wrong tenant/audience/issuer, not-yet-active/expired token, wrong request ID, offline approval store and fail-closed startup settings.
- PostgreSQL integration: short-lived CI-created Ed25519 operator/approval tokens with independent signing keys, trusted fake approval source and live `PrivilegedRoleService` -> restricted SQL audit -> delegated SQL role DDL -> CONSUMED fence. Negative cases reject forged operator signatures and wrong signed approval request ID before DDL.
- This test source is a **CI fixture**, not an external production IAM or connected approval provider. Neither production network isolation nor credential vault/mTLS are proven by a passing CI workflow.

## Explicit open threats

1. A stolen valid operator bearer assertion can be replayed within its short expiry. The UUID `jti` validates format, but no persistent anti-replay store or token binding to mTLS is implemented. Exact command request idempotency is separate.
2. Key rotation and revocation are deployment-controlled pinned-key changes. No JWKS discovery, signed policy change event, remote revocation push/ACK or lease fencing is implemented. The existing policy port must still check live authoritative grants; a cryptographic signature cannot prove current permissions.
3. `TrustedApprovalEvidenceSource` is an interface. Production must use a separate controlled approval store or API with audited access and independent SoD. Insecure sources that simply echo client JWTs are prohibited by contract, not magically blocked by Python type checks.
4. The startup guard is static and reject-by-convention. Python code can instantiate settings directly or hold additional credentials outside the checked mapping; actual workload isolation needs a separate service identity, secret vault, network policy, mTLS and assurance of the runtime/container environment.
5. Schema owner, database superuser, `PostgresTenantRoleOperator(admin_dsn)` and an independently compromised delegated SQL credential remain privileged bypass risks. SQL audit is append-only relative to unprivileged roles, not independent WORM or signed evidence.
6. The SQL role DDL and CONSUMED fence are locally atomic, but session drain, separate terminal audit and remote IAM revocation are not a global atomic operation. Incident investigation and restoration remain pending.

**G0/G1/G2 remain NOT APPROVED. No stable release.** Add exact-SHA test evidence only after observing the GitHub workflows.
