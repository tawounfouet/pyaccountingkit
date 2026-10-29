# Evidence - L01 increment 02: minimal LegalEntity and temporal properties

Date: 2026-10-29. **Evidence snapshot pending remote CI qualification**.

## Delivered in proposed PR #3

- Immutable identity-stable `LegalEntity` kernel slice, with explicit non-book scope, typed legal jurisdiction and functional currency, validated name, positive revision and guarded in-memory amendment.
- `JurisdictionCode` syntax-only VO, `InvalidLegalEntity` error.
- Tests for entity identity, revision, scope, invalid inputs, and tenant differentiation.
- Hypothesis properties for half-open effective and knowledge intervals, touching non-overlap, and symmetry.
- `L01_INVARIANT_TRACEABILITY.md` maps CFG-01..CFG-10 to their actual owners and remaining gaps.

## Local execution before upload

```
PYTHONPATH=src python -m pytest -q tests/unit
78 passed in 0.10s
```

Hypothesis and Ruff are not installed in this isolated local container (package index is unavailable); their results must be verified via GitHub Actions using `[project.optional-dependencies].dev` on the **exact** uploaded commit. **Do not mark G1 approved on this local evidence.**

## Still outstanding

- GitHub CI result for this increment (pending at this evidence draft).
- G0 sign-off and ADR approval; in particular company membership semantics and interval choices.
- L02 authorization, audit, database concurrency / transaction enforcement.
- L03 full organization model and L09 governed publication lifecycle.
