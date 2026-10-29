# FND-C07 — G1 Domain Kernel decision dossier

**Status: PENDING_REVIEW — NO G1 APPROVAL.**  
**Review reference:** standalone recent repository, [draft PR #33](https://github.com/tawounfouet/pyaccountingkit/pull/33) SHA `272d85f319219597abec845929038573b4712203`.  
**Review authority:** independent domain/architecture reviewer; documentation author may not self-approve G1.

## Verified source/test evidence

| Contract | Source location | Observed state / question |
|---|---|---|
| Typed IDs | `domain/shared/identifiers.py` | Frozen UUID wrappers with explicit canonical parse, separated Company / Entity / Book / Draft / Version runtime types |
| Scope | `domain/shared/accounting_scope.py` | Mandatory tenant/company/entity, optional book; identity shape is **not** proof of membership or authorized ownership |
| Calendar time | `domain/shared/effective_interval.py` | Half-open `EffectiveInterval` on business `date`, no naive datetimes |
| Knowledge time | `domain/shared/effective_interval.py` | Half-open timezone-aware `datetime`; UTC conversion before comparisons resolves DST repeated-hour ambiguity |
| Aggregate | `domain/organization/entities.py` | Immutable minimal `LegalEntity`, checked revision/name change; **not** full L03 organization or registration |
| Normative refs | `domain/shared/references.py` | Versioned external framework ref; no normative engine or IFRS/PCG/OHADA accounting rules |
| Digest | `domain/shared/digest.py` | Deterministic local SHA-256 JSON helper; **not** a cross-language/config-publication standard |
| Exceptions | `domain/shared/errors.py` and application ports | Typed domain errors in code; reviewer must confirm public semantics and mapping to contract |
| Architecture | `tests/unit/company_configuration/test_fnd_c05_architecture.py` | Automated domain/application dependency-direction tests, not an independent code review |

- [Python CI #40955190292](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190292): **289 passed / 19 skipped per Python 3.11/3.12**, Ruff green. Tests include domain property and DST-fold regressions.
- [FND-C06 package #40955190309](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190309): built wheel/sdist and verified isolated import on Python 3.11/3.12.

## Review questions requiring a written decision

1. **Aggregate equality:** `LegalEntity.__eq__/__hash__` currently use `(tenant_id, legal_entity_id)`, **not `company_id`**. This is consistent only if the entity UUID is unique within the tenant and cannot legitimately be reused under another company. The persistence key is also `(tenant_id, entity_id)`. Reviewer must confirm that uniqueness model or require change/tests; **do not silently infer membership**.
2. **Scope vs ownership:** `ConfigurationScope` validates typed shape, not that the entity belongs to the company; L02 persistence/commands must provide authoritative checks. Reviewer must verify test traces for CFG-01..CFG-10 ownership.
3. **Temporal policy:** approve half-open business-date and UTC knowledge-instant conventions, DST overlap and no fallback. Confirm intended behaviors for open-ended intervals.
4. **Versioned references:** confirm that registry validation and normative reference content remain outside L01, and data-shape validation is not presented as legality/compliance approval.
5. **Digest stability:** approve local-only deterministic helper, reserve publication/Snapshot canonicalization for later ADR and L09/L10.
6. **API compatibility:** approve explicit *standalone development API* scope, no implied equivalence with `pyaccountingkit_old`.
7. **Error contracts:** decide whether the domain/application exception and identity-equality contracts need changes before G1 sign-off.

## Reserved independent review fields — intentionally unsigned

- Decision: **PENDING_REVIEW**
- Reviewer (domain): **UNASSIGNED**
- Review date: **NOT RECORDED**
- Exact reviewed SHA: **NOT RECORDED**
- GitHub approval / decision URL: **NOT RECORDED**
- Resolved scope/equality/temporal exceptions: **NONE RECORDED**
- G1 integration gate: **NOT SATISFIED**

**This is a review dossier, not a G1 GO.**
