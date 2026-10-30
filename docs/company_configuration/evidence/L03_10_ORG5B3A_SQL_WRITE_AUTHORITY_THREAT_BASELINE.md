# L03-10 — ORG-5b3a: SQL write authority threat baseline and cutover contract

**Status:** R&D RED-TEAM BASELINE ONLY. **No remediation or production authorization.**  
**Dependency:** [ORG-5b2b PR #46](https://github.com/tawounfouet/pyaccountingkit/pull/46), migration `0021`.  
**Tracking:** [ORG-5b #42](https://github.com/tawounfouet/pyaccountingkit/issues/42), [L03/G3 #36](https://github.com/tawounfouet/pyaccountingkit/issues/36).  
**Database:** PostgreSQL 16, tenant-bound CI roles. **No changes to migration bytes 0001–0021.**

## 1. Why evidence consistency is not evidence authenticity

Migrations `0019`, `0020`, `0021` guarantee a *matching and complete*
`request + audit + outbox` chain for the relevant organization SQL rows.
They do not prove that `actor_id` was authenticated independently or that the
SQL login was authorized to fabricate that chain. The CI `cc_runtime_a` login
currently has direct `INSERT` rights on both organization rows and evidence rows.
A stolen runtime DSN is therefore sufficient to construct a coherent but forged
Company registration with an arbitrarily asserted `actor_id`.

**Never label this role production-secure, audit-authenticated, non-repudiable,
or compliant.** `TrustedPrincipal` is an application port, not independent IAM.

## 2. Reproducible adversarial evidence

`tests/integration/company_configuration/test_l03_org5b3a_sql_write_threat_baseline_postgres.py`
provides the following explicit *current-state* checks:

| Evidence | Expected current result | Security meaning |
| --- | --- | --- |
| SQL privilege inventory for organization and evidence tables | `INSERT` currently allowed | Detects the broad-grant vulnerability |
| Forged Company registration + matching request/audit/outbox, all sent over ordinary runtime DSN | Deferred validation accepts the synthetic set | Evidence presence/consistency **does not** attest actor provenance |
| Cross-tenant insert using tenant-A login and tenant-B scope | Permission denied by RLS | Existing tenant isolation remains useful but insufficient |

The forged transaction explicitly executes `SET CONSTRAINTS ALL IMMEDIATE`
to exercise deferred checks, then **rolls back**. No fake business row,
request, audit or outbox is committed. This is a *known exposure test*, not
a security acceptance test. A future hardening change must **replace** its
positive attack assertions with denials; do not leave green tests claiming
the insecure behavior is desired.

## 3. ORG-5b3 design decision required before cutover

**Proposed architecture (ADR pending):** distinguish the **ordinary SQL runtime
caller** (no direct DML on organization/evidence), an independently authorized
**organization command executor**, and **read-only dispatcher/auditor** roles.
One app login must not be granted BOTH arbitrary business-row inserts and
arbitrary request/audit/outbox inserts.

A viable command boundary must, within **one local transaction**, validate:
1. the *trusted* tenant and caller identity, derived from an independently
   validated credential or a server-controlled database role;
2. action-level authorization, target scope, resource status, expected
   revision, immutable idempotency key and canonical request digest;
3. domain invariants and concurrency locks already established in L03;
4. the actual domain mutation plus request receipt, audit record, and
   Outbox event bound to that exact mutation.

The ordinary client must **not** be able to set an unverified `actor_id`
or to self-issue its own authorization. A `SECURITY DEFINER` wrapper that
merely accepts caller-controlled actor/audit data **does not fix the
threat**. Likewise a custom `SET` GUC, caller-supplied HMAC or role-switch
into a broad writer provides no independent proof.

If SECURITY DEFINER is chosen, pin `search_path`, fully qualify tables,
revoke PUBLIC EXECUTE, validate session identity and tenant binding, prevent
`SET ROLE` privilege escalation, and test function owner/RLS interactions.
The trusted executor credential and signing material must be provisioned
and rotated outside the runtime DSN. Database superuser/schema-owner
compromise remains a different trust boundary.

## 4. Cutover sequence and acceptance gates

| Tranche | Change | Acceptance criterion |
| --- | --- | --- |
| ORG-5b3a (this PR) | Record actual SQL grant attack surface and executable exploit proof | Exact-head CI shows the risk without persisting forged rows |
| ORG-5b3b | Choose ADR and implement the independently authorized command boundary, scoped initially to Company registration | Ordinary runtime login CANNOT directly INSERT either business or evidence rows; forged full triple denied |
| ORG-5b3c | Migrate Establishment, LegalIdentifier, Company/Establishment lifecycle and Membership to the same authority model | All six command families preserve authorized positive + replay/rollback/concurrency; hostile DSN rejects |
| ORG-5b3d | Remove old broad grants in explicit deployment/role provisioning cutover, test old/rotated/revoked credentials | No deprecated credential/GRANT bypass; rollback and DR/recovery evidence |
| G3 | Cross-slice qualification and merge review | PR HEAD and eventual main SHA, real CI, no artificial stable release |

**Security gate is DENY on direct SQL**, not just COMMIT consistency of rows
that the same login has been allowed to manufacture. Do not close issue #42
or L03/G3 #36 at this baseline checkpoint.

## 5. Architecture compatibility

- **Company Configuration** owns organization identity and configuration,
  not Ledger entries; `Runtime Resolution`, Projection and Execution
  remain independent bounded contexts.
- Preserve `MembershipId`-native evidence from `0021`; never revert to
  ambiguous `LegalEntityId` receipts.
- Migration history remains immutable and additive. Do not retroactively
  edit `0001..0021`; stage role/privilege changes explicitly.
- Keep `as_of` and `known_at` separate. Do not infer capital control or
  legal succession from organization membership.
- Tests against disposable CI role credentials are **R&D only**, not
  validation of a real identity provider, external register, or production
  compliance.

## 6. Qualification procedure (this PR)

Validate exact PR HEAD on Python 3.11 and 3.12:
`Python CI`, `PostgreSQL integration`, `Company Configuration migration
recovery`, and `Standalone Foundation package & integration`.
Review failing tests as evidence, not as permission to silently weaken
existing constraints. Until those four runs are green, this branch remains
**draft, unqualified**.

## 7. Risk statement

Current SQL tenant isolation prevents *cross-tenant* arbitrary inserts.
It **does not prevent a compromised same-tenant runtime credential from
manufacturing complete, internally consistent organization history and audit
evidence**. This is a tracked P0 architectural gap. ORG-5b3a makes it
reproducible but does not remove it.
