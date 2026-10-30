# L03-22 — G3-C02b3b2b1: signed IAM decision verification at the projection owner

**Status: bounded R&D proof candidate.** Parent [#69](https://github.com/tawounfouet/pyaccountingkit/issues/69), actor-grant epoch [PR #68](https://github.com/tawounfouet/pyaccountingkit/pull/68), SQL issuer COMMIT fence [PR #66](https://github.com/tawounfouet/pyaccountingkit/pull/66). Does **not** integrate mandatory actor grant authorization into the seven SQL business functions, or prove independent production IAM and gateway deployments.

## 1. Trust boundary

An owner-provisioned `ActorGrantEpochReference` from PR #68 is **not** evidence that an external IAM permitted anything. A compromised app/issuer can create this Python value; it must not be used to grant itself access. Previous `organization_actor_grant_epochs` data was only a SQL-owner-managed snapshot, without required independently signed event provenance.

**This increment introduces a signed JWS re-verification boundary before updating owner-managed SQL actor grants:**

```text
[Independent IAM authority (production NOT DEPLOYED)]
      |
      | compact Ed25519 decision JWS
      v
[PinnedIamGrantProjectionVerifier]
      | Ed25519 pinned keys; exact issuer/audience/purpose;
      | strict JWT field/header set; canonical base64 and JSON;
      | actor/tenant/action/target/request/digest/JTI/challenge;
      | grant ID+monotonic epoch; <=30 s signed TTL
      v
[PostgresVerifiedIamGrantProjector — separate owner SQL credential]
      | owner-managed SQL transaction
      | append signed decision SHA256/metadata receipt
      | insert or advance matching actor grant epoch
      v
[PostgreSQL receipts + actor-grant-epoch projection ATOMICALLY]
      |
      v
[Separate 0028 actor-epoch SQL SHARE lock primitive]
      |
      +----> mandatory per-command SQL function wiring: NOT YET IMPLEMENTED
```

The verifier consumes the **raw compact signed JWS**, never a caller-constructible `VerifiedGrant` or `TrustedPrincipal`. It uses the existing pinned `SignedLiveGrantTrust` schema (independent Ed25519 decision authority, not command token key). Only exact `EdDSA`/`JWT`/trusted `kid` headers, strictly shaped signed claims, recognized seven organization actions and short valid time bounds are accepted. A positive `allowed=true, revoked=false` event enables; an explicit `allowed=false, revoked=true` signed event disables. An unsigned/unsupported denial combination cannot silently grant or revoke the epoch.

No trust is placed in caller-supplied signed-claim fields without verifying the IAM signature. **The verifier does not itself prove that the external IAM provider authenticated the human or actually checked its current grant database**, only that the *configured pinned key* signed the event. Production key custody and independently authenticated IAM-to-owner delivery remain necessary.

## 2. Additive SQL 0029

`0029_org_signed_iam_grant_projection_receipts.sql` adds `organization_actor_grant_decision_receipts`:

- `authority_issuer`, globally unique within issuer `challenge` and `command_nonce`;
- grant ID/version, exact tenant/actor/action/target, command issuer, request ID/correlation, canonical request SHA256, decision JWS SHA256, trusted signer `kid`, allow/revoke disposition, signed issue/expiry time and DB projection clock;
- **no raw compact JWS, bearer token, HTTP credential, private key or session secret**;
- `REVOKE ALL FROM PUBLIC`, no DML grants to ordinary runtime or any issuer principal, and permanent BEFORE UPDATE/DELETE immutability trigger;
- the IAM projector writes the receipt and updates owner-only `organization_actor_grant_epochs` in **one SQL transaction**. A duplicate identical JWS produces an explicit idempotent no-op; an altered challenge/JTI collision, same/lower version or changed grant scope raises a conflict and rolls back the receipt. A higher signed version carries a new SHA256 and atomically enables or revokes the grant.

Existing SQL historical migrations 0001–0028 must remain byte-identical; migration/recovery and isolated source/wheel/sdist packaging now require 29 files.

## 3. Security ownership and invariant boundaries

**R&D only**: the PostgreSQL owner is used as fixture identity in CI. A production projector must use a separately provisioned least-privileged grant projection service login that is **not available** to ordinary API workers, gateway business SQL issuers or nonce consumers, and must never grant arbitrary DML to those identities. Authenticate the producer separately (mTLS/service identity + independently pinned decision signing key); enforce replay and chronology outside the ordinary API process.

The signed decision JWS contains `request_id`, `correlation_id`, `request_digest`, `command_nonce` and `challenge` so the receipt is attributable to **what the signer actually signed**. However **this owner projector does not independently verify a command-signing JWS or match the decision to a trusted gateway-issued challenge**: it validates the IAM signature/claims and replay uniqueness, not the pairing of a request to a live gateway call. That authenticated handoff is a further gate to qualify before production. An IAM signing key compromise or provider misissuance is outside the guarantees of this slice.

The existing 0028 epoch function locks a matching owner snapshot under the original tenant-bound SQL issuer login, but **neither the separate projector nor the existing seven DDD SQL controlled functions mandate the per-request proof at COMMIT yet**. The prior actor-IAM TOCTOU test from PR #64 still demonstrates the unresolved remote revocation race. Snapshot SQL locks serialize only owner-projected revocation updates, **after** independent IAM synchronization has delivered them.

## 4. Executable adversarial evidence

PostgreSQL 16 tests use an **ephemeral test Ed25519 signer** and an **injected pinned public verification key**; they prove:

- signed IAM allow → owner SQL epoch + append-only provenance receipt committed atomically, exact identical event is idempotent;
- a *higher signed grant version* carries an explicit revoked state, invalidates the prior epoch, and a later authorized revision may enable it again;
- changed actor/action/target on the same grant ID, stale or same version, mismatched issuer/audience/purpose, unsupported action, invalid UUID/request digest/time, altered signature and unpinned algorithm/KID are rejected before SQL or rolled back without an orphan receipt;
- an old signed event's JTI/challenge cannot be reused to create another projection; both replay uniqueness constraints apply;
- runtime/nonce/business issuer logins cannot insert decision receipts or modify owner-projected grants; even the SQL owner cannot UPDATE/DELETE append-only decision receipt rows;
- a successfully projected allow can be checked by the 0028 PostgreSQL actor epoch SHARE-lock from the independently authorized Company SQL login; this demonstrates **primitive composition only, not mandatory production enforcement**.

## 5. Remaining requirements under #69

1. Independently authenticated **real** producer/IdP decision stream and grant/revocation state, operator-issued service credential, signing key custody/rotation, challenge issuance ownership, durable inbox/order/ACK/reconciliation and bounded propagation latency.
2. Mandatory **non-bypassable** actor-scoped COMMIT guard in all **seven** controlled SQL functions (migration 0030+). Historical direct issuer function EXECUTE surfaces must be revoked or instrumented, including any legacy/test-only caller. Do not infer source authentication from a Python dataclass, raw actor string, GUC or SQL role alone.
3. Immutable per-request SQL business audit/outbox link to grant ID/version, JWS hash/KID, exact command digest and authenticated gateway challenge/JTI. These business receipt references **are not written by this projector**.
4. Genuine concurrent IAM revocation vs PostgreSQL COMMIT under network partitions, multi-process gateways and independent key/secret custody, measured end-to-end SLA. Neither CI ephemeral IAM key nor a local SQL owner fixture qualifies production independence.

Keep [#69](https://github.com/tawounfouet/pyaccountingkit/issues/69), [#67](https://github.com/tawounfouet/pyaccountingkit/issues/67), [#65](https://github.com/tawounfouet/pyaccountingkit/issues/65), [#59](https://github.com/tawounfouet/pyaccountingkit/issues/59) and G3 [#36](https://github.com/tawounfouet/pyaccountingkit/issues/36) OPEN. No stable version, `main` merge or production IAM compliance evidence.
