# FND-C04 — PostgreSQL Migration, Integrity, Recovery and Deployment Qualification

**Date:** 2026-10-29  
**Project:** standalone recent `tawounfouet/pyaccountingkit` only.  
**Status:** **CI-qualified development evidence**, **G2 NOT APPROVED**, **not a production DR or N/N-1 approval**.  
**Feature PR:** [#29 — FND-C04 Migration & Recovery](https://github.com/tawounfouet/pyaccountingkit/pull/29) (stacked on FND-C03 #28).

## Scope and immutable migration source

The append-only SQL files `0001`–`0014` are not changed by FND-C04.

The migration runner is strengthened to:
1. Require contiguous unique numeric source ordinals beginning with `0001`.
2. Reject already-applied migration filenames unknown to the currently installed code (**newer DB / older migrator fail closed**).
3. Reject gaps or non-prefix applied history.
4. Check *all* previously applied file checksums **before executing any new migration**.
5. Preserve transactional advisory lock, atomic SQL migration + ledger row, and idempotent reruns.

**Upgrade is forward-only.** Deleting a migration ledger row, editing historical SQL or silently rolling back schema changes is prohibited.

## Exact-head executable proof

The implementation candidate `3f924d4450efe897f2f3847d4998a7fa905f797b` completed the following 2026-10-29 GitHub Actions runs:

| Workflow | 3.11 | 3.12 | Source |
|---|---|---|---|
| Python unit + Ruff | **287 passed / 18 skipped** | **287 passed / 18 skipped** | [Python CI #40951816972](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40951816972) |
| PostgreSQL 16 integration + Ruff | **129 passed** | **129 passed** | [PG CI #40951816943](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40951816943) |
| New isolated migration qualification + Ruff | **6 passed** | **6 passed** | [FND-C04 CI #40951817081](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40951817081) |

The dedicated test file is `tests/qualification/test_company_config_migration_recovery.py`. Each test creates and deletes its own isolated database on the ephemeral PostgreSQL 16 service, using administrator credentials supplied **only by CI**.

### Proven scenarios

| Scenario | Executable check | Result |
|---|---|---|
| Upgrade existing `0013` deployment | Apply real 0001–0013 bytes, persist a legal entity and signed-revocation receipt + DEAD queue event, run normal migrator to apply only 0014, check checksum prefix, data unchanged and idempotence | **PASS** |
| Fault mid-upgrade | Introduce synthetic 0015 containing DDL then raised SQL exception; verify no partially committed table/ledger row; rerun original sources | **PASS** |
| Future schema | Insert unknown 0015 history row; rerun older migrator | **Fail closed (test PASS)** |
| Missing migration history | Remove a middle ledger record and rerun | **Fail closed (test PASS)** |
| SQL checksum drift | Modify a copy of already-applied 0013 bytes; rerun with modified resource inventory | **Fail closed (test PASS)** |
| Concurrent initial migration | Two independent migrator threads race over one new DB; advisory lock serializes, one applies 14, other 0 | **PASS** |
| Logical backup & restore | `pg_dump -Fc` schema, `pg_restore --no-owner --no-acl` into a second clean DB, compare all 14 history hashes, legal entity and DEAD IAM receipt/queue state, trigger presence and idempotence | **PASS** |

## Important incompatibility: 0013 → 0014 authorization semantics

The SQL signature `cp_redrive_dead_iam_ack(uuid,uuid,text,text,text,text,text,text)` remains unchanged, **but the authorization contract is stricter**:
- With 0013, the recovery account can call the procedure directly using caller-provided actor/checker strings.
- With 0014, a **matching, unexpired, one-use authorization issued by an independent `cc_iam_approval_writer`** is mandatory. Old recovery applications that do not obtain the ticket **fail closed**.
- Therefore **do not claim rolling N/N-1 compatibility for IAM ACK recovery**. Treat the change as an intentional breaking operational behavior, even though the SQL function signature and data schema are forward additive.

### Proposed controlled deployment sequence (NOT executed in a live environment)

1. Inventory running recovery workers, lease/queue state, approval sources and connection pools. Take an independent, encrypted, verified backup; capture existing migration hashes and roles/grants.
2. **Quiesce and drain old recovery workers**, disabling direct manual redrive. Normal ACK delivery may continue only after separate compatibility review.
3. Deploy signed-approval issuer in a truly independent protected workload and provision `cc_iam_approval_writer` credential with separately controlled vault access. Verify signer, current IAM grant, SoD, idempotency/revocation and audit policy.
4. Apply migration 0014 via schema-owner pipeline, after verifying all 0001–0013 historical hashes. Verify role EXECUTE grants and SQL session identities.
5. Deploy the 0014-aware recovery application and validate a scoped incident in a staging environment; separately test expired, replayed, cross-tenant and direct-SQL bypass attempts.
6. Verify outbox claims, incidents, audit/authorization evidence and application metrics. Restore or roll back **application traffic** only to a version compatible with 0014; do **not** destructively down-migrate a security-critical SQL schema without a separately reviewed plan.
7. Store deployment SHA, backup verification, incident/rollback runbook, actual actor/reviewer sign-offs and timing evidence.

## Logical backup versus disaster recovery

The CI proof is a **schema-scoped logical dump/restore** and verifies database objects and selected data. It does **not** verify:
- Global PostgreSQL roles, owners, grants, certificates, cluster configurations, extensions, secrets, identities or external IAM evidence sources. In particular, using `--no-acl` deliberately does **not** restore production role assignments.
- Physical backup, WAL/PITR, encrypted offsite retention, point-in-time restoration, backup age/immutability, disaster failover or KMS/vault restoration.
- A production-equivalent topology, concurrent live writers during backup, data growth/throughput, RPO/RTO, provider acknowledgement or operational time budgets.

Before production deployment, restore **a full representative environment** (data + global role topology + secrets + external dependencies), independently audit access restrictions, rehearse failover and quantify achievable recovery objectives.

## Gate effect

- **FND-C04 deterministic migration safety and isolated logical restore: CI-QUALIFIED.**
- **FND-C04 production restore/DR and N/N-1 operational compatibility: OPEN.**
- **G2: NOT APPROVED** pending independent security review, production IAM writer separation, FND-C05 contracts/reliability, formal ADR and gate evidence.
- **G0/G1:** prior review state unchanged.
- **PR #27/#28/#29:** draft/unmerged. No stable release or main-branch qualification inferred.
