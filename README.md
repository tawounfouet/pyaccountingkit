# PyAccountingKit

Modular Python accounting toolkit. **The standalone Company Configuration Foundation (L00-L02) is a **development and CI-qualified candidate**, not an approved G0/G1/G2 gate, production-ready IAM implementation, or stable release.**

## Company Configuration (L00-L02)

This bounded context **configures, but does not post** accounting entries. It supplies versioned configuration to runtime resolution through future versioned contracts, without owning normative standards or ledger writes.

- `src/pyaccountingkit/company_configuration/domain/`: pure Python domain primitives and scoped aggregate (L01).
- `src/pyaccountingkit/company_configuration/application/`: use cases and ports (L02).
- `src/pyaccountingkit/company_configuration/infrastructure/`: memory, PostgreSQL, IAM and audit candidate adapters (L02).
- `docs/company_configuration/evidence/`: verified CI checkpoints, migration and security limitations, outstanding gates.
- `docs/adr/`: provisional architecture decisions, pending review.
- `tests/unit/company_configuration/`: domain, service, negative and architecture tests.
- `tests/integration/company_configuration/`: opt-in PostgreSQL transactional/security tests.
- `tests/qualification/`: isolated migrations, logical restore and artifact qualification.

Run after installing development dependencies in an isolated environment:

```bash
python -m pip install -e '.[dev,postgres,iam]'
python -m pytest -q
python -m ruff check src tests scripts
```

The project version is a placeholder (`0.0.0`); it is **not** a stable release. L02 persistence, authorization, audit, transactional Inbox/Outbox, and privileged SQL recovery are **candidate implementations** with exact-SHA CI evidence. Production external IAM, independent credential isolation, DR, published C10 consumer contracts, formal gate sign-offs and historical package reconciliation remain **out of scope or pending**.

The consolidated Phase-1 integration candidate is [PR #31](https://github.com/tawounfouet/pyaccountingkit/pull/31). Prior stacked PRs remain unmerged for provenance. Check [standalone gate checklist](docs/company_configuration/evidence/PHASE_1_STANDALONE_FOUNDATION_CLOSURE_CHECKLIST.md) before any integration into `main`.
