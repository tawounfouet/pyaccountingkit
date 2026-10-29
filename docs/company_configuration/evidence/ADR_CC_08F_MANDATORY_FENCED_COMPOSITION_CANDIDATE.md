# ADR-CC-08F - Mandatory Fenced Privileged Role Composition

**Status: PROPOSED. No G2 or production security sign-off.**

## Candidate decision

All application-level privileged SQL role changes must flow through PrivilegedRoleService with a required PrivilegedFencedExecutorPort. After verifying the effective actor, current grant and independent approval twice, the service commits INTENT, issues an exact-scoped fence and executes the role action using that fence. SQL-local revocation and role DDL serialize through the same row lock, with role DDL and permit consumption committed together.

## Rejected alternatives

- Keep a direct TenantRoleOperatorPort in PrivilegedRoleService and document the fence as optional: bypass remains in normal application composition.
- Declare SQL-local fencing globally IAM-atomic: external revocation remains asynchronous.
- Remove all DB owner capabilities from the repository without an operational migration strategy: a leaked privileged DSN is still a bypass until deployment isolation is proven.

## Remaining decisions

Restrict privileged control plane deployment, admin DSN issuance and API surface. Define IAM revocation propagation, approval freshness and acknowledgment. Certify audit/reconciliation of post-DDL drain failures, including a missing application terminal record. Test credential logging, restore, failover and incident operations. Require independent review and approved G0/G1/G2 gates.
