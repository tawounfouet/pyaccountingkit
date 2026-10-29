# ADR-CC-08B - IAM-gated privileged SQL operations and SoD (candidate)

**Status: PROPOSED, NOT ACCEPTED**

**Context:** L02-06 owner-only SQL role operators can mutate PostgreSQL logins, while L02-07a offers tenant-scoped pool/secrets ports. Those primitives do not establish human authorizations, independently approved operations, a reliable journal of privilege changes, or separation of duties.

**Candidate decision:** Require authenticated operator identity, an independently verified operation-specific approval with a different effective actor, and an authoritative policy check. Fail closed on any failed verification or unavailable **intent** audit. Write an immutable owner-only intent record before SQL role DDL and a separate immutable outcome afterwards. Use unique request IDs for intent replay prevention. Treat incomplete outcome audit as a security incident; never represent the operator action as safely completed.

**Alternatives not accepted as sufficient:** trusting a role name supplied by a client; authorization determined by PostgreSQL tenant RLS alone; an unauthenticated `approve=true` flag; self-approval via another role; writing a single audit record after the SQL operation without any precondition; logging secrets for audit convenience.

**Trade-offs:** separate audit transactions can leave unresolved intents or ambiguous role outcomes. A later version should provide a dedicated privileged control plane with external durable workflow state, approval revocation checks, and a reconciliation worker. No schema-owner database session should be accessible to normal request handlers.

**Review required:** external IdP and approval provider contracts; policy revision/TTL, MFA, privileged operator SoD roles, approved action set, vault integration, secure log posture, operation recovery/idempotence, real deployment isolation and independent attack testing. G0/G1/G2 remain unsigned.
