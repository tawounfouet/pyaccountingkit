# PyAccountingKit

PyAccountingKit is a Python toolkit for double-entry accounting built around a
framework-free domain model, hexagonal architecture, deterministic replay and
strict accounting invariants.

The project is designed to support several accounting and regulatory contexts
without coupling the accounting core to Django, SQLAlchemy, FastAPI or a
specific regulatory dataset.

## Status

PyAccountingKit is under active beta development. The package metadata is
currently on the `0.2.0b1` line and the public API is **not yet stable**.

The current hardening milestone is `LOT-QA-01 — Cross-Lot Accounting & Policy
Integrity Remediation`. Its purpose is to consolidate cross-cutting invariants
before feature development continues toward the next beta.

Do not infer release readiness from the version number alone. A release is
qualified only when the canonical CI, package and security gates are green and
the milestone Definition of Done is satisfied.

## Core guarantees

The following rules are intentional domain constraints, not implementation
accidents:

- monetary arithmetic uses `Decimal`; business code must never introduce
  binary floating-point arithmetic;
- every accounting operation is scoped to exactly one `AccountingEntity`;
  cross-entity chart, journal, period, policy or account usage must fail closed;
- a journal line with both debit and credit equal to zero is invalid and must
  never be made constructible merely to satisfy an old test fixture;
- journal entries and journal-entry proposals must be balanced before posting;
- posted entries are immutable; corrections use reversal/adjustment entries;
- policy resolution is fail-closed when required runtime context is missing or
  ambiguous;
- current policy execution requires the policy set to be active, effective for
  the accounting date, entity-compatible and reference/snapshot-compatible;
- historical replay is an explicit execution mode and must remain deterministic;
- company-account resolution is entity-, accounting-date- and chart-version
  aware;
- posting mutations, audit records, outbox events and idempotency state belong
  to the same transactional unit of work.

When a new invariant invalidates an old fixture, **fix the fixture or generator;
do not weaken the invariant**.

## Architecture

Dependency direction is intentionally strict:

```text
adapters  ───────► application ───────► domain
   │                    │                  │
   └──────────────► ports ◄────────────────┘
                         │
                        core
```

Main areas:

- `src/pyaccountingkit/core/` — primitives such as money, currency, clock,
  identifiers, revisions, idempotency and entity-scope guards;
- `src/pyaccountingkit/domain/` — pure accounting model and policies;
- `src/pyaccountingkit/application/` — use cases and transactional
  orchestration;
- `src/pyaccountingkit/ports/` — repository, unit-of-work, chart-resolution,
  account-role-resolution, audit, outbox and external-service contracts;
- `src/pyaccountingkit/adapters/` — in-memory and later production adapter
  implementations;
- `docs/` — specifications, ADRs, plans and roadmap; architectural decisions
  are documentation-driven.

A particularly important cross-lot path is:

```text
AccountingEntity + AccountingDate
        │
        ▼
CompanyChart ──► CompanyChartVersion ──► CompanyChartOfAccounts
        │
        ├──► AccountRole resolution
        │
        └──► JournalEntry / Proposal
                     │
                     ▼
              PostingOrchestrator
                     │
        Entry + Audit + Outbox + Idempotency
                     │
                     ▼
                   COMMIT
```

## Documentation

Start with:

- `docs/ROADMAP.md` for the lot sequence and release gates;
- `docs/plans/` for milestone-specific implementation plans;
- `docs/specs/` for canonical requirements and ADRs;
- `AGENTS.md` for the mandatory coding-agent workflow and repository-specific
  guardrails;
- `CONTRIBUTING.md` for contribution and commit conventions.

## Installation

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Development workflow

Do not use GitHub Actions as the first place to discover local formatting,
typing or test failures. Before pushing a change, run the same gates locally.

```bash
# Apply canonical formatting first.
python -m ruff format src tests scripts

# Then verify static quality.
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy src

# Core deterministic test suite used by the Python matrix in CI.
python -m pytest tests/unit tests/property tests/contract -v --tb=short

# Canonical release qualification.
python scripts/qualify_release.py
```

For security parity with `.github/workflows/security.yml`:

```bash
python -m pip install pip-audit "bandit[toml]"
python -m pip_audit
python -m bandit -r src/ -c pyproject.toml
```

The CI test matrix currently qualifies supported Python versions independently.
A change is not ready merely because it passes on one interpreter.

## Change-safety checklist

Before committing or pushing a refactor:

1. Read the active plan/spec/ADR and the current package version in
   `pyproject.toml`; never assume an obsolete milestone.
2. If changing a constructor, protocol or orchestrator signature, search the
   whole repository and migrate **all** call sites, fixtures and tests in the
   same change.
3. If strengthening a domain invariant, update Hypothesis strategies and test
   builders so they generate valid objects unless the test is explicitly
   testing rejection.
4. Prefer ports/resolvers at application boundaries. Do not bypass a versioned
   resolver by injecting a raw aggregate merely because an older test did so.
5. Keep entity, date, chart version, policy version and reference snapshot
   traceability intact across application boundaries.
6. Run formatter, lint, typing, tests, release qualifier and relevant security
   checks before pushing.

The more detailed rules for coding agents are maintained in `AGENTS.md`.

## License

MIT
