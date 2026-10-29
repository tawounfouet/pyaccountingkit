# Company Configuration - provisional foundation architecture decisions

Status: **PROPOSED, NOT APPROVED**. Scope: first L01 increment, before L02 database design.

1. **Package placement:** `src/pyaccountingkit/company_configuration/domain/shared/`, reusing the planned bounded context hierarchy. The current repository has no preexisting shared kernel to reuse; consolidation with other historical codebases remains an explicit G0 task.
2. **Runtime-typed identities:** frozen UUID wrappers distinguish `CompanyId`, `LegalEntityId`, `AccountingBookId`, `ConfigurationDraftId` and `ConfigurationVersionId`. Parsing from strings is explicit and canonical.
3. **Tenant and accounting scope:** `ConfigurationScope` requires tenant, company and legal entity, with an optional typed book. This is an identity/shape invariant, **not** proof of membership or authorization; L02 must validate actual scope against the authoritatively loaded resource.
4. **Temporal semantics:** `EffectiveInterval` uses calendar `date`; `KnowledgeInterval` uses timezone-aware `datetime`. Both intervals are half-open (`[start, end)`). No fallback to current versions is allowed. This choice requires reconciliation with canonical ADR-CC-04.
5. **Normative ownership:** `ReferenceFrameworkRef` has an explicit version; it cannot validate external normative content (L04). No embedded standard or IFRS chart of accounts.
6. **Digest:** `ContentDigest.from_canonical_json` is a small deterministic local helper, **not** an approved publication protocol. ADR-CC-06 must decide schema canonicalization and cross-language interoperability.
7. **L02 blockers remain open:** DB/storage architecture (ADR-CC-03), publication atomicity (ADR-CC-05), authorization/SoD (ADR-CC-08), and migration topology must be decided before implementing durable writes.

**No decisions above are a substitute for a recorded architectural sign-off.**
