# L02-07f - Mandatory Fenced Privileged Role Service

**Status: candidate implementation, not approved.** G0/G1/G2 still require independent review and authorization decisions.

## Security objective

L02-07e supplied a PostgreSQL-local fencing primitive, but the main PrivilegedRoleService still accepted the legacy direct role operator. This was a concrete authorization bypass on the normal application path: a correctly approved request could execute SQL owner DDL without a fence. L02-07f removes this direct operator dependency from the application service.

## Delivered

- New pure application fence contract with typed PrivilegedFencePermit and FencedRoleOperation plus PrivilegedFencedExecutorPort.issue/execute. Infrastructure implements this port; application no longer imports infra.
- PrivilegedRoleService **requires** the fenced executor at construction, rejects the legacy roles= composition, enforces SoD and exact approval twice, writes durable INTENT, issues a scoped fence **only after** the final authorization check, consumes the fence around SQL role DDL and reports a separately audited SUCCEEDED / FAILED / CANCELLED result.
- The SQL adapter still guarantees one database transaction for role DDL and fence CONSUMED/evidence under a row lock. The main application service and SQL adapter now have an integrated runtime proof.
- Unit proof for fail-closed fence issuance, absence of DDL when issue fails, permit-to-request identity binding and rejection of legacy unfenced constructor.
- PostgreSQL proof of end-to-end identity, scoped permit, consumed state and immutable evidence in addition to the existing SQL contention, revocation, rollback, direct runtime-denial and no-replay tests.

## Threat model and operational gaps

- No real IdP, approval policy adapter or external revocation acknowledgment. The **local** PostgreSQL fence cannot protect against changes in IAM that have not reached the DB.
- The low-level PostgresTenantRoleOperator is still importable and an administrator with its DSN can invoke it directly. Application construction refuses it; **deployment isolation** is still required to remove the infrastructure bypass.
- The operator's post-commit session drain and separate privileged-operation terminal audit are not atomic with SQL fence consumption. An interrupted drain requires incident reconciliation; a FAILED application outcome does not necessarily prove absence of role changes.
- Issued permits are data, not authentication tokens; only trusted control-plane composition is authorized to issue.
- No privileged deployment/secret vault, schema owner isolation, independent SoD, signed ADR, C10 consumer E2E or G0/G1/G2 sign-off.

## Verification

CI should run PostgreSQL 16 and Python 3.11/3.12. Do not claim green until exact GitHub Actions runs are observed.
