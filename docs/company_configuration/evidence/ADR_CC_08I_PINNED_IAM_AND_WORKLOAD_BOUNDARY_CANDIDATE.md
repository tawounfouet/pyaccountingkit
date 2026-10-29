# ADR-CC-08I - Pinned signed IAM evidence and strict workload startup boundary

**Decision status:** PROPOSED, not approved. CI alone must not close G2.

## Context

The delegated SQL control and audit roles introduced in ADR-CC-08G/08H remove schema-owner credentials from the normal privileged service composition. However the `OperatorIdentityPort` and `ApprovalVerificationPort` still depend on independently trusted implementations. The current application accepts `VerifiedOperator`/`VerifiedApproval` from those ports; unauthenticated stubs are insufficient for production. Also, SQL role separation is not process or network isolation.

## Candidate decision

Use distinct, pinned Ed25519 signer trust roots for short-lived **operator authentication assertions** and independently retrieved **approval assertions**, represented as strict compact JWS/EdDSA envelopes. Verify signature, issuer, audience, kind, identity, exact request scope and time before constructing typed application identities. Do not follow token-supplied URLs or keys. Keep authorization grants/revocations in a separately trusted live policy adapter. Only a separately controlled approval evidence source may return the approval assertion by reference.

Production control-plane startup should fail closed when schema-owner or runtime DB credentials are present, when the expected dedicated audit/DDL login is not configured, when TLS `verify-full` is absent, or when the two signing roots are not distinct. Continue to have the L02-07h composer validate actual PostgreSQL `session_user` and capability grants.

## Alternatives and rejected claims

- **Accept caller-provided operator/approval IDs**: not authentication; SoD is bypassable.
- **Accept arbitrary JWT headers, JWK URLs or `alg=none`**: algorithm/key confusion and attacker key injection.
- **Assume signed but unrevoked approval**: an offline signature cannot establish current authorization or close a remote IAM/database race.
- **Treat an environment check as a network security boundary**: static startup checks do not prove runtime confinement, absence of a privileged credential elsewhere or mTLS workload identity.

## Required independent decisions before G2

- Select production IdP/issuer, key ownership, JWKS/pin rotation lifecycle, alerting on key revocation, signed-approval repository, required evidence freshness and mTLS/DPoP token binding.
- Build the real policy/approval providers and test revocation ACK and operator grant/approval invalidation under concurrency with privileged role DDL.
- Deploy privileged execution and audit in separate tightly scoped processes/workloads with distinct secret-manager policies, network egress controls, pinned CA, workload identity and independently controlled owner/migration role.
- Audit SQL password statement logging and separate the owner-only operational audit custody, WORM/retention, backup/restore, tenant segregation, failover and incident drills.
- Independent architecture and security review; approve G0 and G1 before signing G2. No production release until then.
