# Evidence - L01 increment 02: minimal LegalEntity and temporal properties

Date: 2026-10-29. **CI qualification evidence recorded; G0/G1 approval still pending**.

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

Hypothesis and Ruff were unavailable in the isolated local container (package index unreachable). They were installed by GitHub Actions via `[project.optional-dependencies].dev`; see remote evidence below. **Do not mark G1 approved based solely on these tests.**

## Still outstanding

- **GitHub CI run [#10](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40838129260)**: completed successfully on commit `a4d8d7e572d2d72fde1878b095ba6de4c057c173`. Python **3.11 and 3.12** jobs both passed unit tests + property-based tests + Ruff. A verified job log reports **82 passed in 0.65s** and `All checks passed!`.
- G0 sign-off and ADR approval; in particular company membership semantics and interval choices.
- L02 authorization, audit, database concurrency / transaction enforcement.
- L03 full organization model and L09 governed publication lifecycle.
