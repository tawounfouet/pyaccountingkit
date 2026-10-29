# G1 — Domain Kernel independent qualification decision

**Decision:** PENDING_REVIEW. **Reviewer:** NOT ASSIGNED. **Approved SHA:** NONE.  
**Target:** recent repo standalone Domain Kernel L01 on [PR #32](https://github.com/tawounfouet/pyaccountingkit/pull/32).  
**Automated checkpoint:** `098f6de80b916d0545b65c2dfec9357f854cddcd`; current PR head must be requalified separately.

## Contract inventory and executable evidence

| Invariant/ownership | Implementation | Existing proof |
|---|---|---|
| IDs not interchangeable at runtime, canonical UUID parse | `domain/shared/identifiers.py` | `tests/unit/company_configuration/test_identifiers.py` |
| Explicit nonblank tenant, typed company/entity/book, no implicit current scope | `domain/shared/accounting_scope.py` | `test_scope.py` |
| Business effective interval is half-open on `date`, rejects invalid bounds | `domain/shared/effective_interval.py` | `test_intervals.py` |
| Knowledge instant is timezone aware, half-open, compared in UTC to distinguish DST `fold` | `domain/shared/effective_interval.py` | PR #3 DST backport plus `test_intervals.py` |
| Typed currency/jurisdiction/normative reference syntax, digest construction | `domain/shared/references.py`, `digest.py` | `test_references_and_digest.py` |
| LegalEntity scoped stable id, immutable revision, guarded `with_legal_name` | `domain/organization/entities.py` | `test_legal_entity.py` |
| No domain infrastructure import, application only depends inward on interfaces/domain | AST dependency boundary checks | `test_architecture.py` |

- Python unit/property suite [#40954760622](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40954760622): **289 passed, 18 skipped per Python 3.11/3.12**, Ruff green.
- Domain kernel configures, but **does not post accounting entries**, grant membership, activate books or validate external normative standard truth. These are subsequent bounded context responsibilities.

## Outstanding review questions

1. **Equality/key ownership:** `LegalEntity.__eq__/__hash__` use `(tenant_id, entity_id)`; `ConfigurationScope` also carries a `company_id`. PostgreSQL `legal_entities` primary key is `(tenant_id, entity_id)`. Confirm tenant-global legal-entity UUID semantics, or change domain+schema identity together **before signing G1**. Do not silently redefine business identity in this gate.
2. **Digest serialization:** digest is deterministic local JSON, *not* a cross-language or published C10 canonical representation.
3. **Temporal ownership:** date vs instant intervals, no implicit current fallback, storage and current vs historical resolution responsibilities require normative ADR sign-off.
4. **Entity lifecycle:** no full L03 organization/membership validity; ensure no API or docs imply those transitions exist.
5. **Error semantics:** confirm stable typed error categories and scope information leak policy before consumer contract publication.

**Conclusion:** coding and test evidence exists; **G1 remains unapproved** pending independent contract/ADR review and a reviewer decision naming the exact candidate SHA.
