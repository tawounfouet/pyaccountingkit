# L03-19 — G3-C02b3a Cross-family Signed Gateway SQL Qualification and Revocation Race

**Status:** R&D evidence candidate, exact-head CI qualification required. Tracks [#63](https://github.com/tawounfouet/pyaccountingkit/issues/63), upstream G3-C02a [#58](https://github.com/tawounfouet/pyaccountingkit/pull/58), durable nonce [#60](https://github.com/tawounfouet/pyaccountingkit/pull/60), signed live grant adapter [#62](https://github.com/tawounfouet/pyaccountingkit/pull/62).

## 1. Problem and objective

Before this increment, only `RegisterCompany` had a complete CI-controlled path **Ed25519 signed actor/typed command → independently signed mocked HTTP grant → PostgreSQL durable nonce → existing DDD service → SQL issuer-only command → atomic request/audit/outbox**. The six other routes were mapped in the gateway but lacked executable proof with real SQL issuers.

This slice adds a **single controlled PostgreSQL 16 integration harness** executing the seven DDD action types, with independent, tenant-bound SQL credentials for each of the four business-issuer families:

| Signed organization operation | SQL authority | Transactional evidence |
|---|---|---|
| `organization.company.register` | Company writer | `organizational_companies`, organization request/audit/outbox |
| `organization.establishment.register` | Registry writer | `organizational_establishments`, organization request/audit/outbox |
| `organization.legal_identifier.register` | Registry writer | `organizational_legal_identifiers`, organization request/audit/outbox |
| `organization.company.transition` | Lifecycle writer | `organizational_company_revisions`, lifecycle request/audit/outbox |
| `organization.establishment.transition` | Lifecycle writer | `organizational_establishment_revisions`, lifecycle request/audit/outbox |
| `organization.membership.assign` | Membership writer | `organizational_membership_revisions`, membership request/audit/outbox |
| `organization.membership.end` | Membership writer | New membership revision, membership request/audit/outbox |

The sequence establishes its own typed Company and LegalEntity prerequisite fixtures; the seven operations themselves are executed only through the signature-checking gateway and the correct SQL issuer credential.

## 2. Test invariants and adversarial signals

- For each action, an **ephemeral** Ed25519 command signer provides a short-lived signed actor/tenant/action/target/request/correlation/digest/JTI; the real `PinnedOrganizationCommandVerifier` is used.
- A **separate** ephemeral test IAM decision key signs the actual `HttpsSignedOrganizationGrantSource` request using an injected HTTP provider **stub**. Signed challenge, actor and command identity are verified; no real third-party IdP is contacted.
- `PostgresDurableCommandNonceStore` accepts one JTI on a tenant-bound SQL consumer account, commits the JTI independently, then the real DDD application service uses a **different** SQL business writer.
- Each command's first successful operation increments the target write and exactly one request/audit/outbox, a spent signed JTI is denied without new SQL, and a *fresh* signed JTI with an unchanged business request ID returns the original receipt without duplicate business evidence.
- A signed **revoked** decision is denied before SQL and before consuming any JTI.
- A signed **mismatched action** is denied before the live IAM request, nonce and business SQL.
- Existing migrations 0001–0026, RLS/FORCE RLS, four SQL issuer policies, transactionality, server-side guard and public grants remain unchanged. The CI-only test signing keys and IAM grant decision stubs **are not deployable credentials**.

## 3. Explicit TOCTOU observation

A second real SQL integration test deliberately toggles simulated IAM revocation **after an authorized signed decision**, inside a SQL command's injected `before_commit` hook, **before transaction COMMIT**. The existing software may still commit successfully because its IAM validation happened before SQL and no commit-time external IAM fence exists. This is a **known, measured residual exposure**, not evidence of successful instantaneous revocation.

The next design must select one of:

1. Trusted SQL transaction-bound authorization fencing backed by an independently maintained grant/revocation epoch that is checked at the authoritative write boundary, including documented propagation/delivery SLAs.
2. A policy-approved bounded exposure window (with revalidation immediately before commit, strict TTL and audit) if true cross-system atomicity is impossible, with measured worst-case timing.

Without real independent IAM ownership, **do not invent a revocation-at-commit guarantee**. Rechecking a test mock in the same application process is not authoritative production revocation.

## 4. What is not proven

No live IdP, signed-grant custody from a real provider, independent gateway deployment, encrypted secret injection/isolation, production network restrictions, current IAM grant propagation SLA, independent cryptographically linked actor provenance in SQL, or external C10 accounting event delivery. The tests create their signed attestation and IAM decision keys in **test code only**. A compromised independently privileged SQL issuer remains privileged, subject to PostgreSQL grants and its owner-maintained tenant binding.

**G3-C02b #59, G3-C02b3 #63 and G3 #36 remain OPEN**. A green R&D CI must not be described as production certification, `main` merge or stable release.
