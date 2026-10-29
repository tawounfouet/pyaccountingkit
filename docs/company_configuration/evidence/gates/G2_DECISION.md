# FND-C07 — G2 Technical Foundations decision dossier

**Status: PENDING_REVIEW / NO G2 APPROVAL / NO PRODUCTION SECURITY CLAIM.**  
**Review reference:** standalone recent `tawounfouet/pyaccountingkit`, [draft PR #33](https://github.com/tawounfouet/pyaccountingkit/pull/33) SHA `272d85f319219597abec845929038573b4712203`.

## Evidence qualified in CI, not signed security certification

| Subsystem | Demonstrated development evidence | Limit |
|---|---|---|
| Scope + UoW + SQL RLS | PostgreSQL 16 role/login tenancy and transaction tests, local application authorization | Production identity providers, SQL role issuance/rotation and privileged admin review absent |
| Audit / denials | Append-only SQL audit and denial fixtures; verified-principal-based durable authorization denial | Unauthenticated failures belong to independent AuthN boundary; no certified WORM/retention |
| Outbox | Immutable event source, lease token + expiration fencing, bounded retries and terminal DEAD | At-least-once, no exactly-once external effect or broker provider SLA |
| Inbox | Scoped producer/consumer/event digest dedup; shared receipt + projection SQL transaction; command-only handler facade | Not a sandbox; no external producer attestation, authoritative C10 message schema or external handler effect guarantee |
| IAM control / revocations | Signed-evidence Python verifiers, SQL local fences, durable ACK delivery and 0014 one-use independent SQL grant | A database-issued grant is **not** PostgreSQL Ed25519 verification. Requires truly isolated writer and recovery workloads, protected credentials, live IAM policy and independent revocation review |
| Migration history | Contiguous/checksum-validated 0001–0014, real 0013→0014 upgrade, injected rollback and logical dump/restore | No production PITR, full roles/grants/secrets restore, RPO/RTO or rolling N/N-1 recovery worker compatibility |
| Package | 14 SQL files identical in wheel/sdist/source, isolated wheel import | `0.0.0` nonrelease, no production publication/version contract |

**Exact code evidence:** [Python #40955190292](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190292) (**289 passed / 19 skipped per version**), [PG #40955190201](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190201) (**133 passed/version**), [migration #40955190187](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190187) (**6 passed/version**), [package #40955190309](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190309) (**success on Python 3.11/3.12**); all workflows completed SUCCESS on candidate SHA `272d85f319219597abec845929038573b4712203`.

## Security/operational findings still needing independent review

| ID | Material gate concern | Required reviewer disposition |
|---|---|---|
| G2-SEC-01 | SQL `cc_iam_recovery` direct-call bypass of 0013 fixed by 0014 one-use independently-issued grants; issuer `cc_iam_approval_writer` remains a trusted capability that itself does **not** verify a signature in SQL | Review trust boundary for compromised writer credential, actual separation/vault, signed current approvals, SoD, revocation race, direct SQL abuse and denial evidence. [Issue #9](https://github.com/tawounfouet/pyaccountingkit/issues/9) remains open |
| G2-SEC-02 | Client-set GUC spoof addressed by session-user tenant mapping candidate, but production privilege model not independently approved | Audit restricted roles, grants/SET ROLE, connection pools, credential revocation, RLS and SECURITY DEFINER functions |
| G2-C10-01 | Inbox dedup is a locally scoped illustrative projector; not a vetted external consumer | Decide whether external C10 contract is **explicitly excluded** from standalone *development* Foundation and tracked for L10, or must block G2; cannot claim external delivery/identity |
| G2-OPS-01 | 0014 recovery authorization contract intentionally breaks old recovery worker behavior even with stable procedure signature | Approve drain/rollout staging playbook; identify compatible workers and rollback boundary before live use |
| G2-DR-01 | Schema-only `pg_dump/pg_restore --no-acl --no-owner` does not restore cluster identities or secrets | Bound G2 to isolated local DB qualification, reserve PITR/production DR, verify full topo if production claimed |
| G2-OPS-02 | No production load/chaos metrics or live SLO/alerting proof | Decide bounded development acceptance vs required pre-production operational qualification |
| G2-ARCH-01 | All L02 security/ops ADRs remain candidate/proposed | Record explicit approval/exception list with owners; do not infer from CI |

## Required G2 reviewer tests / artifacts

1. Inspect SQL owner/auth topology and 0014 SECURITY DEFINER grants, including stolen recovery vs stolen approval-writer vs colluding roles, signature-validation point and grant expiry/revocation.
2. Run adversarial tenant-switch, search_path, SQL role escalation and multi-tenant pooling scenarios on representative **non-production** SQL roles; inspect exact-SHA CI and migration checksum proofs.
3. Verify independent actor and current approval **as deployed**; do not treat `VerifiedRedriveApproval` value objects or CI test fixtures as live IdP proofs.
4. Confirm Outbox/Inbox at-least-once boundary; require external producer identity/C10 schema and DLQ runbooks before consumer certification.
5. Authorize/deny the specific **standalone development** scope with named exceptions and no claims of production IAM, WORM, DR, release, or Ledger posting.

## Reserved independent review fields — intentionally unsigned

- Decision: **PENDING_REVIEW**
- Independent security reviewer: **UNASSIGNED**
- Infrastructure/operations reviewer: **UNASSIGNED**
- Review date: **NOT RECORDED**
- Reviewed exact SHA: **NOT RECORDED**
- GitHub approval / decision link: **NOT RECORDED**
- Accepted exceptions and external-dependency owners: **NONE RECORDED**
- G2 integration gate: **NOT SATISFIED**

**Not a production-ready security attestation or a G2 GO.**
