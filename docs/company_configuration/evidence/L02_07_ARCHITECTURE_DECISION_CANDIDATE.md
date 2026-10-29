# ADR candidate - Tenant pool & external credential provider

**Status: PROPOSED - not approved.**

- Context: INF-02/07 and SEC default-deny prohibit shared tenant credentials, silent fallback and secrets in domain DTOs. L02-05 binds login role to tenant via PostgreSQL `session_user`.
- Proposed decision: use one physical PostgreSQL pool per `(tenant, role_kind, credential generation)` and a trusted versioned provider. Every checkout independently validates the server-side tenant and login identity; stale/unavailable secrets refuse service. Role lifecycle operator and pool owner are separate trust boundaries.
- Consequences: more DB sessions as tenant count grows; isolation reduces accidental cross-tenant pooling but increases resource consumption. An explicit pool size/budget and eviction strategy is needed before production. Credential generation must be monotonically managed across replicas. Compromised tenant credentials retain within-tenant privileges; business action IAM/SoD remains mandatory.
- Alternatives deferred: a shared pool with application GUC (not secure against adversarial SQL client), one database per tenant (operational overhead), per-request fresh connection (no pooling), a secure independent PostgreSQL proxy (evaluate after requirements).
- Acceptance pending: independent security review, operator/secret access model, pool benchmark under N tenants, revocation/cert rotation/pooling failure drills, TLS and backup/restore evidence. Do **not** mark G2 approved on green unit/integration tests alone.
