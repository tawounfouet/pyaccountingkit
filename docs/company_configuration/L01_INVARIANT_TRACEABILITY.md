# L01 - Domain Kernel invariant traceability

Date: 2026-10-29. **Status: implementation candidate, ADRs and gates unapproved**.

The canonical domain invariants are `CFG-01` to `CFG-10` in `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md`. The L01 kernel provides primitives; it does **not** implement or certify the complete business invariants.

| ID | Canonical requirement | Domain ownership and current enforcement | L01 tests / remaining work |
|---|---|---|---|
| CFG-01 | Explicit and coherent accounting scope | `ConfigurationScope` validates typed scope and rejects mismatches; `LegalEntity` checks its own scope. Membership and tenant permissions belong to L02/L03. | `test_scope.py`, `test_legal_entity.py`; external identity resolution outstanding. |
| CFG-02 | Valid normative framework per active book | `ReferenceFrameworkRef` requires code/version shape. Normative content and activation check belong to L04 with normative adapter. | `test_references_and_digest.py`; normative compatibility **not tested**. |
| CFG-03 | Account allowed in book | L05 chart/account eligibility, L10 C10 and Execution. | Not implemented in L01. |
| CFG-04 | Period allows posting | L06 period semantics; authoritative check at posting in Execution. | Only interval algebra tested in `test_intervals.py` and property tests; **not a posting permission**. |
| CFG-05 | Published configurations immutable | L01 uses frozen dataclasses. L09/L02 need published version guard and durable immutability. | `test_legal_entity.py` verifies immutable candidate revisions; no published storage. |
| CFG-06 | Resolution unambiguous | L01 intervals support overlap detection. Runtime Resolution owns resolution, L09/L10 expose data. | Temporal tests; no priority/resolver implementation. |
| CFG-07 | Historical snapshot reproducible | L01 `ContentDigest` local JSON fingerprint, L09 snapshots / L10 contract; ADR-CC-06 remains open. | `test_references_and_digest.py`; no canonical published snapshot protocol. |
| CFG-08 | Policies and rulesets compatible | L07 policy/ruleset constraints and normative validation. | Not implemented in L01. |
| CFG-09 | Unique effect per event and book | Cross-context Accounting Projection / Execution with Ledger. | Not implemented in L01; must not be assigned to Company Configuration. |
| CFG-10 | Sensitive configuration changes attributed/audited | L01 name candidate amendments require `reason`, expected revision; **not sufficient** for audit/authorization. L02 and L09 own secure auditing/approvals. | `test_legal_entity.py`; actor, append-only audit and SoD outstanding. |

## L01-07 scope decision (provisional)

`LegalEntity` was chosen over a configuration publication aggregate because it exposes identity, scope and revision invariants without pretending that L09 approval/publication already exists. It is an **L01 pure model slice** and not the L03 entity management feature. For example:

- `with_legal_name` returns a **new candidate instance** and increments revision, leaving the original unchanged.
- Revision checks are optimistic-in-memory only. They are not transaction-safe without L02 repository/UoW guarantees.
- `JurisdictionCode` checks the shape of two uppercase letters but does **not** validate actual legal jurisdictions or regulatory rules.
- `ConfigurationScope` provides an identity perimeter, not proof of membership or authorization.
- Company/legal-entity membership model is an open ADR. This provisional record must be revisited after G0 and before L03.

## Gate G1 still requires

1. Canonical repository identity and G0 decision.
2. Architecture review of the provisional model, ADR-CC-02 and ADR-CC-04.
3. CI unit **and property-based** test evidence for the exact commit SHA.
4. Independently reviewed namespace, API and error contract; no database/framework dependencies in the domain.
5. Written `G1_decision.md` with reviewer, SHA, exceptions and approval.
