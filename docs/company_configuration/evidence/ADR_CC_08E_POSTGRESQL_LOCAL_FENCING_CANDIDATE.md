# ADR-CC-08E - PostgreSQL-local privileged fencing (PROPOSED)

**Not approved:** this is a candidate decision pending security and architecture review.

## Decision

After trusted AuthN, current-grant policy and independent approval checks, a separately deployed privileged issuer may mint a short-lived, per-request fence bound to tenant, target PostgreSQL login, role action, actor and approval. SQL role DDL requires an ACTIVE fence and locks it FOR UPDATE; the role change, consumption and evidence commit together. Revocation takes that same row lock, giving an enforceable SQL-local serial order. One ACTIVE fence per login prevents overlapping grants.

## Trust and operation boundaries

Production must place owner credentials **exclusively** in a segregated privileged control plane, never in web/tenant workers. Current repository code cannot prove this deployment is in place. The existing direct operator remains a bypass if an owner DSN is leaked. A real IAM/PAM and cryptographically independently verified checker are still required.

## Explicit non-guarantees

An external IAM revocation is not automatically atomic with PostgreSQL. A revoked decision not propagated to SQL may be executed. SQL CONSUMED does not certify subsequent backend drain, the existing terminal operation audit, incident closure or a fully applied credential change. Owner-only SQL evidence is not externally attested WORM.

## Acceptance blockers

Cross-system revocation propagation/ack and IAM lease model; admin secret and network isolation; SoD and approval signing; sensitive SQL logging, vault, TLS and managed pools; interrupted drain/restore/failover runbook; independent security review and G0/G1/G2 sign-offs. No production or stable release implied.
