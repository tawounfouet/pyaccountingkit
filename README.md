# PyAccountingKit

Modular Python accounting toolkit. **Foundations are under development; no release or qualification gate is claimed.**

## Company Configuration (L00-L02)

This bounded context **configures, but does not post** accounting entries. It supplies versioned configuration to runtime resolution through future versioned contracts, without owning normative standards or ledger writes.

- `src/pyaccountingkit/company_configuration/domain/shared/`: pure Python domain primitives (L01, initial increment).
- `docs/company_configuration/evidence/L00/`: verified repository baseline and unresolved checks.
- `docs/adr/`: provisional architecture decisions, pending review.
- `tests/unit/company_configuration/`: boundary and negative tests.

Run after installing development dependencies in an isolated environment:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check src tests
```

The project version is a placeholder (`0.0.0`); it is **not** a stable release. L02 persistence, authorization, audit and outbox have not yet been implemented.
