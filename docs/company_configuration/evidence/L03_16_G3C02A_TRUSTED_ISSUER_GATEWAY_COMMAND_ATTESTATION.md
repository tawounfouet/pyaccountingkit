# L03-16 — G3-C02a Trusted Organization Issuer Gateway and Command Attestation

**Status:** bounded R&D implementation, *not* a proof of production IAM, separated process credentials or full G3 sign-off. Tracks [issue #57](https://github.com/tawounfouet/pyaccountingkit/issues/57), depends on qualified [G3-C01 PR #56](https://github.com/tawounfouet/pyaccountingkit/pull/56), after ORG-5b3b→5b3c3 SQL issuer authority (migrations 0022–0025).

## Decision — use a gateway, not a caller-constructed TrustedPrincipal

Define a **separate trust and deployment boundary**, not another SQL client function:

```text
Ordinary API worker  (no SQL issuer DSNs / signing private keys)
          |
          | typed command + externally IAM-issued signed attestation
          v
Isolated trusted issuer gateway (verify pinned Ed25519 + live IAM grants)
          |
          | consume one-use JTI via atomic shared nonce store
          | derive TrustedPrincipal internally from verified actor/tenant
          v
Existing DDD Application Service (additional domain action authorization)
          |
          | issuer-only PostgreSQL credential, from gateway secret manager
          v
0022–0025 controlled SQL commands + RLS, audit, request, outbox
```

A public API must **never** map submitted `actor_id`, `tenant_id`, `role` or `TrustedPrincipal` fields directly to an issuer command. The gateway's `execute(command, signed_evidence=...)` accepts a *typed DDD command* and a compact Ed25519 signed JWS. The private signing key belongs to an **independent IAM/attestation service**, not the ordinary API or the SQL database. `OrganizationTrustedIssuerGateway` itself has no DSN and exposes mandatory verifier, live authorization, nonce and executor ports. `OrganizationServiceExecutor` maps only seven fixed organization actions to existing Company/Establishment/LegalIdentifier/Lifecycle/Membership application methods.

**Limit:** the Python class alone does not enforce physical process isolation; only production deployment with independent credentials and network policies can prove that. Both the gateway's executor and existing DDD services must be private to the trusted process.

## G3-C02a signed command envelope (strict, fail closed)

Allowed JWS header: `{"alg":"EdDSA","typ":"JWT","kid":"<trusted-id>"}` with exact three fields. Verification key is a pinned **Ed25519 public key** from independent deployment configuration (no autodiscovered JWK, algorithm fallback or shared HMAC secret).

Allowed signed claims, **exactly**:

| Field | Meaning |
|---|---|
| `iss`, `aud`, `kind` | exact pinned IAM issuer, gateway audience, `organization.command` purpose |
| `sub`, `tenant_id` | actor identity and tenant issued by the independent IAM |
| `action`, `target_id` | exact DDD command action and typed UUID target |
| `request_id`, `correlation_id` | immutable business request and tracing identifiers |
| `request_digest` | lower-case SHA256 over the entire canonical JSON-encoded typed command |
| `iat`, `nbf`, `exp` | signed integer Unix timestamps, positive validity no more than 120 seconds by default |
| `jti` | signed UUID nonce, atomically consumed once by a required external store |

Malformed JSON, duplicate keys, untrusted key IDs, noncanonical base64url, wrong algorithm, expired/future attestation, wrong audience, wrong tenant, wrong actor field, target mismatch, different request id, changed command payload, incorrect digest or duplicate JTI must be rejected *before SQL*. The verifier returns a typed `VerifiedCommandEnvelope`; a caller constructing one by hand is **not authentication**.

The exact command digest includes the complete DDD command object (e.g. Company name, legal identifier, membership effective interval, expected revision, reason), not only the actor/action/target. Server logic determines the action/tenant/target from the typed object and compares all signed fields. No SQL write occurs before signature verification, live IAM check and atomic nonce consumption.

## Live IAM grant and revocation / replay semantics

`LiveIssuerAuthorizationPort.require(issuer, principal, action, target_id)` is **mandatory**, evaluated on every submission, even if the request is an idempotent replay. It must query an independently trusted authorization/revocation source; stale cached allow-lists are insufficient to claim a production revocation guarantee. A revoked grant blocks the command before any SQL issuer operation.

`DurableNoncePort.consume(issuer, nonce, expires_at) -> bool` must implement an atomic, durable cluster-wide insert-if-absent with secure retention through signed expiry + maximum clock skew (and sufficient replay horizon). A duplicate/failed store returns False and denies execution. **Burn-on-attempt semantics:** if downstream SQL or a process fails after nonce consumption, a client must obtain a **fresh** independently signed attestation with a fresh JTI; application request-id + digest idempotency ensures exactly one state mutation. This is not a distributed atomic transaction spanning IAM, nonce store and SQL; do not claim cross-system exactly-once delivery.

## What was implemented and proven

- `application/organization_issuer_gateway.py`: typed command identity, canonical full-command digest, required verification/authorization/nonce/execution ports, fail-closed gateway, seven-action DDD service adapter.
- `infrastructure/iam/organization_command_evidence.py`: pinned public-key Ed25519 verification with exact claims, short TTL, canonical base64url/JWS, issuer/audience enforcement.
- Unit adversarial tests create an *ephemeral private test key*, in-memory nonce mock and live-grant mock; positive signed command, invalid JWS/header, forged claims, stale TTL, content mismatch, revoked IAM grant, replayed nonce and unavailable nonce backend.
- PostgreSQL 16 integration executes **a genuinely signed Company registration** through the gateway, DDD service and independent `cc_org_company_writer_a` test credential, then verifies exact request/audit/outbox and idempotent replay and revocation before SQL.
- Existing PostgreSQL 16 role/SQL authority posture and packaging qualification remain in CI. **Migrations 0001–0025 are not edited.**

## Required deployment follow-up — G3-C02b / not yet certified

1. Supply a real IAM authentication issuer with independent signing-key custody, signing/verification rotation, auditable permission grants and revocation queries.
2. Implement and qualify `LiveIssuerAuthorizationPort` with **real external IAM authority** and revocation SLAs; do not use the in-memory grant mock.
3. Implement `DurableNoncePort` on a shared durable backing store with atomic uniqueness and retention/expiry tests under concurrency, network faults and process restarts.
4. Deploy the gateway separately; provision gateway-only PostgreSQL command issuer secrets from a separate secret manager identity, never ordinary worker environment, and demonstrate a compromised API worker cannot retrieve/use issuer credentials. Test network isolation and incident revocation.
5. Establish external audit trail for signed identity evidence (e.g. trusted token hash, issuer/key ID, request correlation) alongside SQL request/audit/outbox, no sensitive token logs. The SQL schema currently records actor_id but **not its signed attestation**.
6. Re-run an exact-head integrated qualification, then stage L03 stack consolidation and main qualification. Do not close #57 or G3 #36, publish stable, or assert SOC2 based on these R&D mocks.
