# L02 Increment 01 - Ports and in-memory transactional proof

**Status:** candidate implementation; G0, G1 and G2 remain **unapproved**. 2026-10-29.

## Design boundary

This step exercises an application slice over the L01 `LegalEntity` model. It is deliberately limited to a test adapter: **no SQL database, migrations, durable audit, production IAM, published configuration, C10 schema or actual event delivery exists**. No business operation posts journal entries.

## Implemented

1. Typed `CreateLegalEntity` and `RenameLegalEntity` commands, independent of Django/ORM/HTTP.
2. `TrustedPrincipal` context populated by a future trusted authentication adapter, not raw request JSON. Server authorization port with default-deny memory allowlist; access check before repository access or cached idempotent response.
3. `LegalEntityRepository`, `UnitOfWork`, `AuthorizationPort`, `ClockPort` abstract ports; structured receipt, audit and pending event records.
4. `LegalEntityService`: scoped create/read/name amendment, optimistic revision, reason/correlation, scoped idempotency and stable typed failures.
5. `MemoryUnitOfWork`: copy-on-enter staging and guarded commit with one-process lock. Entity + audit + outbox + request record commit together *for memory adapter only*; injected failure before commit leaves state unchanged.
6. Security/negative tests: tenant crossing, company-scope guessing, missing grant, revoked access before replay, stale revisions, duplicated keys with mismatched request, concurrent writes, simulated pre-commit failure, invalid clock.

## Limits and ADRs not settled

- An allowlisted `TrustedPrincipal` is **not** a security token or a trusted identity verifier; transport adapter must verify caller identity and scopes, and infra must implement object-level access and deny-by-default.
- Memory store has no persistence or cross-process atomicity, and its inspection attributes are for tests only. It is not a compliance-qualified append-only audit log.
- `PendingEvent` is an **internal candidate** and not a contracted C10 integration event; external delivery, retry, deduplication and retention are not implemented.
- Idempotency identity is `(tenant, actor, scope, action, request_id)`, a provisional model subject to ADR; request digest covers semantic payload (not correlation metadata). Durable expiry, policy and operation-level conflict rules remain open.
- The zero-/one-revision assumption is limited to new/amended `LegalEntity`, not a general published configuration revision scheme.
- Reader queries do not write denied-decision audit. This must be addressed before G2.
- The `MemoryUnitOfWork` commit behavior simulates an atomic in-process boundary only. Test results must not be advertised as PostgreSQL transactional proof.

## Qualification checklist

- [ ] Verify GitHub CI status on exact SHA for Python 3.11/3.12 (pytest, Ruff).
- [ ] Review typed commands and port interfaces independently.
- [ ] Decide ADR-CC-03 (storage), ADR-CC-05 (publication atomicity), ADR-CC-08 (AuthZ and SoD) before production adapter.
- [ ] Introduce SQL schema, migrations, security isolation guarantees and post-failure recovery tests.
- [ ] Test append-only audit and outbox delivery with a real persisted implementation.
- [ ] Record G0/G1/G2 sign-offs explicitly. This increment itself cannot close G2.
