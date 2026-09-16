"""Executable release-0.3 pipeline shared by integration and replay qualification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.adapters.imports.fec import FECAdapter, FECSourceDescriptor
from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.in_memory.reference_reporting_model_provider import (
    InMemoryReferenceReportingModelProvider,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.adapters.regulatory.json_renderer import CanonicalJSONRegulatoryRenderer
from pyaccountingkit.application.imports.execution import ImportExecutionService
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.application.reporting.regulatory_export_service import RegulatoryExportService
from pyaccountingkit.application.reporting.regulatory_reporting_service import (
    RegulatoryReportingService,
)
from pyaccountingkit.application.reporting.trial_balance_query import TrialBalanceQuery
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    FiscalYearId,
    IdFactory,
    JournalId,
    PeriodId,
)
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)
from pyaccountingkit.domain.imports.import_plan import (
    ImportEntryPlan,
    ImportPlan,
    ImportPlannedLine,
)
from pyaccountingkit.domain.imports.mapping import (
    ExplicitImportAccountMapper,
    ExplicitImportJournalMapper,
)
from pyaccountingkit.domain.imports.normalized_record import NormalizedImportRecord
from pyaccountingkit.domain.imports.source_artifact import SourceArtifact
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.reporting.engine import (
    FinancialStatementBuildRequest,
    FinancialStatementEngine,
    StatementControlStatus,
)
from pyaccountingkit.domain.reporting.mappings import (
    MappingProvenance,
    StatementAccountMapping,
    StatementMappingSet,
    StatementMappingSetStatus,
    StatementMappingStatus,
)
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingNode,
    ReferenceReportingNodeType,
)
from pyaccountingkit.domain.reporting.regulatory_export import RegulatoryExportDefinition
from pyaccountingkit.domain.reporting.regulatory_mapping import (
    RegulatoryMappingProvenance,
    RegulatoryMappingSet,
    RegulatoryMappingSetStatus,
    RegulatoryMappingStatus,
    RegulatoryStatementMapping,
)
from pyaccountingkit.domain.reporting.regulatory_profile import (
    RegulatoryProfileStatus,
    RegulatoryReportingProfile,
)
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotStatus,
)
from pyaccountingkit.domain.reporting.statement_definition import (
    FinancialStatementDefinition,
    FinancialStatementType,
)
from pyaccountingkit.domain.reporting.statement_line import (
    StatementControlRole,
    StatementLineDefinition,
    StatementLineType,
    StatementSignConvention,
)
from pyaccountingkit.domain.reporting.trial_balance import TrialBalanceSnapshot

ENTITY = EntityId("release-0.3-entity")
PERIOD_ID = PeriodId("fy-2026")
JOURNAL_ID = JournalId("journal-ac")
AS_OF = date(2026, 12, 31)
SNAPSHOT_ID = "release-0.3-financial-snapshot"

_FEC_HEADER = "\t".join(
    (
        "JournalCode",
        "JournalLib",
        "EcritureNum",
        "EcritureDate",
        "CompteNum",
        "CompteLib",
        "CompAuxNum",
        "CompAuxLib",
        "PieceRef",
        "PieceDate",
        "EcritureLib",
        "Debit",
        "Credit",
        "EcritureLet",
        "DateLet",
        "ValidDate",
        "Montantdevise",
        "Idevise",
    )
)


@dataclass(frozen=True, slots=True)
class Release03PipelineResult:
    """Observable evidence from one complete 0.3.x execution."""

    source_checksum: str
    fec_valid: bool
    import_plan_checksum: str
    imported_entry_id: str
    ledger_entry_count: int
    audit_event_count: int
    same_store_replay_preserved_single_effect: bool
    trial_balance_checksum: str
    trial_balance_balanced: bool
    financial_result_checksum: str
    financial_control_passed: bool
    report_snapshot_checksum: str
    report_snapshot_published: bool
    regulatory_report_checksum: str
    regulatory_validation_checksum: str
    regulatory_validation_valid: bool
    export_payload_checksum: str
    evidence_checksum: str
    cash_amount: str
    supplier_amount: str
    regulatory_assets_amount: str
    regulatory_liabilities_equity_amount: str

    @property
    def replay_fingerprint(self) -> tuple[str, ...]:
        """Semantic values that must be identical across fresh executions."""
        return (
            self.source_checksum,
            self.imported_entry_id,
            self.trial_balance_checksum,
            self.financial_result_checksum,
            self.report_snapshot_checksum,
            self.regulatory_report_checksum,
            self.regulatory_validation_checksum,
            self.export_payload_checksum,
            self.evidence_checksum,
        )


def _fec_line(*, account: str, debit: str, credit: str, auxiliary: str = "") -> str:
    return "\t".join(
        (
            "AC",
            "Achats",
            "E1",
            "20261231",
            account,
            f"Compte {account}",
            auxiliary,
            "Fournisseur RC" if auxiliary else "",
            "RC-001",
            "20261231",
            "Qualification release 0.3",
            debit,
            credit,
            "",
            "",
            "20261231",
            "",
            "",
        )
    )


def _fec_payload() -> bytes:
    return (
        _FEC_HEADER
        + "\n"
        + _fec_line(account="512000", debit="100.00", credit="0")
        + "\n"
        + _fec_line(account="401000", debit="0", credit="100.00", auxiliary="SUP-RC")
        + "\n"
    ).encode()


def _company_chart() -> CompanyChartOfAccounts:
    return CompanyChartOfAccounts(
        entity_id=ENTITY,
        accounts=(
            CompanyAccount(
                id=AccountId("512000"),
                entity_id=ENTITY,
                code="512000",
                label="Banque",
            ),
            CompanyAccount(
                id=AccountId("401000"),
                entity_id=ENTITY,
                code="401000",
                label="Fournisseurs",
            ),
        ),
    )


def _chart_resolver(chart: CompanyChartOfAccounts) -> InMemoryVersionedCompanyChartResolver:
    versioned_chart = CompanyChart(
        chart_id="release-0.3-chart",
        entity_id=ENTITY,
        code="PCG",
        label="Release 0.3 qualification chart",
        primary_standard="fr-pcg",
        code_policy_id="numeric",
        reference_snapshot_id="pcg-chart-reference-2026",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=ChartStatus.ACTIVE,
                effective_from=date(2026, 1, 1),
            ),
        ),
    )
    return InMemoryVersionedCompanyChartResolver(versioned_chart, {"v1": chart})


def _build_import_plan(
    *,
    source_checksum: str,
    normalized_records: tuple[NormalizedImportRecord, ...],
    adapter: FECAdapter,
) -> ImportPlan:
    groups = adapter.grouping().group(normalized_records)
    account_mapper = ExplicitImportAccountMapper(
        {
            "512000": AccountId("512000"),
            "401000": AccountId("401000"),
        }
    )
    journal_mapper = ExplicitImportJournalMapper({"AC": JOURNAL_ID})
    entry_plans: list[ImportEntryPlan] = []

    for group in groups:
        source_journal = group.source_journal_code
        if source_journal is None:
            raise RuntimeError("release qualification FEC group must carry a source journal")
        journal_decision = journal_mapper.resolve(source_journal)
        if not journal_decision.executable or journal_decision.journal_id is None:
            raise RuntimeError("release qualification journal mapping must be executable")

        planned_lines: list[ImportPlannedLine] = []
        for record in group.records:
            account_decision = account_mapper.resolve(record.source_account_code)
            if not account_decision.executable or account_decision.target_account_id is None:
                raise RuntimeError("release qualification account mapping must be executable")
            planned_lines.append(
                ImportPlannedLine(
                    source_record_ref=record.source_record_ref,
                    account_id=account_decision.target_account_id,
                    debit=record.debit,
                    credit=record.credit,
                )
            )

        entry_plans.append(
            ImportEntryPlan(
                source_entry_key=group.source_entry_key,
                accounting_date=group.accounting_date,
                journal_id=journal_decision.journal_id,
                period_id=PERIOD_ID,
                lines=tuple(planned_lines),
                description="Release 0.3 FEC qualification",
            )
        )

    return ImportPlan(
        batch_id="release-0.3-batch",
        entity_id=ENTITY,
        source_checksum=source_checksum,
        adapter_id=adapter.adapter_id,
        adapter_version=adapter.adapter_version,
        mapping_version="release-0.3-import-map-v1",
        chart_version="v1",
        entry_plans=tuple(entry_plans),
        expected_line_count=len(normalized_records),
    )


def _statement_definition() -> FinancialStatementDefinition:
    return FinancialStatementDefinition(
        definition_id="release-0.3-balance-sheet",
        code="RC_BALANCE_SHEET",
        statement_type=FinancialStatementType.BALANCE_SHEET,
        version="1",
        effective_from=date(2026, 1, 1),
        lines=(
            StatementLineDefinition(
                line_id="assets-total",
                code="ASSETS_TOTAL",
                label="Total assets",
                line_type=StatementLineType.TOTAL,
                order=20,
                control_role=StatementControlRole.ASSETS_TOTAL,
            ),
            StatementLineDefinition(
                line_id="cash",
                code="CASH",
                label="Cash",
                line_type=StatementLineType.DETAIL,
                order=10,
                parent_line_id="assets-total",
            ),
            StatementLineDefinition(
                line_id="le-total",
                code="LE_TOTAL",
                label="Liabilities and equity",
                line_type=StatementLineType.TOTAL,
                order=40,
                control_role=StatementControlRole.LIABILITIES_EQUITY_TOTAL,
            ),
            StatementLineDefinition(
                line_id="suppliers",
                code="SUPPLIERS",
                label="Suppliers",
                line_type=StatementLineType.DETAIL,
                order=30,
                parent_line_id="le-total",
                sign_convention=StatementSignConvention.CREDIT_POSITIVE,
            ),
        ),
    )


def _statement_mapping_set(definition: FinancialStatementDefinition) -> StatementMappingSet:
    return StatementMappingSet(
        mapping_set_id="release-0.3-statement-map",
        accounting_entity_id=ENTITY,
        statement_definition_id=definition.definition_id,
        version="1",
        status=StatementMappingSetStatus.ACTIVE,
        mappings=(
            StatementAccountMapping(
                mapping_id="cash-map",
                company_account_id="512000",
                statement_line_code="CASH",
                allocation=Decimal("1"),
                mapping_status=StatementMappingStatus.VALIDATED,
                provenance=MappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
            StatementAccountMapping(
                mapping_id="supplier-map",
                company_account_id="401000",
                statement_line_code="SUPPLIERS",
                allocation=Decimal("1"),
                mapping_status=StatementMappingStatus.VALIDATED,
                provenance=MappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
        ),
        effective_from=date(2026, 1, 1),
    )


def _regulatory_coordinates(
    definition: FinancialStatementDefinition,
) -> tuple[
    ReferenceReportingModel,
    RegulatoryReportingProfile,
    RegulatoryMappingSet,
    RegulatoryExportDefinition,
]:
    model = ReferenceReportingModel(
        model_id="release-0.3-pcg-model",
        model_code="BALANCE_SHEET",
        framework="PCG",
        edition="2026",
        reference_snapshot_id="release-0.3-pcg-reference-2026",
        reference_snapshot_checksum="d" * 64,
        nodes=(
            ReferenceReportingNode(
                node_id="reg-assets",
                code="REG_ASSETS",
                label="Regulatory assets",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=1,
                required=True,
                human_validation_required=True,
                account_hints_executable=False,
                account_hints=("5*",),
                provenance="release-0.3-qualified-reference",
            ),
            ReferenceReportingNode(
                node_id="reg-le",
                code="REG_LIABILITIES_EQUITY",
                label="Regulatory liabilities and equity",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=2,
                required=True,
                account_hints_executable=False,
                provenance="release-0.3-qualified-reference",
            ),
        ),
    )
    profile = RegulatoryReportingProfile(
        profile_id="release-0.3-pcg-profile",
        code="PCG_RELEASE_0_3",
        framework="PCG",
        jurisdiction="FR",
        edition="2026",
        version="1",
        status=RegulatoryProfileStatus.ACTIVE,
        reference_snapshot_id=model.reference_snapshot_id,
        reference_snapshot_checksum=model.reference_snapshot_checksum,
        financial_statement_definition_ids=(definition.definition_id,),
        regulatory_mapping_set_id="release-0.3-reg-map",
        export_definition_ids=("release-0.3-json",),
        effective_from=date(2026, 1, 1),
        accounting_entity_id=ENTITY,
    )
    mapping_set = RegulatoryMappingSet(
        mapping_set_id="release-0.3-reg-map",
        accounting_entity_id=ENTITY,
        profile_id=profile.profile_id,
        reference_model_id=model.model_id,
        version="1",
        status=RegulatoryMappingSetStatus.ACTIVE,
        mappings=(
            RegulatoryStatementMapping(
                mapping_id="reg-assets-map",
                statement_line_code="ASSETS_TOTAL",
                reference_node_id="reg-assets",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
            RegulatoryStatementMapping(
                mapping_id="reg-le-map",
                statement_line_code="LE_TOTAL",
                reference_node_id="reg-le",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
        ),
        effective_from=date(2026, 1, 1),
    )
    export_definition = RegulatoryExportDefinition(
        export_definition_id="release-0.3-json",
        code="RELEASE_0_3_JSON",
        version="1",
        profile_id=profile.profile_id,
        renderer_id="canonical-json-v1",
        media_type="application/json",
        schema_version="1",
        effective_from=date(2026, 1, 1),
        required_node_ids=("reg-assets", "reg-le"),
    )
    return model, profile, mapping_set, export_definition


def run_release_0_3_pipeline(
    *,
    snapshot_created_at: datetime,
    export_time: datetime,
    id_seed: int,
    replay_import_in_same_store: bool,
) -> Release03PipelineResult:
    """Run the complete 0.3.x source-to-evidence chain with production components."""
    payload = _fec_payload()
    adapter = FECAdapter(
        FECSourceDescriptor(
            fiscal_year_start=date(2026, 1, 1),
            fiscal_year_end=date(2026, 12, 31),
        )
    )
    artifact = SourceArtifact.from_bytes(
        artifact_ref="fec:release-0.3",
        source_type="FEC",
        payload=payload,
        acquired_at=datetime(2026, 12, 31, 12, 0, tzinfo=UTC),
        filename="123456789FEC20261231.txt",
        media_type="text/plain",
    )
    parsed = adapter.parse(artifact, batch_id="release-0.3-batch", payload=payload)
    normalized = adapter.normalizer().normalize(parsed, batch_id="release-0.3-batch")
    fec_report = adapter.validator().report(
        batch_id="release-0.3-batch",
        raw_records=parsed.records,
        normalized_records=normalized,
    )
    plan = _build_import_plan(
        source_checksum=artifact.checksum,
        normalized_records=normalized,
        adapter=adapter,
    )

    store = InMemoryStore()
    uow_factory = InMemoryUnitOfWorkFactory(store)
    with uow_factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PERIOD_ID,
                entity_id=ENTITY,
                fiscal_year_id=FiscalYearId("fy-2026"),
                start_date=date(2026, 1, 1),
                end_date=AS_OF,
                status=ClosingStatus.OPEN,
            )
        )
        uow.journals.add(
            Journal(
                id=JOURNAL_ID,
                entity_id=ENTITY,
                code="AC",
                label="Achats",
            )
        )
        uow.commit()

    chart = _company_chart()
    posting = PostingOrchestrator(
        uow_factory,
        _chart_resolver(chart),
        PostingService(clock=FrozenClock(datetime(2026, 12, 31, 18, 0, tzinfo=UTC))),
    )
    import_service = ImportExecutionService(posting)
    imported = import_service.execute(
        plan,
        currency=EUR,
        actor_id="release-qualification",
        source_checksum=artifact.checksum,
        adapter_version=adapter.adapter_version,
        mapping_version=plan.mapping_version,
        chart_version=plan.chart_version,
    )

    replay_preserved_single_effect = True
    if replay_import_in_same_store:
        replayed = import_service.execute(
            plan,
            currency=EUR,
            actor_id="release-qualification",
            source_checksum=artifact.checksum,
            adapter_version=adapter.adapter_version,
            mapping_version=plan.mapping_version,
            chart_version=plan.chart_version,
        )
        replay_preserved_single_effect = (
            replayed.created_entry_ids == imported.created_entry_ids
            and len(store.entries) == 1
            and len(store.audit_log) == 1
        )

    trial_balance = TrialBalanceQuery(uow_factory, chart).balance_for(
        PERIOD_ID,
        TrialBalanceSnapshot.ADJUSTED,
    )
    definition = _statement_definition()
    statement_mapping_set = _statement_mapping_set(definition)
    financial = FinancialStatementEngine().build(
        FinancialStatementBuildRequest(
            accounting_entity_id=ENTITY,
            as_of=AS_OF,
            reporting_source=trial_balance,
            statement_definition=definition,
            mapping_set=statement_mapping_set,
        )
    )
    snapshot = ReportSnapshot.from_result(
        snapshot_id=SNAPSHOT_ID,
        result=financial,
        created_at=snapshot_created_at,
    )

    model, profile, regulatory_mapping_set, export_definition = _regulatory_coordinates(definition)
    regulatory = RegulatoryReportingService(
        InMemoryReferenceReportingModelProvider((model,))
    ).build(
        snapshot=snapshot,
        profile=profile,
        mapping_set=regulatory_mapping_set,
        model_code=model.model_code,
    )
    ids = iter((id_seed, id_seed + 1))
    exported = RegulatoryExportService(
        renderer=CanonicalJSONRegulatoryRenderer(),
        clock=FrozenClock(export_time),
        id_factory=IdFactory(lambda _: next(ids)),
    ).export(
        report=regulatory.report,
        validation=regulatory.validation,
        profile=profile,
        definition=export_definition,
    )

    imported_entry_id = str(imported.created_entry_ids[0])
    cash = financial.line("CASH").amount
    supplier = financial.line("SUPPLIERS").amount
    regulatory_assets = regulatory.report.node("REG_ASSETS").amount
    regulatory_le = regulatory.report.node("REG_LIABILITIES_EQUITY").amount
    if regulatory_assets is None or regulatory_le is None:
        raise RuntimeError("release qualification regulatory totals must be monetary")

    return Release03PipelineResult(
        source_checksum=artifact.checksum,
        fec_valid=fec_report.valid,
        import_plan_checksum=plan.checksum,
        imported_entry_id=imported_entry_id,
        ledger_entry_count=len(store.entries),
        audit_event_count=len(store.audit_log),
        same_store_replay_preserved_single_effect=replay_preserved_single_effect,
        trial_balance_checksum=trial_balance.checksum,
        trial_balance_balanced=trial_balance.total_debit == trial_balance.total_credit,
        financial_result_checksum=financial.checksum,
        financial_control_passed=all(
            control.status is StatementControlStatus.PASS for control in financial.controls
        ),
        report_snapshot_checksum=snapshot.checksum,
        report_snapshot_published=snapshot.status is ReportSnapshotStatus.PUBLISHED,
        regulatory_report_checksum=regulatory.report.checksum,
        regulatory_validation_checksum=regulatory.validation.checksum,
        regulatory_validation_valid=regulatory.validation.is_valid,
        export_payload_checksum=exported.artifact.payload_checksum,
        evidence_checksum=exported.evidence.checksum,
        cash_amount=str(cash.amount),
        supplier_amount=str(supplier.amount),
        regulatory_assets_amount=str(regulatory_assets.amount),
        regulatory_liabilities_equity_amount=str(regulatory_le.amount),
    )


__all__ = ["Release03PipelineResult", "run_release_0_3_pipeline"]
