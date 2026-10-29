# ADR-CC-08H - Separate privileged SQL audit capability

**Status: PROPOSED.** Not approved by CI, not a production sign-off.

## Decision candidate

Separate the privileged role operation capability from the privileged audit writer capability at the PostgreSQL authentication boundary. `cc_control_plane` can invoke only three narrowly restricted fencing routines. `cc_privileged_audit` can invoke only a fourth schema-owner-controlled `SECURITY DEFINER` journal entry point. Neither login gets direct table access, PostgreSQL superuser or CREATEROLE. The application composition requires and checks both capabilities, rejecting a schema-owner credential.

The SQL audit function applies server-side phase constraints, binds terminal records to an existing INTENT and requires a consumed exact-scoped SQL fence before recording `SUCCEEDED`. It uses server time and the existing append-only audit table and trigger, without changing historical migration checksums.

## Rejected alternatives

- Continue using `PostgresPrivilegedAudit(ADMIN)` in the main application composition. This gives the role-operation process unnecessary owner privileges.
- Grant plain INSERT/SELECT on `privileged_operation_audit` to a runtime role. This allows fabricated completion and direct inspection of the full privileged journal.
- Declare this an independent external evidence store or zero-trust audit. Schema owners can still control SECURITY DEFINER functions and the stored records.

## Required production gates

- Separate independently controlled audit storage and attestability/retention; separate audit operator and infrastructure owner, incident review and operational monitoring.
- Signed or independently verified IAM approvals and authentic operator identity; delegated SQL role must not accept unchecked actor/checker strings from an untrusted caller.
- Hardened isolated deployment, egress constraints, TLS, secret vault/workload identities, explicit deny of admin DSN in request paths, SQL sensitive-statement logging policy, backup/failover and recovery exercises.
- Deterministic ownership/approval of the migration and operational ADR, independent security review, signed G0/G1/G2.

This ADR merely proposes a smaller SQL capability boundary, not a full deployment architecture.
