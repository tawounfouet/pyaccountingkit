# ADR-CC-08A - Tenant SQL login operations and connection lifecycle (proposed)

- **Status:** PROPOSED, not accepted.
- **Context:** L02-05 binds SQL tenant identity to `session_user`. Production readiness additionally requires explicit credential issuance, rotation, revocation and pool lifecycle. An application-controlled GUC must never grant additional tenant access.
- **Decision candidate:** A privileged, separately deployed administrator owns tenant-role lifecycle. Each tenant has distinct runtime, dispatcher and Inbox login credentials. A role may belong to one tenant only. Production pools must be physically segmented by PostgreSQL login/tenant, never repurposed across tenants. On credential rotation or revocation, terminate existing DB sessions and force pool invalidation. Enforce account and expected tenant equality before role changes. Do not expose admin DSNs to request handlers.
- **Security controls:** least privilege, no inheritable tenant role membership, no application `CREATEROLE` or `BYPASSRLS`, operator approvals + durable audit + protected secret manager, no password-bearing SQL statement logging, validated TLS, emergency-revocation runbook and independent attack review.
- **Consequences:** role count/pool count and operational complexity grow with tenants. A shared pool by tenant cannot be used; privileged provisioning is part of the trusted computing base. Rotation demands coordinated rollout; an unsuccessful session drain is a security incident. A new-connection factory does not itself prove any pool implementation.
- **Rejected shortcut:** reuse one database credential with `SET app.tenant_id` per request; that was shown spoofable by L02-04 tests and rejected in L02-05.
- **Open:** exact ownership of privileged IAM admin, secret manager, TLS enforcement, operator authorization/SoD, full SQL statement auditing, tenant pool driver, deployment rollback, cross-region restoration, SLO and testing after live credential expiry.

This ADR is a **candidate decision** pending architectural review and sign-off. It must not be cited as approved company policy.
