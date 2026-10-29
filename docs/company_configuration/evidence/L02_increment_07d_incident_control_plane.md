# L02-07d - Privileged Incident Control Plane: Independent Decisions

**Status:** draft technical candidate. **G0 / G1 / G2 are not approved.** No external IdP, IAM approval workflow, privileged control-plane deployment, vault or production release is claimed.

## Source requirements and purpose

The Company Configuration Security, Authorization & Audit Model (`19_COMPANY_CONFIGURATION_SECURITY_AUTHORIZATION_AND_AUDIT_MODEL.md`) calls for default deny, strict SoD on effective identities, append-only critical mutation audit, distinct audit/domain events and no credential material in evidence. L02-07b records privileged intent before DDL; L02-07c flags old unresolved intent as `OUTCOME_MISSING / UNKNOWN`. **A review record is not evidence that a past SQL mutation succeeded or failed.**

L02-07d adds a **human-controlled incident disposition** to that state without replay, credential rotation, SQL role alteration or dishonest classification of a historical DDL result.

## New ports and components

- `PrivilegedIncidentService` verifies a principal through `OperatorIdentityPort`, checks the *current* disposition grant through `IncidentPolicyPort`, and obtains an independently verified `VerifiedIncidentApproval` through `IncidentApprovalPort`. These are ports, **not live providers**.
- The approval must bind the exact `review_id`, tenant, disposition, evidence reference and time window, and must come from another effective actor.
- The PostgreSQL `PostgresPrivilegedIncidentRepository` locks the reviewed row, verifies tenant, preserves `UNKNOWN`, refuses a late terminal DDL audit, and requires **four distinct effective persons**: original SQL actor, original discrepancy reviewer, investigator recording disposition and independent approving checker.
- The disposition can only be `ESCALATED`, `REMEDIATION_REQUIRED` or `INVESTIGATION_DOCUMENTED`. There is **no `SUCCEEDED`, `FAILED`, `CLOSED` or automatic DDL retry** in this workflow.
- Immutable migration `0007_privileged_incident_decisions.sql` adds owner-only decision evidence with one decision per review, plus a separate append-only denial stream. The denial stream uses the authenticated actor tenant even when a foreign target is requested. Neither stream contains a password or DSN field.
- An unknown or terminal-late review cannot be converted into a forged incident outcome. A real incident manager must inspect independent role state, logs and evidence before deciding subsequent actions.

## Verification contract

- Unit: identity and tenant binding, current grant, approval scope and expiry, self-approval, evidence reference binding, denial audit failure, malformed disposition and no role DDL.
- PostgreSQL 16: one append-only decision for a reviewed UNKNOWN request, no terminal DDL event invented, tenant-scoped denial, four-actor SoD, late terminal exclusion, concurrent decision uniqueness, SQL role access restrictions and checksum-preserving migration.
- Run Python 3.11 and 3.12 in GitHub Actions; retain exact-SHA links only when CI is green.

## Non-claims and residual blockers

1. **No production incident management system.** A decision is an immutable action plan and evidence pointer, not proof of incident closure, validity of the evidence, or a historical DDL success/failure. Evidence refs are external identifiers and require separate retention and access controls.
2. **No real identity/approval system or signed evidence.** Python verified dataclasses are not tokens; a trusted control-plane composition must connect AuthN, policy grants, independent approvals and SoD at runtime.
3. **No approved transactional authorization lease.** A permission/approval may change between verification and SQL decision insertion. The control-plane reviewer role/DSN is a trusted security boundary; administrators can bypass Python ports. Independent review required.
4. **No atomic cross-system guarantee.** PostgreSQL role DDL, session drains, final audit, manual decisions and external IAM policy may use different transactions/systems. There is no automated recovery, reactivation, revocation compensation or background job.
5. **No operational acceptance.** Real privileged-role separation, TLS, a vault, legal retention, attestations, signed ADRs, restores, disaster recovery and G0/G1/G2 reviews remain open.

An auditor may inspect the decision and historical `UNKNOWN` marker, but must never treat the disposition itself as a certification of the original role mutation.
