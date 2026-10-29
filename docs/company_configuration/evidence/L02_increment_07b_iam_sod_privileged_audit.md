# L02-07b - Privileged Role Operations: authorization, SoD and append-only audit

**Status:** candidate implementation, not approved G0/G1/G2. The code works with a **trusted** external identity/approval/policy implementation; it does **not** implement a production IAM, authenticated approval workflow or maker/checker platform.

## Source and intent

Based on `19_COMPANY_CONFIGURATION_SECURITY_AUTHORIZATION_AND_AUDIT_MODEL.md`: RBAC/ABAC/ReBAC policy is server-side; client claims do not confer privileges; SEC-06 strict separation of effective identities; SEC-10 audit of critical mutations; SEC-15 no secrets in audit; denial audit is independent of a rejected mutation; audit unavailable blocks the critical operation. These are **candidate** product security requirements, not proof of policy acceptance.

## Boundary and flow

- `OperatorIdentityPort.verify(opaque_context)` returns a `VerifiedOperator`. Only a real external AuthN adapter may create verified identity. A plain dataclass or raw API JSON is not authentication.
- `PrivilegedPolicyPort.require()` asks a trusted policy decision provider for the current operator grant on the target tenant/role/action. Default deny is mandatory in the adapter. This candidate has test fakes only.
- `ApprovalVerificationPort.resolve(reference)` obtains an independently verified, nonexpired approval matching the *exact* request UUID, tenant, SQL login, action and approval reference. The approver actor ID must differ from the executing operator actor ID even if either actor has multiple roles.
- A denied verified actor is recorded to a separate owner-only audit connection, tagged with the authenticated tenant (never a requested foreign tenant). If this audit is unavailable, the operation remains denied.
- On valid authorization, a committed append-only `INTENT` event is required *before* the privileged role operator runs; the UUID intent index prevents reuse of the same request ID as a new mutation.
- Afterwards, `SUCCEEDED` or `FAILED` is appended to the journal. Failure to persist the completion evidence raises `PrivilegedAuditIncomplete` and MUST trigger operational reconciliation, **not** a success response. `FAILED` means the operator reported an exception, not proof the underlying DDL had no side effects.
- PostgreSQL schema-owner-only `privileged_operation_audit` table, versioned migration `0005`, protected update/delete trigger and no grants to runtime/dispatcher/Inbox roles. No password/DSN/token is ever written by this component.

## Explicit limits and unresolved risks

- Critical DDL, backend/session termination and final audit **do not share one atomic transaction** in this initial integration. A crash after role mutation can leave an INTENT without a final outcome; reconcile on restart. This does not meet a fully atomic privileged mutation+audit guarantee.
- PrivilegedRoleService is a *composition boundary*: direct access to `PostgresTenantRoleOperator` and the admin DSN bypasses it. A production deployment MUST isolate the owner role and expose only the IAM-protected service. No deployment proof exists.
- The trusted identity and approval adapters are stubs/ports, not provider implementations. Real identity, revocation race checks, approval signatures/digests, immutable approval repository, actor/grant lookup, SoD verification and MFA still need operational qualification.
- A Python `VerifiedOperator`/`VerifiedApproval` instance alone can be constructed by arbitrary Python code: it is not a security token and must never be accepted as a proof from a caller. Verify inside a trusted adapter, constrain who calls the service.
- Administrative password DDL may appear in PostgreSQL statement logging. A production vault, no-sensitive-SQL-logging policy, secure TLS, controlled rotation, approval expiration/reuse checks and secret custody remain critical blockers.
- Audit append-only trigger is not a WORM guarantee. Schema owner/superuser controls remain trusted; no independent cryptographic integrity, retention policy or export validation yet.
- Authorization policy is only checked before INTENT, not atomically again with role DDL; revocation/approval race and locking policy require a separate ADR and tests.
- No C10 consumer proof, no Ledger posting, no approved G2 and no published stable release.

## Qualification contract

- Pure Python test suite: successful approved rotation, self-approval denied, binding/expiration mismatch, tenant denial audited under verified tenant, permission revocation, audit outage, failed operator, missing outcome evidence, replay and opaque AuthN context.
- PostgreSQL tests: committed intent+outcome, protected immutable audit, denied SoD without changed credentials, globally unique request ID, rejected direct runtime role and failed-role mutation outcome.
- Run both Python 3.11 and 3.12 and PostgreSQL 16. Only attach exact SHA and Actions URLs after observed success; preserve PR as **draft**.

## Next increments

Formalize an approved SoD/approval policy and integrate a real IAM/IdP + vault; implement a least-privilege administrative control plane with audited policy decisions, an independently verifiable actor-to-request binding, reconciliation of `INTENT` entries missing outcomes, and safe secret rotation without password-bearing SQL logs. Finish G0/G1 baseline and independent G2 security review.

## Exact-SHA automated evidence

Implementation commit `e2414cca16b8c175abba70de5820962a7c4e418b` passed:
- [PostgreSQL 16 CI #40874962870](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40874962870): **53 integration tests passed** on Python 3.11 and **53 passed** on Python 3.12; Ruff checks succeeded. Seven new PostgreSQL privileged-operations tests are included.
- [Python CI #40874963079](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40874963079): **125 passed and 7 PostgreSQL-only skipped** on each Python 3.11 and Python 3.12; Ruff passed. Seventeen new pure-Python SoD/authorization tests are included.

The tests qualify this candidate only. PostgreSQL role mutation, backend drain and final audit are not a single transaction; an external IAM and independent approvals remain integration gaps. No signed G2 decision, no production deployment acceptance, no G0/G1 sign-off or stable release.
