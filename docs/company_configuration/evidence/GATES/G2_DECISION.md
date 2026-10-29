# G2 — Technical Foundations / security / durability decision

**Decision:** PENDING_REVIEW / NO SECURITY GO SIGNED.  
**Reviewer:** NOT ASSIGNED. **Approved SHA:** NONE.  
**Target:** [PR #32](https://github.com/tawounfouet/pyaccountingkit/pull/32) in recent standalone repo. **Historical reconciliation deferred**.

## Technically qualified evidence — 2026-10-29 checkpoint `098f6de80b916d0545b65c2dfec9357f854cddcd`

| Subject | Proved in automated CI | Not proven |
|---|---|---|
| SQL transactional UnitOfWork, audit/outbox atomicity, optimistic writes and idempotency | [PG CI #40954760659](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760659): 136 passed per Python 3.11/3.12 | Finance/ledger posting contract, live load/SLO |
| SQL tenant isolation via server-bound session_user; denial audit; role privilege negatives | PG tests in L02-05 and later | Independent production IAM, protected credentials, cross-boundary pen test |
| Independent SQL approval-writer ticket for DEAD IAM acknowledgement redrive | FND-C03 one-use `0014`; expired/mismatched/forged recovery-only requests denied | Approval writer compromised/collusion, live signed IdP/PAM and vault/network |
| Migration integrity, 0013→0014 upgrade, rollback-on-failure, restore | [Recovery CI #40954760543](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760543): 6 passed/version | Real PITR, roles/grants/secrets, RPO/RTO, live operational recovery |
| Outbox bounded leased at-least-once and local transactional Inbox dedup | FND-C05 negative tests + full PG CI | Real broker and C10 consumer / Ledger E2E, global exactly-once |
| Package resource integrity | [Artifact CI #40954760631](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760631): wheel/sdist, 14 SQL hashes, clean import | Public stable release/canonical cross-repo compatibility |

Python unit suite [#40954760622](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760622): 289 passed / 18 skipped per supported Python version, Ruff green.

## Open threats and operational blockers (fail closed)

1. **Independent security review is missing.** Issue [#9](https://github.com/tawounfouet/pyaccountingkit/issues/9) remains open. Migration 0004 changes tenant RLS to server-authoritative roles, but independent credential/proxy/tenant provisioning verification and offensive test review are not signed.
2. **One-use IAM ticket is only a limited defense.** Holder of `cc_iam_recovery` *alone* cannot bypass the approved ticket. The distinct `cc_iam_approval_writer` must run in a separately controlled workload with signed, current independent approval source. SQL itself does NOT verify Ed25519; colluding/stolen writer credentials and admin/superuser bypass remain outside its tested boundary. Do not place both secrets in one runtime.
3. **Time-of-check and external revocation** of signed approvals/grants and post-commit IAM ACK: live provider/issuer evidence, signer custody, key rotation, revocation races and independent audit trust still require deployment design and validation.
4. **Migration 0014 is behaviorally breaking** for legacy recovery workers despite unchanged SQL signature. Require drain, protected writer provisioning, staged upgrade and cutover test; do not promise N/N-1 recovery interoperability.
5. **Operational restore is incomplete:** local `pg_dump/pg_restore` tests exclude globals/roles/secrets and do not establish PITR/RPO/RTO or offsite backup compliance.
6. **External producer/consumer trust:** broker authentication, published schema/versioned C10 consumer contract and transactional side-effect ownership are not qualified by sample Inbox projections.
7. **Authorization and incident/runbook governance:** production per-tenant DB identity/connection pools, on-call security approvals, incident decision evidence, DLQ replay and least-privilege deployments need recorded review.

## G2 acceptance conditions

- Independent security and SQL role threat review, with artifacted actor, signed decision, scope, timestamp and current PR SHA.
- Architecture/risk owner explicitly accepts what *development-only* Foundation excludes, **without** treating mocked IAM or CI role tests as deployed production controls.
- All G0/G1 decisions approved, all four workflows green at current exact PR SHA, migration and release topology checked.
- Any merge decision must name whether G2 GO is **development-only** and explicitly forbid deployment of unqualified privileged functions or external connections.

**Verdict:** technical implementation has CI evidence, but **G2 PENDING_REVIEW**. No authorization to claim production-ready controls, stable package or Foundation closure.
