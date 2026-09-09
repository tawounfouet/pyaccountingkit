# LOT-00.3 - Repository & Scaffold Cleanup Inventory

> Baseline: PyAccountingKit `0.0.1` Repository Bootstrap.

This inventory records the deterministic cleanup performed before real accounting-domain implementation.

## Policy

- Structural namespaces are retained.
- Empty business classes are removed from the executable surface and replaced by explicit module scaffolds.
- `test_*.py` files without a real test are removed rather than replaced by fake passing tests.
- Example directories are explicitly classified as non-runnable future scaffolds.
- No accounting behavior is introduced by LOT-00.3.

## Empty business placeholder modules normalized (15)

- `src/pyaccountingkit/core/clock.py`
- `src/pyaccountingkit/core/currency.py`
- `src/pyaccountingkit/core/errors.py`
- `src/pyaccountingkit/core/idempotency.py`
- `src/pyaccountingkit/core/identifiers.py`
- `src/pyaccountingkit/core/money.py`
- `src/pyaccountingkit/core/revisions.py`
- `src/pyaccountingkit/domain/charts/company_account.py`
- `src/pyaccountingkit/domain/charts/company_chart.py`
- `src/pyaccountingkit/domain/identity/entity.py`
- `src/pyaccountingkit/domain/identity/fiscal_year.py`
- `src/pyaccountingkit/domain/journals/journal.py`
- `src/pyaccountingkit/domain/journals/journal_entry.py`
- `src/pyaccountingkit/domain/journals/journal_line.py`
- `src/pyaccountingkit/domain/periods/accounting_period.py`

## Placeholder test modules removed (43)

- `tests/concurrency/test_postgres_concurrency.py`
- `tests/contract/test_repository_contract.py`
- `tests/golden/cfa_fra/test_closing_parity.py`
- `tests/golden/cfa_fra/test_fec_parity.py`
- `tests/golden/cfa_fra/test_posting_parity.py`
- `tests/golden/regulatory/test_fec_compliance.py`
- `tests/golden/regulatory/test_pcg_baseline.py`
- `tests/golden/regulatory/test_syscohada_baseline.py`
- `tests/integration/test_django_adapter.py`
- `tests/integration/test_sqlalchemy_adapter.py`
- `tests/migration/test_cfa_fra_migration.py`
- `tests/performance/test_fec_throughput.py`
- `tests/performance/test_large_ledger.py`
- `tests/property/test_balance_invariants.py`
- `tests/property/test_money_properties.py`
- `tests/replay/test_historical_replay.py`
- `tests/unit/core/test_money.py`
- `tests/unit/domain/test_aged_balance.py`
- `tests/unit/domain/test_bank_reconciliation.py`
- `tests/unit/domain/test_closing.py`
- `tests/unit/domain/test_company_chart.py`
- `tests/unit/domain/test_consolidation_group.py`
- `tests/unit/domain/test_consolidation_statements.py`
- `tests/unit/domain/test_currency_translation.py`
- `tests/unit/domain/test_fec_reader.py`
- `tests/unit/domain/test_fec_writer.py`
- `tests/unit/domain/test_financial_analysis.py`
- `tests/unit/domain/test_financial_facts_export.py`
- `tests/unit/domain/test_financial_statements.py`
- `tests/unit/domain/test_import_pipeline.py`
- `tests/unit/domain/test_intercompany_eliminations.py`
- `tests/unit/domain/test_intercompany_reconciliation.py`
- `tests/unit/domain/test_journal_entry.py`
- `tests/unit/domain/test_matching.py`
- `tests/unit/domain/test_numbering_policy.py`
- `tests/unit/domain/test_policies.py`
- `tests/unit/domain/test_posting_service.py`
- `tests/unit/domain/test_reconciliation_engine.py`
- `tests/unit/domain/test_reference_standards.py`
- `tests/unit/domain/test_reversal.py`
- `tests/unit/domain/test_subledger.py`
- `tests/unit/public/test_application_facade.py`
- `tests/unit/test_architecture_boundaries.py`

## Existing real test modules retained (0)

- None at this milestone

## Non-placeholder implementation modules preserved (47)

- `src/pyaccountingkit/adapters/django/mappers.py`
- `src/pyaccountingkit/adapters/django/models.py`
- `src/pyaccountingkit/adapters/django/repositories.py`
- `src/pyaccountingkit/adapters/imports/fec_reader.py`
- `src/pyaccountingkit/adapters/in_memory/repositories.py`
- `src/pyaccountingkit/adapters/in_memory/unit_of_work.py`
- `src/pyaccountingkit/adapters/reconciliation/bank_statement_reader.py`
- `src/pyaccountingkit/adapters/regulatory/fec_writer.py`
- `src/pyaccountingkit/adapters/sqlalchemy/mappers.py`
- `src/pyaccountingkit/adapters/sqlalchemy/repositories.py`
- `src/pyaccountingkit/adapters/sqlalchemy/tables.py`
- `src/pyaccountingkit/domain/consolidation/adjustments/adjustment.py`
- `src/pyaccountingkit/domain/consolidation/chart/mapping.py`
- `src/pyaccountingkit/domain/consolidation/controls/staleness.py`
- `src/pyaccountingkit/domain/consolidation/currency/rates.py`
- `src/pyaccountingkit/domain/consolidation/currency/translation.py`
- `src/pyaccountingkit/domain/consolidation/entries/entry.py`
- `src/pyaccountingkit/domain/consolidation/entries/ledger.py`
- `src/pyaccountingkit/domain/consolidation/group/entity.py`
- `src/pyaccountingkit/domain/consolidation/group/ownership.py`
- `src/pyaccountingkit/domain/consolidation/group/scope.py`
- `src/pyaccountingkit/domain/consolidation/intercompany/elimination.py`
- `src/pyaccountingkit/domain/consolidation/investments/goodwill.py`
- `src/pyaccountingkit/domain/consolidation/investments/minority.py`
- `src/pyaccountingkit/domain/consolidation/packages/package.py`
- `src/pyaccountingkit/domain/consolidation/periods/period.py`
- `src/pyaccountingkit/domain/consolidation/runs/run.py`
- `src/pyaccountingkit/domain/consolidation/snapshots/snapshot.py`
- `src/pyaccountingkit/domain/periods/closing_status.py`
- `src/pyaccountingkit/domain/reconciliation/controls/sign_off.py`
- `src/pyaccountingkit/domain/reconciliation/definitions/profile.py`
- `src/pyaccountingkit/domain/reconciliation/differences/difference.py`
- `src/pyaccountingkit/domain/reconciliation/matching/policies.py`
- `src/pyaccountingkit/domain/reconciliation/resolutions/proposal.py`
- `src/pyaccountingkit/domain/reconciliation/runs/run.py`
- `src/pyaccountingkit/domain/reconciliation/snapshots/source_snapshot.py`
- `src/pyaccountingkit/domain/reconciliation/sources/item.py`
- `src/pyaccountingkit/integrations/cfa_fra/adapter.py`
- `src/pyaccountingkit/integrations/cfa_fra/mapper.py`
- `src/pyaccountingkit/integrations/cfa_fra/migration.py`
- `src/pyaccountingkit/integrations/regulatory_framework/matrix.py`
- `src/pyaccountingkit/integrations/regulatory_framework/profile.py`
- `src/pyaccountingkit/public/dto/entry.py`
- `src/pyaccountingkit/public/dto/ledger.py`
- `src/pyaccountingkit/public/dto/statement.py`
- `src/pyaccountingkit/public/protocols/references.py`
- `src/pyaccountingkit/public/protocols/unit_of_work.py`

## Exit criteria

- Empty top-level business classes remaining: **0**
- Fake `test_*.py` modules remaining: **0**
- Root business exports added: **0**
- Accounting features implemented by this lot: **0**
