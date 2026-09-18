# LOT-21 — Public API Facade Implementation Plan

**Target:** `0.5.0a1`  
**Baseline:** stable `0.4.0` at `e2dc1ad2a0a40e6577c0cb5f6dd9cbbd1fb5984e`  
**Scope:** Public API Facade only. LOT-22 extension contracts/manifests and LOT-23/24 ORM adapters remain separate.

## 1. Objective

Turn the existing `src/pyaccountingkit/public/` bootstrap placeholders into a coherent,
framework-neutral user boundary without changing accounting semantics from LOT-10..20.

The public composition root is:

```text
AccountingApplication
├── references
├── charts
├── entries
├── ledger
├── closing
├── controls
├── imports
├── statements
├── reporting
├── analysis
└── subledgers
```

## 2. Architectural rules

1. Public API never imports Django or SQLAlchemy.
2. Public query results must fail closed if an ORM object crosses the boundary.
3. Public DTOs are stdlib dataclasses, immutable by default.
4. Mutations are explicit verbs; no public transaction/locking API is exposed.
5. `CommandContext` carries already-resolved actor/correlation metadata; it performs no auth.
6. Missing namespace operations raise a typed, machine-readable public error.
7. Core-only `import pyaccountingkit` must work with no optional ORM installed.
8. LOT-21 does not freeze the pre-1.0 API; LOT-22 formalizes compatibility manifests/contracts.
9. LOT-21 must not create a second posting, closing, import, reporting, analysis or subledger engine.

## 3. Public primitives

### CommandContext

```text
actor
correlation_id
request_id?
idempotency_key?
metadata
```

The object is frozen and copies metadata into a read-only mapping.

### Pagination

`Cursor` is opaque. `Page[T]` is frozen, tuple-backed, cursor-first and validates page metadata.

### Errors

```text
PyAccountingKitError
└── PublicAccountingError
    ├── PublicOperationUnavailableError
    ├── PublicBoundaryViolationError
    └── PublicValidationError
```

Each exposes `code`, `message`, `context`, `retryable` and `to_info()`.

## 4. Namespace bridge

LOT-21 introduces explicit user-facing namespace classes. They delegate to application services
bound at composition time. This bridge is deliberately internal to LOT-21: it is not the public
adapter-author protocol contract planned for LOT-22.

Every explicit operation passes keyword arguments and optional `CommandContext`, then validates
the returned graph for Django/SQLAlchemy ancestry before returning it.

This keeps LOT-21 independent of the future Django/PostgreSQL and SQLAlchemy/PostgreSQL adapters.

## 5. DTO baseline

Initial public immutable DTOs cover the core high-value read surfaces:

- `JournalLineDTO`, `JournalEntryDTO`;
- `TrialBalanceLineDTO`, `TrialBalanceDTO`;
- `FinancialStatementLineDTO`, `FinancialStatementDTO`.

They provide explicit `from_domain` conversion and never expose an ORM instance.

## 6. GAPI qualification

Executable tests must demonstrate:

```text
[ ] AccountingApplication exposes all 11 namespaces
[ ] namespace methods are explicit and delegate without ORM coupling
[ ] CommandContext is immutable and metadata cannot be mutated
[ ] Page is immutable/validated
[ ] public DTOs are immutable and map domain values deterministically
[ ] public errors have machine-readable codes
[ ] missing operation fails closed with typed public error
[ ] Django/SQLAlchemy-derived return values are rejected without importing those frameworks
[ ] package root exposes AccountingApplication and Money
[ ] core-only import does not import django/sqlalchemy
[ ] existing 0.4 qualification remains green
[ ] Python 3.11/3.12/3.13, Ruff, mypy, package and Security remain green
```

## 7. Out of scope

- public extension protocols as a frozen compatibility contract (LOT-22);
- deterministic public manifest generation/freeze (LOT-22);
- Django/PostgreSQL persistence implementation (LOT-23);
- SQLAlchemy/PostgreSQL persistence implementation (LOT-24);
- async API;
- authn/authz;
- new accounting business semantics.

## 8. Exit criterion

LOT-21 is complete when `0.5.0a1` exposes the framework-neutral facade and immutable public
boundary, GAPI tests are green, optional ORM frameworks are absent from core imports, all 0.4
business qualifications remain green, and canonical CI/Security pass on the exact PR head.
