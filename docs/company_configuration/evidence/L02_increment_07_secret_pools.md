# L02-07a - Tenant-scoped Secret Provider & PostgreSQL Connection Pools

**Status:** engineering candidate, subject to GitHub exact-SHA CI and independent review. G0/G1/G2 are not approved.

## Goal

This increment implements a limited, executable port to a **trusted secrets provider** and a **physically segregated pool per tenant + service role** (`runtime`, `dispatcher`, `inbox`). The public domain and application services have no dependency on this adapter. This is a proposed infrastructure composition, **not a live secret manager or IAM provider**.

## Contract

- The provider returns a `TenantCredential` carrying a tenant, role-kind, expected login role, monotonically increasing credential generation and non-printable DSN. It is queried **before every checkout**, even if the pool already exists. Missing/unavailable/foreign secrets fail closed.
- `TenantPoolRegistry` caches a physical `psycopg_pool.ConnectionPool` only for `(tenant_id, role_kind)`. Each checkout verifies both the **server-owned** `bound_tenant()` and the authenticated `session_user` matches the issued login. One tenant cannot request another tenant's pool by merely setting a GUC.
- On a higher generation, it retires the old pool. In-use connections are retired when returned; this is **not** a forced interrupt. L02-06's privileged operator and the production process must independently invalidate old server sessions and terminate revoked logins. The application layer must not hold a checkout beyond a bounded operation.
- The cached DSN necessarily lives in process memory with the pool; no claim of secret-free process memory. `repr` omits DSNs. Real credential distribution, cryptographic protection, vault authorization, refresh latency and access auditing are not in this increment.
- Same-generation secret changes and generation regression are rejected. The trusted provider must issue monotonically increasing versions; concurrent rollbacks / distributed coordination require a separately approved credential lifecycle specification.
- A vault outage causes checkout failure rather than an implicit fallback to a cached secret; existing in-flight operations can continue until forcibly terminated by PostgreSQL, which requires operational governance.

## Exact-SHA qualification matrix

- Python unit fakes: isolated tenant+role keys; rotation; grace for in-flight checkout; credential outage; stale epoch; secret drift; invalid identity; verifier failure.
- PostgreSQL integration: role-/tenant-bound pool checkouts, wrong tenant and role DSNs, refresh after version bump, no stale cached lease on provider outage.
- PostgreSQL 16, Python 3.11/3.12, Ruff. **Record exact commit, run URLs, and counts only after CI succeeds.**

## Still blocking G2

1. `TenantSecretProvider` is an interface only: no Vault/AWS Secrets Manager/Azure Key Vault or external IAM/SoD integration, nor audit of vault access.
2. No real application-service adapter composition to shared pool, no operational connection budget benchmark, backpressure, TLS certificate validation, password log redaction, secret distribution or failover tests.
3. No production privileged operation approval or independent evidence/audit of credential rotation/revocation, no emergency break-glass governance.
4. Historical repository provenance, formal ADR decisions, G0 and G1 remain unresolved; do not merge a qualified release without these gates.

## Exact-SHA CI qualification (automated checks only)

Implementation SHA `8a286b757aacba81511bc5b11876060c02b54d6d`:
- [PostgreSQL CI #40871381836](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40871381836): **46 passed** under Python 3.11 and **46 passed** under Python 3.12; Ruff green. Five new PostgreSQL integration scenarios included.
- [Python CI #40871381720](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40871381720): **108 passed, 6 skipped** (PostgreSQL integration-only modules) on Python 3.11 and 3.12; Ruff green. Nine new pure-Python unit tests included.

**G0/G1/G2 remain unsigned.** These are library-component tests on ephemeral infrastructure, not proof of production IAM, secret vault controls, TLS, or independent connection-pool security review.
