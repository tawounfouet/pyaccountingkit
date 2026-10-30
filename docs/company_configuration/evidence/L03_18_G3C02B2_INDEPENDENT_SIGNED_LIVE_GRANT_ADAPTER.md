# L03-18 — G3-C02b2 Independent Signed Live IAM Authorization Decisions

**Status: bounded R&D qualification candidate.** This document specifies the concrete external IAM *protocol adapter*, not a vendor-certified or production-deployed IdP. Tracks [#61](https://github.com/tawounfouet/pyaccountingkit/issues/61), parent [#59](https://github.com/tawounfouet/pyaccountingkit/issues/59), G3 [#36](https://github.com/tawounfouet/pyaccountingkit/issues/36), and builds on signed gateway #58 + durable nonce #60.

## 1. Confirmed missing boundary

The gateway previously verified a pinned Ed25519 command attestation and consumed a PostgreSQL-backed one-use JTI, but live authorization was exercised **only** with an in-memory mock. Signature verification alone cannot establish *current* permissions after a grant revocation. Conversely, direct SQL issuer login authority verifies the SQL credential, not the human `actor_id` or current IAM authorization.

**G3-C02b2 adds a concrete independently signed HTTPS grant decision adapter**, while retaining the mock only as an injected test upstream. No producer-side IdP and no production network/secret infrastructure have been connected in this slice.

## 2. Trust topology and flow

```text
[Ordinary API] typed command + independently signed command JWT
      |
      v
[Isolated gateway] verify pinned command Ed25519 signature, tenant/action/target/digest
      |
      | POST /v1/organization/authorization/decisions
      | gateway service bearer credential (vault-injected, NOT caller token)
      | fresh challenge UUID + signed command nonce + full request identity
      v
[Independent IAM grant/revocation decision provider]
      |
      | one Ed25519 signed allow/deny/revoked decision
      | pinned independent decision verification key
      v
[Gateway] verify exact decision + challenge + TTL + current authorization version
      |
      v
[Durable nonce SQL consumer] atomic one-time JTI commit
      |
      v
[Existing DDD organization command services + independently issued SQL writer]
      |
      v
[PostgreSQL domain row + request receipt + audit + outbox in one SQL transaction]
```

`LiveIssuerAuthorizationPort.require` now receives the **full bound command identity**: `issuer`, `TrustedPrincipal`, `action`, `target_id`, `request_id`, `correlation_id`, `request_digest`, `command_nonce`. The gateway derives these from a verified command token and typed DDD command; the raw API caller is not permitted to inject a `TrustedPrincipal`.

## 3. Wire contract (version 1, provider-independent)

`POST https://<pinned-iam-origin>/v1/organization/authorization/decisions` with `Content-Type: application/json`, `Accept: application/jose`, `Cache-Control: no-store`, and deployment-injected `Authorization: Bearer <gateway-service-credential>`. The origin is pinned configuration, **not token metadata or user input**, and must be HTTPS with no embedded credentials, redirect or arbitrary path; existing stdlib `HttpsIamTransport` uses system trust/hostname checking and denies redirects.

The JSON body contains **exactly** `command_issuer`, `sub` (actor), `tenant_id`, `action`, `target_id`, `request_id`, `correlation_id`, `request_digest`, `command_nonce` and a **new random `challenge` UUID for every HTTP call**.

The provider must respond `200 application/jose` with a **compact EdDSA / Ed25519 JWS**, signed by a **separate pinned decision authority**. Exact protected header: `alg=EdDSA`, `typ=JWT`, trusted `kid`. No unsigned, algorithm-switch, remote JWK autodiscovery, missing/duplicate fields, unrecognized key, altered signature or oversized response is accepted.

The signed payload contains exactly the ten echoed request fields plus:

| Signed claim | Contract |
|---|---|
| `iss` / `aud` / `kind` | pinned decision authority / gateway decision audience / `organization.authorization.decision` |
| `allowed` | **boolean true** required; false is denial |
| `revoked` | **boolean false** required; true is denial |
| `grant_id` | canonical UUID of the authorization grant, provider-defined |
| `grant_version` | integer >=1; provider must guarantee current authoritative revision |
| `iat`, `nbf`, `exp` | integer Unix timestamps, coherent and signed, validity <=30s default; no expired or not-yet-active decision |

Each request generates a fresh random challenge. **A recorded, still-valid signed allow response is not reusable**, because its signed challenge will differ from the new request. The command attestation JTI and whole command digest also bind the response to the *specific* verified request. This check does not replace the separate atomic nonce-consumption gate.

### Failure / logging contract

- Non-200, malformed body, mismatch, denial, revoked, expired, invalid signature, network outage, timeout, unknown key, unavailable transport or any unexpected verification error raises `PermissionDenied`. No SQL nonce or business command is consumed before positive verification.
- No cached positive result, no fallback to client-declared `actor_id`, no pre-signed “permission granted” JWT taken from the ordinary caller. No authorization retry that could accidentally weaken a revocation decision.
- The adapter's `repr` redacts the bearer service token. Do not print the token, signed decisions or HTTP authorization headers to application logs. Runtime exception chaining should be sanitized by the deployment error boundary as well.
- The provider **must validate its own service caller credentials** and authoritative live grant/revocation state on *every request*. The adapter can verify the response signature and binding, but cannot independently prove the provider actually checked its internal IAM source.

## 4. Executable tests and limits

Unit tests use only an **ephemeral test Ed25519 private key** and injected fake HTTP transport. They exercise strict signed allow/revoke/deny, missing or altered identity/action/tenant/target/command digest/JTI/challenge, stale/future grant, key/algorithm switch, invalid signature, replayed old signed positive response, unavailable provider, HTTPS pinning, explicit timeout and token redaction.

The real PostgreSQL 16 Company registration integration uses **the actual signed live-grant adapter** with a fake HTTP IAM responder, then the **actual PostgreSQL-backed durable JTI** and the **Company-controlled SQL writer**, and proves one atomic business/request/audit/outbox entry, idempotent fresh-token replay, original-token reuse refusal, and zero new writes after a signed revoked response. The fake remote authority signs **in test code only**.

Existing G3-C01 SQL issuer posture, migrations 0001–0026 checksum/recovery and source/sdist/wheel parity remain required.

## 5. Still-open production blockers

1. **Independent real provider:** no real upstream grant/revocation provider service or IAM tenant-to-actor authentication, no production issuer/decision signing-key custody or key rotation evidence. The test transport is not a live production HTTP call.
2. **Separate deployment:** a code-level gateway does not enforce process/host/secret separation. Require network segmentation and a gateway-only vault identity with SQL writer/nonce consumer DSNs; compromised ordinary API worker must be unable to read those secrets.
3. **Revocation window / TOCTOU:** “current” means provider state at decision time. A grant may be revoked **after** a positive decision but before the SQL commit. Production requires a bounded revocation SLA, freshness thresholds, and either revalidation, transaction-bound authority fencing, or an explicit risk acceptance. This slice does not provide atomic external IAM-to-PostgreSQL authorization.
4. **Attestation provenance:** SQL audit currently stores caller actor metadata from controlled SQL issuance, not a cryptographic decision hash, grant ID/version or signed decision evidence. Separate durable evidence linkage and independent logs are required.
5. **Production retention and continuity:** nonce retention/backup capacity, IAM timeouts/outages, cross-region failover and incident recovery remain operator acceptance tasks.
6. **Broader command verification:** Company signed gateway E2E is exercised; Establishment, LegalIdentifier, lifecycle and membership require their own live signed-grant + SQL end-to-end qualification.

**Do not close parent #59/#57 or G3 #36 or merge L03 solely on this R&D contract.** No human IAM production certification, main qualification or stable release claim.
