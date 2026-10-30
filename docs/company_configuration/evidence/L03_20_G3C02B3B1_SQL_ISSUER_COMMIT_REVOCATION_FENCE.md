# L03-20 — G3-C02b3b1: SQL issuer COMMIT revocation fence

**Status: bounded PostgreSQL-local R&D slice; NOT transaction-bound human IAM.**
Tracks [G3-C02b3b #65](https://github.com/tawounfouet/pyaccountingkit/issues/65), depends on [G3-C02b3a #64](https://github.com/tawounfouet/pyaccountingkit/pull/64). Parent [G3-C02b #59](https://github.com/tawounfouet/pyaccountingkit/issues/59) and [G3 #36](https://github.com/tawounfouet/pyaccountingkit/issues/36) remain OPEN.

## The specific revocation guarantee being added

Prior SQL issuer allowlists (`organization_{company,registry,lifecycle,membership}_command_issuers`) were checked at the beginning of the controlled write. An owner-disabled SQL issuer *after* this check but *before* COMMIT could still write business records and audit/outbox evidence. PostgreSQL can close that local credential authority race without introducing an unverifiable external IAM claim.

The additive `0027_org_issuer_commit_revocation_fence.sql` adds two pinned-`search_path` `SECURITY DEFINER` functions and nine `AFTER INSERT FOR EACH ROW DEFERRABLE INITIALLY DEFERRED` constraint triggers on the request/audit/outbox evidence tables across all four SQL issuer families.

- Each deferred trigger identifies the family from **signed-command evidence target_kind** for the Company/Registry shared evidence tables or from the dedicated lifecycle/membership evidence table identity.
- The privileged function verifies the **original PostgreSQL `session_user`**, the independently owner-maintained tenant binding `bound_tenant()`, and the correct family's separately maintained issuer allowlist row, `enabled=true`.
- `SELECT ... FOR SHARE` locks the owner-managed issuer row through COMMIT. A concurrent owner-issued `UPDATE enabled=false` must acquire an incompatible row lock. If the owner's disablement commits **before** the fenced transaction obtains this lock, the fenced SQL commit is refused and all business/request/audit/outbox records roll back. If the command locks first, the owner's disablement waits and cannot commit until after that command finishes.
- This is **serialization relative to owner-managed SQL issuer role revocation**, not a guarantee that a remotely revoked *human IAM grant* is already represented in PostgreSQL. There is no remote IAM SQL sync pipeline, grant epoch per actor or external IdP attestation in this slice.
- Both new SQL functions revoke PUBLIC EXECUTE; the privileged helper has a static family whitelist, never dynamic caller-controlled SQL. The original SQL issuer-only controlled registration/lifecycle/membership grants and the 0001–0026 migrations are unchanged.
- The original SQL read-only G3-C01 posture verifier now checks all nine COMMIT triggers are enabled **AFTER INSERT / ROW / DEFERRABLE / INITIALLY DEFERRED**, their exact function target, and the new helper security properties. An ordinary runtime SQL login must not be able to bypass this fence or `SET ROLE` into an issuer identity.

## R&D red-team and positive SQL tests

The seven-action signed gateway suite is kept intact: ephemeral test Ed25519 command key → signed fake IAM HTTP decision → actual PostgreSQL one-use nonce → independent real SQL issuers → atomic audit/outbox.

New parameterized tests, one per issuer family (Company, Registry, Lifecycle, Membership):

1. The owner first grants the issuer role (`enabled=true`).
2. The real controlled SQL command writes domain + request/audit/outbox **but does not commit**.
3. Its test-only `before_commit` hook opens an **independent admin PostgreSQL connection** and commits `enabled=false` for the original issuer role.
4. The already staged command then attempts COMMIT. A deferred issuer fence sees the revoked SQL login and rejects COMMIT with SQLSTATE `42501`. All transaction business/evidence rows are rolled back. The independently committed JTI remains spent (**burn-on-attempt**).
5. An owner-controlled reset re-enables the issuer; replaying the same signed JTI still fails the durable nonce check.

The complementary locking test forces PostgreSQL deferred constraints to execute early *inside the controlled transaction* via `SET CONSTRAINTS ALL IMMEDIATE` and holds the issuer `FOR SHARE` lock. A separate owner revocation `UPDATE` with a strict lock timeout must block. After the controlled transaction commits, the owner disablement succeeds; a subsequent new signed command must fail its SQL issuer check even though the mocked HTTP IAM allows it.

CI must qualify **27 SHA256-identical SQL migrations** in source, wheel and sdist; 0001–0026 checksums untouched; Python 3.11/3.12, PostgreSQL 16, recovery and SQL authority posture must remain green.

## External human IAM TOCTOU remains OPEN

An independently signed live IAM allow decision can still become stale after the HTTPS check. Owner-managed `organization_*_command_issuers.enabled` is a SQL **login** authorization bit, **not** an actor-specific grant/epoch with authorized action, target, issuer nonce, attestation hash or revocation version. A revoked human grant does not magically disable the SQL login, and doing so would revoke every operation through that login (coarse-grained emergency kill switch). No external atomic IAM/DB transaction exists.

Closing [#65](https://github.com/tawounfouet/pyaccountingkit/issues/65) requires a verified **independent IAM-to-SQL revocation/epoch distribution and commit-time actor/action/grant/version fence**, or explicit risk-accepted non-atomic revocation semantics with measured SLA and trustworthy control ownership. Do not silently replace this with an `actor_id` string, GUC, trusted session_user alone, in-memory grant cache or mock signer.

Production requirements still missing: independently deployed gateway and secret/key custody, real IdP/grant decision provider, revocation propagation SLA/partitions/incident path, signed actor/epoch provenance linked to immutable SQL audit and external C10 delivery, stress tests under true concurrent processes and disaster recovery. **No G3 closure, stable release or merge** may be claimed from this local SQL issuer slice.
