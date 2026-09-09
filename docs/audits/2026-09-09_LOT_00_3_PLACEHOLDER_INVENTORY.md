# LOT-00.3 - Repository & Scaffold Cleanup Inventory

> Baseline target: PyAccountingKit `0.0.1` Repository Bootstrap.

This inventory records the cleanup performed before any real accounting-domain implementation.

## Decision

`0.0.1` is an engineering bootstrap, not an accounting-engine release. Therefore the package root exposes version metadata only, while every other Python module under `src/pyaccountingkit/` is a documentation-only architectural scaffold. Module paths are retained so the roadmap structure is visible without advertising premature runtime behavior.

## Cleanup policy

- Preserve the package and namespace topology.
- Remove all premature business classes, enums, DTOs, adapter shells, protocols and other executable symbols.
- Preserve an implementation-target plan reference in a module docstring when one already existed.
- Remove `test_*.py` files that contained no real tests; never replace them with `assert True`.
- Classify all example directories as non-runnable future scaffolds.
- Introduce no accounting behavior.

## Source modules neutralized during the final sweep (47)

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

## Total documentation-only source scaffold modules (233)

- `src/pyaccountingkit/adapters/__init__.py`
- `src/pyaccountingkit/adapters/django/__init__.py`
- `src/pyaccountingkit/adapters/django/mappers.py`
- `src/pyaccountingkit/adapters/django/migrations/__init__.py`
- `src/pyaccountingkit/adapters/django/models.py`
- `src/pyaccountingkit/adapters/django/models/__init__.py`
- `src/pyaccountingkit/adapters/django/queries/__init__.py`
- `src/pyaccountingkit/adapters/django/repositories.py`
- `src/pyaccountingkit/adapters/django/repositories/__init__.py`
- `src/pyaccountingkit/adapters/django/unit_of_work.py`
- `src/pyaccountingkit/adapters/imports/__init__.py`
- `src/pyaccountingkit/adapters/imports/fec/__init__.py`
- `src/pyaccountingkit/adapters/imports/fec/controls.py`
- `src/pyaccountingkit/adapters/imports/fec/normalizer.py`
- `src/pyaccountingkit/adapters/imports/fec/parser.py`
- `src/pyaccountingkit/adapters/imports/fec/schema.py`
- `src/pyaccountingkit/adapters/imports/fec_reader.py`
- `src/pyaccountingkit/adapters/in_memory/__init__.py`
- `src/pyaccountingkit/adapters/in_memory/repositories.py`
- `src/pyaccountingkit/adapters/in_memory/unit_of_work.py`
- `src/pyaccountingkit/adapters/reconciliation/__init__.py`
- `src/pyaccountingkit/adapters/reconciliation/bank/__init__.py`
- `src/pyaccountingkit/adapters/reconciliation/bank_statement_reader.py`
- `src/pyaccountingkit/adapters/reconciliation/external/__init__.py`
- `src/pyaccountingkit/adapters/reconciliation/import_sources/__init__.py`
- `src/pyaccountingkit/adapters/regulatory/__init__.py`
- `src/pyaccountingkit/adapters/regulatory/fec_writer.py`
- `src/pyaccountingkit/adapters/regulatory/filesystem.py`
- `src/pyaccountingkit/adapters/regulatory/http.py`
- `src/pyaccountingkit/adapters/regulatory/object_storage.py`
- `src/pyaccountingkit/adapters/regulatory/package.py`
- `src/pyaccountingkit/adapters/sqlalchemy/__init__.py`
- `src/pyaccountingkit/adapters/sqlalchemy/mappers.py`
- `src/pyaccountingkit/adapters/sqlalchemy/migrations/__init__.py`
- `src/pyaccountingkit/adapters/sqlalchemy/queries/__init__.py`
- `src/pyaccountingkit/adapters/sqlalchemy/repositories.py`
- `src/pyaccountingkit/adapters/sqlalchemy/repositories/__init__.py`
- `src/pyaccountingkit/adapters/sqlalchemy/tables.py`
- `src/pyaccountingkit/adapters/sqlalchemy/tables/__init__.py`
- `src/pyaccountingkit/adapters/sqlalchemy/unit_of_work.py`
- `src/pyaccountingkit/application/__init__.py`
- `src/pyaccountingkit/application/analysis/__init__.py`
- `src/pyaccountingkit/application/charts/__init__.py`
- `src/pyaccountingkit/application/closing/__init__.py`
- `src/pyaccountingkit/application/consolidation/__init__.py`
- `src/pyaccountingkit/application/controls/__init__.py`
- `src/pyaccountingkit/application/entries/__init__.py`
- `src/pyaccountingkit/application/imports/__init__.py`
- `src/pyaccountingkit/application/ledger/__init__.py`
- `src/pyaccountingkit/application/reconciliation/__init__.py`
- `src/pyaccountingkit/application/references/__init__.py`
- `src/pyaccountingkit/application/reporting/__init__.py`
- `src/pyaccountingkit/application/subledgers/__init__.py`
- `src/pyaccountingkit/core/__init__.py`
- `src/pyaccountingkit/core/clock.py`
- `src/pyaccountingkit/core/currency.py`
- `src/pyaccountingkit/core/errors.py`
- `src/pyaccountingkit/core/idempotency.py`
- `src/pyaccountingkit/core/identifiers.py`
- `src/pyaccountingkit/core/money.py`
- `src/pyaccountingkit/core/results.py`
- `src/pyaccountingkit/core/revisions.py`
- `src/pyaccountingkit/domain/__init__.py`
- `src/pyaccountingkit/domain/analysis/__init__.py`
- `src/pyaccountingkit/domain/analysis/analysis_snapshot.py`
- `src/pyaccountingkit/domain/analysis/diagnostics.py`
- `src/pyaccountingkit/domain/analysis/functional_balance.py`
- `src/pyaccountingkit/domain/analysis/indicators.py`
- `src/pyaccountingkit/domain/analysis/ratios.py`
- `src/pyaccountingkit/domain/analysis/scores.py`
- `src/pyaccountingkit/domain/analysis/trends.py`
- `src/pyaccountingkit/domain/analysis/working_capital.py`
- `src/pyaccountingkit/domain/audit/__init__.py`
- `src/pyaccountingkit/domain/audit/actor.py`
- `src/pyaccountingkit/domain/audit/events.py`
- `src/pyaccountingkit/domain/charts/__init__.py`
- `src/pyaccountingkit/domain/charts/company_account.py`
- `src/pyaccountingkit/domain/charts/company_chart.py`
- `src/pyaccountingkit/domain/charts/generation.py`
- `src/pyaccountingkit/domain/charts/numbering.py`
- `src/pyaccountingkit/domain/charts/regulatory_binding.py`
- `src/pyaccountingkit/domain/closing/__init__.py`
- `src/pyaccountingkit/domain/closing/accruals.py`
- `src/pyaccountingkit/domain/closing/adjustments.py`
- `src/pyaccountingkit/domain/closing/closing_run.py`
- `src/pyaccountingkit/domain/closing/evidence.py`
- `src/pyaccountingkit/domain/closing/opening.py`
- `src/pyaccountingkit/domain/closing/provisions.py`
- `src/pyaccountingkit/domain/consolidation/__init__.py`
- `src/pyaccountingkit/domain/consolidation/adjustments/__init__.py`
- `src/pyaccountingkit/domain/consolidation/adjustments/adjustment.py`
- `src/pyaccountingkit/domain/consolidation/chart/__init__.py`
- `src/pyaccountingkit/domain/consolidation/chart/mapping.py`
- `src/pyaccountingkit/domain/consolidation/controls/__init__.py`
- `src/pyaccountingkit/domain/consolidation/controls/staleness.py`
- `src/pyaccountingkit/domain/consolidation/currency/__init__.py`
- `src/pyaccountingkit/domain/consolidation/currency/rates.py`
- `src/pyaccountingkit/domain/consolidation/currency/translation.py`
- `src/pyaccountingkit/domain/consolidation/entries/__init__.py`
- `src/pyaccountingkit/domain/consolidation/entries/entry.py`
- `src/pyaccountingkit/domain/consolidation/entries/ledger.py`
- `src/pyaccountingkit/domain/consolidation/group/__init__.py`
- `src/pyaccountingkit/domain/consolidation/group/entity.py`
- `src/pyaccountingkit/domain/consolidation/group/ownership.py`
- `src/pyaccountingkit/domain/consolidation/group/scope.py`
- `src/pyaccountingkit/domain/consolidation/intercompany/__init__.py`
- `src/pyaccountingkit/domain/consolidation/intercompany/elimination.py`
- `src/pyaccountingkit/domain/consolidation/investments/__init__.py`
- `src/pyaccountingkit/domain/consolidation/investments/goodwill.py`
- `src/pyaccountingkit/domain/consolidation/investments/minority.py`
- `src/pyaccountingkit/domain/consolidation/packages/__init__.py`
- `src/pyaccountingkit/domain/consolidation/packages/package.py`
- `src/pyaccountingkit/domain/consolidation/periods/__init__.py`
- `src/pyaccountingkit/domain/consolidation/periods/period.py`
- `src/pyaccountingkit/domain/consolidation/runs/__init__.py`
- `src/pyaccountingkit/domain/consolidation/runs/run.py`
- `src/pyaccountingkit/domain/consolidation/snapshots/__init__.py`
- `src/pyaccountingkit/domain/consolidation/snapshots/snapshot.py`
- `src/pyaccountingkit/domain/controls/__init__.py`
- `src/pyaccountingkit/domain/controls/definitions.py`
- `src/pyaccountingkit/domain/controls/gates.py`
- `src/pyaccountingkit/domain/controls/results.py`
- `src/pyaccountingkit/domain/controls/runs.py`
- `src/pyaccountingkit/domain/identity/__init__.py`
- `src/pyaccountingkit/domain/identity/entity.py`
- `src/pyaccountingkit/domain/identity/fiscal_year.py`
- `src/pyaccountingkit/domain/imports/__init__.py`
- `src/pyaccountingkit/domain/imports/batch.py`
- `src/pyaccountingkit/domain/imports/import_plan.py`
- `src/pyaccountingkit/domain/imports/issues.py`
- `src/pyaccountingkit/domain/imports/normalized_record.py`
- `src/pyaccountingkit/domain/imports/raw_record.py`
- `src/pyaccountingkit/domain/imports/source_artifact.py`
- `src/pyaccountingkit/domain/journals/__init__.py`
- `src/pyaccountingkit/domain/journals/journal.py`
- `src/pyaccountingkit/domain/journals/journal_entry.py`
- `src/pyaccountingkit/domain/journals/journal_line.py`
- `src/pyaccountingkit/domain/ledger/__init__.py`
- `src/pyaccountingkit/domain/ledger/general_ledger.py`
- `src/pyaccountingkit/domain/ledger/posting.py`
- `src/pyaccountingkit/domain/ledger/reversal.py`
- `src/pyaccountingkit/domain/ledger/snapshots.py`
- `src/pyaccountingkit/domain/ledger/trial_balance.py`
- `src/pyaccountingkit/domain/periods/__init__.py`
- `src/pyaccountingkit/domain/periods/accounting_period.py`
- `src/pyaccountingkit/domain/periods/closing_status.py`
- `src/pyaccountingkit/domain/policies/__init__.py`
- `src/pyaccountingkit/domain/policies/applicability.py`
- `src/pyaccountingkit/domain/policies/measurement.py`
- `src/pyaccountingkit/domain/policies/policy_set.py`
- `src/pyaccountingkit/domain/policies/policy_trace.py`
- `src/pyaccountingkit/domain/policies/recognition.py`
- `src/pyaccountingkit/domain/reconciliation/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/controls/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/controls/sign_off.py`
- `src/pyaccountingkit/domain/reconciliation/definitions/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/definitions/profile.py`
- `src/pyaccountingkit/domain/reconciliation/differences/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/differences/difference.py`
- `src/pyaccountingkit/domain/reconciliation/matching/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/matching/policies.py`
- `src/pyaccountingkit/domain/reconciliation/resolutions/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/resolutions/proposal.py`
- `src/pyaccountingkit/domain/reconciliation/runs/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/runs/run.py`
- `src/pyaccountingkit/domain/reconciliation/snapshots/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/snapshots/source_snapshot.py`
- `src/pyaccountingkit/domain/reconciliation/sources/__init__.py`
- `src/pyaccountingkit/domain/reconciliation/sources/item.py`
- `src/pyaccountingkit/domain/references/__init__.py`
- `src/pyaccountingkit/domain/references/capabilities.py`
- `src/pyaccountingkit/domain/references/concepts.py`
- `src/pyaccountingkit/domain/references/crosswalks.py`
- `src/pyaccountingkit/domain/references/effective_plan.py`
- `src/pyaccountingkit/domain/references/hierarchy.py`
- `src/pyaccountingkit/domain/references/nodes.py`
- `src/pyaccountingkit/domain/references/relations.py`
- `src/pyaccountingkit/domain/references/reporting.py`
- `src/pyaccountingkit/domain/references/snapshots.py`
- `src/pyaccountingkit/domain/references/standards.py`
- `src/pyaccountingkit/domain/reporting/__init__.py`
- `src/pyaccountingkit/domain/reporting/mappings.py`
- `src/pyaccountingkit/domain/reporting/regulatory_profile.py`
- `src/pyaccountingkit/domain/reporting/report_snapshot.py`
- `src/pyaccountingkit/domain/reporting/statement_definition.py`
- `src/pyaccountingkit/domain/reporting/statement_line.py`
- `src/pyaccountingkit/domain/subledgers/__init__.py`
- `src/pyaccountingkit/domain/subledgers/aging.py`
- `src/pyaccountingkit/domain/subledgers/allocations.py`
- `src/pyaccountingkit/domain/subledgers/due_items.py`
- `src/pyaccountingkit/domain/subledgers/matching.py`
- `src/pyaccountingkit/domain/subledgers/parties.py`
- `src/pyaccountingkit/domain/subledgers/payables.py`
- `src/pyaccountingkit/domain/subledgers/receivables.py`
- `src/pyaccountingkit/domain/subledgers/reconciliation.py`
- `src/pyaccountingkit/domain/subledgers/settlements.py`
- `src/pyaccountingkit/domain/subledgers/subledger.py`
- `src/pyaccountingkit/domain/traceability/__init__.py`
- `src/pyaccountingkit/domain/traceability/evidence.py`
- `src/pyaccountingkit/domain/traceability/lineage.py`
- `src/pyaccountingkit/domain/traceability/provenance.py`
- `src/pyaccountingkit/domain/traceability/reproducibility.py`
- `src/pyaccountingkit/integrations/__init__.py`
- `src/pyaccountingkit/integrations/cfa_fra/__init__.py`
- `src/pyaccountingkit/integrations/cfa_fra/adapter.py`
- `src/pyaccountingkit/integrations/cfa_fra/mapper.py`
- `src/pyaccountingkit/integrations/cfa_fra/migration.py`
- `src/pyaccountingkit/integrations/regulatory_framework/__init__.py`
- `src/pyaccountingkit/integrations/regulatory_framework/matrix.py`
- `src/pyaccountingkit/integrations/regulatory_framework/profile.py`
- `src/pyaccountingkit/ports/__init__.py`
- `src/pyaccountingkit/ports/artifacts.py`
- `src/pyaccountingkit/ports/audit.py`
- `src/pyaccountingkit/ports/exchange_rates.py`
- `src/pyaccountingkit/ports/outbox.py`
- `src/pyaccountingkit/ports/queries.py`
- `src/pyaccountingkit/ports/reconciliation.py`
- `src/pyaccountingkit/ports/references.py`
- `src/pyaccountingkit/ports/repositories.py`
- `src/pyaccountingkit/ports/unit_of_work.py`
- `src/pyaccountingkit/ports/valuation.py`
- `src/pyaccountingkit/public/__init__.py`
- `src/pyaccountingkit/public/application.py`
- `src/pyaccountingkit/public/context.py`
- `src/pyaccountingkit/public/dto/__init__.py`
- `src/pyaccountingkit/public/dto/entry.py`
- `src/pyaccountingkit/public/dto/ledger.py`
- `src/pyaccountingkit/public/dto/statement.py`
- `src/pyaccountingkit/public/errors.py`
- `src/pyaccountingkit/public/pagination.py`
- `src/pyaccountingkit/public/protocols/__init__.py`
- `src/pyaccountingkit/public/protocols/references.py`
- `src/pyaccountingkit/public/protocols/unit_of_work.py`

## Test cleanup

The initial LOT-00.3 sweep removed **43** `test_*.py` files after AST verification showed that none contained a real pytest/unittest test function or test class. No fake passing tests were introduced.

Remaining `test_*.py` files after cleanup: **0**.

## Examples

Example scaffold directories classified: **6**.

- `basic_accounting/` - future, non-runnable scaffold in `0.0.1`
- `consolidation/` - future, non-runnable scaffold in `0.0.1`
- `fec_import/` - future, non-runnable scaffold in `0.0.1`
- `financial_reporting/` - future, non-runnable scaffold in `0.0.1`
- `reconciliation/` - future, non-runnable scaffold in `0.0.1`
- `subledger/` - future, non-runnable scaffold in `0.0.1`

## Exit criteria

- Root accounting/business exports: **0**
- Executable non-root package modules: **0**
- Remaining fake `test_*.py` modules: **0**
- Runnable examples claimed by `0.0.1`: **0**
- Accounting features implemented by LOT-00.3: **0**

Real bootstrap tests are intentionally introduced later by LOT-00.5; engineering safety scripts are introduced by LOT-00.4.
