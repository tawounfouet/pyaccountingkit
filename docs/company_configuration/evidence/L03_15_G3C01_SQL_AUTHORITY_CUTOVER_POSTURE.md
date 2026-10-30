# L03-15 — G3-C01 SQL authority deployment posture and consolidation readiness

**Status: R&D gate candidate — not production IAM accreditation or full G3 acceptance.**

Depends on the SQL migration series 0022–0025 in the stacked organization L03 PRs #49, #50, #52, #54. Parent trackers #36, #42 and #48. Scope issue #55.

## 1. Previously unverified deployment gap

The issuer split was developed and live-qualified with **ephemeral CI SQL roles only** in `scripts/setup_postgres_ci.py`. Until G3-C01, each role-family had its own transaction and denial tests, but no single fail-closed gate verified that a given deployment had installed **all four SQL authorities simultaneously**, with their exact tenant bindings, enabled guards, FORCE RLS and non-impersonation.

The 0022–0025 SQL migrations define the stored functions and owner-managed issuer tables. They do **not** provision, distribute, rotate or secure production role credentials. Schema-owner and superuser operations remain outside this check.

## 2. New read-only check

`scripts/verify_org_sql_authority.py` is an explicitly configured SQL posture auditor, not a deployer. It only reads `pg_catalog`, `tenant_role_bindings` and the four owner-managed issuer policy tables. The auditor requires an independent connection with sufficient read permissions; `CC_PG_ADMIN_DSN` is an environment variable for CI compatibility and should **not** be reused by an application worker.

Inputs are the **real expected login identities and tenants**, never guessed from the database:

- `--runtime ROLE:TENANT` repeated once per tenant
- `--issuer company:ROLE:TENANT`, `registry:...`, `lifecycle:...`, `membership:...`, exactly once for each family per tenant

The check refuses missing tenants, missing roles, duplicates, shared issuer/runtime logins, and arbitrary additional issuers in the submitted topology. It then tests:

1. Every login has `LOGIN`, `NOINHERIT`, `NOSUPERUSER`, `NOCREATEROLE`, `NOCREATEDB`, `NOBYPASSRLS`.
2. Each login's owner-managed `tenant_role_bindings` equals its declared tenant; issuer allowlist is **enabled**, same tenant and same original SQL login. No caller can mutate those owner-managed policy tables.
3. Ordinary runtime has no direct `INSERT` on domain registration, lifecycle and membership tables and no direct INSERT on lifecycle or membership evidence; issuer has no direct INSERT on **any** organization target/evidence table, including column grants.
4. Shared registration request/audit/outbox may still have legacy runtime INSERT grants **only while BOTH** Company and Registry target-kind INSERT triggers are present and enabled. All other tables require their issuer INSERT trigger; all 15 target/evidence tables must have FORCE RLS.
5. Every controlled SQL function and underlying SECURITY DEFINER guard must have pinned `search_path`, no `PUBLIC EXECUTE`, and authority-check SQL must refer to `session_user` and `bound_tenant()`.
6. Only the designated issuer family has EXECUTE on its SQL commands; ordinary API runtime and other issuer families may not execute them; no runtime may `SET ROLE` into an issuer.
7. No runtime or issuer can perform `UPDATE`, `DELETE` or `TRUNCATE` on these evidence/domain tables.

**FAIL is the default** if the connection/permissions, catalog, binding, trigger, function, ACL or input cannot be verified. The CLI does not log DSNs, read production credentials other than using its own read-only connection, or mutate database state.

## 3. CI and negative controls

The PostgreSQL 16 CI runs the auditor after creating ephemeral test roles and after existing integration tests. A dedicated integration test also verifies the full topology and negative controls:

- issuer allowlist switched to `enabled=false` *inside a transaction*: detection must fail and changes are rolled back;
- `organization_command_requests` Registry guard disabled *inside a transaction*: detection must fail and changes are rolled back;
- an operator-declared tenant-to-issuer role swap: detection must fail without changing SQL.

Python-only unit/qualification tests exercise parsing/completeness with no PostgreSQL connection. The original migration bytes 0001–0025 are unchanged. The existing four workflows (Python, PostgreSQL, recovery, wheel/sdist) and Python 3.11/3.12 matrix still apply.

## 4. Operator runbook (safe by default)

Before any production promotion:

1. Stop ordinary organization mutation traffic and inventory all real API SQL logins and issuer logins per tenant. Do not store passwords or DSNs in repository files or PR comments.
2. Provision independent SQL issuer credentials with a deployment/IAM workflow **outside `setup_postgres_ci.py`**. Do not run that CI fixture in production.
3. Apply reviewed migrations 0022–0025 via controlled schema owner migration account. Assign only required per-family SQL EXECUTE plus tenant-scoped SELECT for receipt/parent read and COMMIT proof. Revoke direct legacy ordinary SQL INSERT on target/evidence as specified; retain the documented shared registration evidence grants only under both enabled guards.
4. Give a separately provisioned **read-only** auditor connection SELECT on owner-managed binding/issuer tables plus pg_catalog visibility. Pass exact expected role bindings on CLI and set `CC_PG_ADMIN_DSN` through an appropriate runtime secret provider; run `python scripts/verify_org_sql_authority.py --runtime ... --issuer ...`.
5. Record the command's **exit code, sanitized findings, migration digests, PostgreSQL version, tested topology, cutover timestamp and exact application commit** in a separately controlled evidence store. Exit code 0 means **database SQL posture passed**, *not* that user identities have been independently authenticated.
6. Keep traffic closed if any check fails. Restore privileges and issuer bindings through authorized change management, then rerun auditor and rollback/recovery scenarios before opening traffic.

## 5. Known non-goals and remaining blockers

- This is a **declared-role topology audit**, not discovery of every possible hidden database login; a separate owner-signed inventory and grants review must attest the supplied role list is exhaustive.
- Trigger/function text inspection is a defense-in-depth static indicator, not a formal proof of SQL semantic equivalence; migrations, role ownership, supply chain, and superuser privilege separation need independent review.
- A valid issuer still passes arbitrary `actor_id` and action in its command parameters. Real human IAM authentication, action-specific authorization, incident revocation, issuer credential sequestration and external audit append-only guarantees remain **OPEN**.
- A stolen issuer login can make authorized-looking changes. The script does not test a production connector, secret rotation, authentication ceremony or operations access boundaries.
- No claim that G3 is complete on `main`, no merge of the stacked L03 PRs and no published/stable version from this R&D qualification alone.
