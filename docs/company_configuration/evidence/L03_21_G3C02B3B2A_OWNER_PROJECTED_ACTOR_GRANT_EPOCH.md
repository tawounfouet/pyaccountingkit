# L03-21 — G3-C02b3b2a: owner-projected actor grant epoch SQL fence primitive

**Status: bounded R&D prerequisite, not enforced in DDD commands and not independent IAM qualification.** Tracks [#67](https://github.com/tawounfouet/pyaccountingkit/issues/67), parent [#65](https://github.com/tawounfouet/pyaccountingkit/issues/65), [#59](https://github.com/tawounfouet/pyaccountingkit/issues/59) and [#36](https://github.com/tawounfouet/pyaccountingkit/issues/36). Stacked on SQL issuer COMMIT fence [PR #66](https://github.com/tawounfouet/pyaccountingkit/pull/66).

## 1. Security distinction — do not mix authority layers

The earlier 0027 COMMIT guard protects **an owner-controlled SQL issuer role**, not an individually revoked *human IAM grant*. An independently signed HTTP allow decision in the gateway can still become stale before COMMIT. No IAM→SQL revocation propagation or human-level external grant provenance is verified in this increment.

This work adds **the owner-projected actor grant epoch SQL primitive** needed for a later integration. It does not install actor fencing on existing seven DDD command paths or claim a deployed independent IdP.

## 2. Additive SQL 0028

`0028_org_actor_grant_epoch_projection.sql` (0001–0027 left byte-identical) adds `organization_actor_grant_epochs` with:

- Global `grant_id UUID`, tenant, actor, **exact supported organization action**, exact target UUID, independent `authority_issuer`, strictly positive `grant_version`, `enabled`, short `valid_until`, 64-lowercase-hex `decision_sha256`, `source_event_id` and `observed_at`.
- No bearer token, upstream service credential, raw JWT, signing private key or unnecessary human personal data.
- Only migration/SQL owner can provision/update this table. All PUBLIC grants are revoked, and SQL runtime, nonce consumer and four business issuer login identities have **no INSERT/UPDATE/DELETE/TRUNCATE** on the owner-projected grants.
- A revision guard rejects changing the grant identity/scope and rejects nonincreasing epochs and reusing an identical `source_event_id` in consecutive versions. This is a database monotonicity check, **not** cryptographic validation or upstream event replay ordering across a distributed system.
- `require_org_actor_grant_epoch(tenant,grant_id,version,actor,action,target,authority,decision_sha256)`, `SECURITY DEFINER`, pinned `search_path`, no PUBLIC EXECUTE, validates the original `session_user` against its independently owner-managed tenant + **matching business SQL issuer family**. A runtime/nonce SQL principal or a Registry login attempting a Company grant cannot pass.
- The function selects exactly one owner-projected grant with matching actor/tenant/action/target/authority/digest/version, `enabled=true`, unexpired and no more than **5 min** into the future. `SELECT ... FOR SHARE` locks that specific grant row until the **same PostgreSQL transaction** commits or rolls back; a preceding owner revocation wins and denies the check, and a later owner revocation blocks until the transaction ends.

The Python `ActorGrantEpochReference` validates the reference shape; `PostgresActorGrantEpochFence.require(connection, reference)` requires an **existing non-autocommit issuer SQL connection** and calls the SQL function in that same transaction. A Python dataclass can always be caller-constructed: this object **is not independently authenticated identity evidence**.

## 3. What a later trusted owner adapter must do

Independent upstream IAM must authenticate the grant source and signing key, check issuer/actor/tenant/action/target/grant epoch, replay controls and TTL, and atomically project **verified** updates. The owner identity performing SQL projection cannot be shared with an ordinary API or the SQL issuer gateway. Current `source_event_id`/decision hash is *owner-provided metadata*, not proof that the upstream JWT was cryptographically verified; without independent verification these are not certified.

Owner provisioning needs monotonic deliveries with durable inbox/dedup, revocation-first ordered version updates, confirmed acknowledgements, bounded propagation lag, key rotation, outage fail-closed policy and disaster recovery. Revocation only takes effect in PostgreSQL **after a trusted owner update commits**; PostgreSQL cannot know of a still-undelivered external IAM revocation.

### Audit and transaction integration left open

All seven live DDD registration/lifecycle/membership UoWs still call their 0022–0025 business SQL functions without a mandatory actor grant epoch reference. Thus **no actor-level SQL COMMIT enforcement is claimed yet**. A future migration 0029+ must thread a trusted, non-spoofable, exactly scoped per-command reference into controlled write/receipt/evidence paths, bind its signed digest and original JTI, and require the epoch lock **inside every relevant business transaction**, preferably at SQL-level COMMIT or protected issuer function boundaries.

When a late actor grant check fails, SQL domain/request/audit/outbox must roll back while separately consumed JTI remains spent. Proper immutable audit/outbox link to signed decision hash, grant ID/version, issuer/key ID and exact command digest is future work. No caller-controlled `actor_id`, GUC, plain `TrustedPrincipal`, CI mock credential or SQL session role alone constitutes an independent IAM decision.

## 4. Executable R&D checks

- Four issuer SQL families can explicitly invoke the tenant-scoped epoch lock with a correctly supported action; other issuer family cannot reuse the same approved grant.
- Wrong tenant/actor/action/target/version/decision SHA/authority/grant ID, revoked or expired epoch, over-long expiry and disabled issuer are denied.
- Owner epoch increment invalidates stale references, including reenabled grants with a newer epoch. Owner cannot rewrite actor/scope or regress a grant version.
- A held `FOR SHARE` blocks owner revocation with a finite lock timeout; revocation committed before the check is denied. Tests exercise the actual PostgreSQL 16 connections, not simulated synchronization.
- Ordinary runtime/nonce principals cannot invoke the epoch function or mutate the projection; all four SQL issuers cannot mutate the projection.
- G3 SQL authority posture check now requires correct `SECURITY DEFINER`, pinned search paths, no PUBLIC EXECUTE, correct caller privileges and no owner-grant write privileges.
- Source/wheel/sdist SHA256 parity across **28** migrations, Python 3.11/3.12 and PostgreSQL 16 recovery required for qualification.

## 5. Residual external security gaps

No actual external IdP, independently signed verified grant delivery, IAM source-of-truth SLA, distributed revocation propagation, gateway-only credential/key custody, deployed gateway boundary, comprehensive immutable actor provenance or native SQL mandatory actor-grant integration. **Issue #67 remains OPEN** pending these components. G3, G3-C02b and all upstream stacked L03 PRs stay unmerged; no stable release or production authorization compliance can be inferred from this prerequisite.
