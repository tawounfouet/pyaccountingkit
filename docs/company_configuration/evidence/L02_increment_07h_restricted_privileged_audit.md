# L02-07h - Dedicated Privileged Audit Writer & Restricted Composition

**Status:** technical candidate, G0/G1/G2 and security review NOT APPROVED. Migration 0010; migrations 0001-0009 unchanged.

## Security problem

L02-07g delegated the SQL role modification through `cc_control_plane`, a restricted `LOGIN` with only three narrow `SECURITY DEFINER` functions. The normal privileged service still needed `PostgresPrivilegedAudit(ADMIN)`, however, exposing a PostgreSQL schema-owner credential in the same runtime composition. This preserved an owner-level bypass despite restricted role-operations SQL.

## Implemented narrow boundary

- SQL migration `0010_delegated_privileged_audit.sql`: one owner-managed `SECURITY DEFINER` entry point `cp_append_privileged_audit`, fixed `search_path`, revoked PUBLIC grants, strict per-phase validation. For a terminal outcome the function reads the original, exact-scoped INTENT and copies the server-owned approval identity, rejecting actor/tenant/request/role mismatches.
- **SUCCEEDED is refused without an exact matching consumed SQL fence**. This does not certify backend drain or an external incident closure; the historical role DDL and terminal evidence still span separate transactions.
- A dedicated ephemeral test login `cc_privileged_audit` cannot access privileged tables, issue/revoke/consume fences, or ALTER ROLE. Conversely, `cc_control_plane`, runtime, dispatcher and Inbox must not execute the audit function.
- `DelegatedPrivilegedAudit` implements the existing application audit port with **no owner DSN** and a redacted representation. The database assigns its own `recorded_at` clock, rather than blindly persisting client timestamps.
- `build_restricted_privileged_service()` checks the authenticated SQL login and privilege grants for **both** independently provisioned credentials before constructing `PrivilegedRoleService`, `DelegatedPrivilegedAudit`, and `DelegatedPrivilegedControlPlane`.
- PostgreSQL tests: role/capability confinement, denial persistence, duplicate INTENT and outcome rejection, no success without consumed fence, actor/tenant mismatch, rejection of forged self-approval, end-to-end service with only restricted DSNs, and rejection of admin/swapped/runtime DSNs.

## Threat model and remaining blockers

1. **DB owner is still trusted.** The schema owner/superuser and legacy raw `PostgresTenantRoleOperator(admin_dsn)` remain available to an independently privileged caller. `SECURITY DEFINER` and owner-only tables are not externally attested WORM evidence.
2. **No signed IAM authorization:** the audit and fence functions accept actor/checker values supplied by their callers. An external IdP, authorization decision signing, SoD, lifecycle revocation propagation and PAM remain absent.
3. **No deployed service segregation:** separate SQL logins plus a composition check are a database capability boundary, not an isolated service/network, workload identity, secret vault, mTLS or production admission control.
4. **Audit and DDL are not globally atomic.** INTENT and SUCCEEDED/FAILED/CANCELLED are separately committed; if post-role DDL session termination fails, the outcome remains ambiguous and must be reconciled.
5. **Operational controls** including backup/restore, owner credential custody, SQL password statement logging, retention, independent audit reviewer and G0/G1/G2 approvals require separate evidence.

## Verification

Exact implementation SHA `3025731bdacb2b833291930141ce7322fd9eb7fa` passed:

- [PostgreSQL CI #40918911563](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40918911563): **98 integration tests passed** per Python 3.11 and 3.12, including 8 newly added restricted-audit tests; Ruff green.
- [Python CI #40918911446](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40918911446): **169 passed, 12 PostgreSQL integration modules skipped** per Python version; Ruff green.

This is an ephemeral CI role capability proof, not a deployed protected control-plane process or external audit custody. No approved G0/G1/G2, no stable release.
