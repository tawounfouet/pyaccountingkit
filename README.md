# PyAccountingKit

Python accounting toolkit — **standalone Company Configuration Foundation
(L00–L02), under review**. This repository is the primary **development target**
for the new Foundation. It is NOT the historical framework's production API and
has NOT been released or approved as a stable distribution.

**Important:** the project currently uses the placeholder package version
`0.0.0`. Do not publish it under the `pyaccountingkit` distribution name,
rely on historical API parity, or use the privileged SQL control-plane paths in
production without independent security/deployment approvals.

## Scope of the Foundation

`pyaccountingkit.company_configuration` manages **configuration**; it does
not own journal or Ledger posting. The stack contains the following candidates:

- **L00 — Baseline and architecture:** scoped recent-repository bootstrap,
  ADR inventory and independent gate-review checklist.
- **L01 — Pure Domain Kernel:** typed scope and identifiers, immutable values,
  UTC temporal intervals, versioned references and a minimal `LegalEntity`.
- **L02 — Technical Foundations:** application use cases and ports, in-memory
  and PostgreSQL repositories/Unit of Work, audit and bounded Outbox/Inbox,
  scoped SQL authorization and IAM recovery (with independent one-use grants),
  migration runner and SQL restoration qualification.

The branch chain is presently [#27](https://github.com/tawounfouet/pyaccountingkit/pull/27)
→ [#28](https://github.com/tawounfouet/pyaccountingkit/pull/28)
→ [#29](https://github.com/tawounfouet/pyaccountingkit/pull/29)
→ [#31](https://github.com/tawounfouet/pyaccountingkit/pull/31).
A **single FND-C06 PR to `main` is a review candidate, not a merge or sign-off**.

## Development and qualification

Python 3.11 and 3.12 are covered by automated unit and PostgreSQL 16 CI.
With a local Python environment:

```bash
python -m pip install -e '.[dev,postgres,iam]'
python -m pytest -q
python -m ruff check src tests scripts
python -m build
python scripts/qualify_foundation_artifacts.py . dist
```

The PostgreSQL integration and migration/restore tests require ephemeral
test-only roles, a dedicated isolated database and the `CC_PG_*` test variables
defined by the relevant GitHub Actions workflows. **Do not run the CI role
provisioner against a production database.**

Production-like control-plane deployments need separate IAM approval issuers,
protected signing keys, PostgreSQL role isolation, audit and restore policy,
and an independent review of SQL SECURITY DEFINER procedures. PostgreSQL
logical dump/restore CI does not prove disaster recovery, RPO/RTO or live IAM.

## Documentation and gates

- [Foundation G0/G1/G2 closure checklist](docs/company_configuration/evidence/PHASE_1_STANDALONE_FOUNDATION_CLOSURE_CHECKLIST.md).
- [Standalone-first scope decision](docs/company_configuration/evidence/L00/ADR_CC_00A_STANDALONE_FOUNDATION_SCOPE.md).
- [Security hardening FND-C03](docs/company_configuration/evidence/L02_07n_INDEPENDENT_RECOVERY_GRANT_SECURITY_HARDENING.md).
- [Migration/recovery FND-C04](docs/company_configuration/evidence/L02_08_FND_C04_MIGRATION_RECOVERY_QUALIFICATION.md).
- [Reliability FND-C05](docs/company_configuration/evidence/L02_09_FND_C05_RELIABILITY_AND_CONTRACTS.md).

**G0, G1 and G2 remain subject to independently recorded decisions**; green
CI alone does not equal production readiness, acceptance or a release. Work
to reconcile `pyaccountingkit_old` is explicitly postponed until after the
standalone new-repository Foundation is completed.
