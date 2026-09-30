"""Executable CFA FRA golden parity qualification for LOT-25."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from pyaccountingkit.adapters.imports.fec import (
    FECAdapter,
    FECSourceDescriptor,
    discover_fec,
)
from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.application.ledger.reversal_orchestrator import ReversalOrchestrator
from pyaccountingkit.application.reporting.trial_balance_query import TrialBalanceQuery
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import XAF
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)
from pyaccountingkit.domain.imports.source_artifact import SourceArtifact
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import (
    EntryStatus,
    EntryType,
    JournalEntry,
)
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.reporting.trial_balance import TrialBalanceSnapshot
from pyaccountingkit.integrations.cfa_fra import load_golden_fixture

FIXTURES = Path(__file__).parent / "fixtures"
ENTITY = EntityId("cfa-ent")
PERIOD = PeriodId("p-2025-01")
JOURNAL = JournalId("jod")
NOW = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)


def _money(value: str) -> Money:
    return Money.from_str(value, XAF)


def _chart() -> CompanyChartOfAccounts:
    labels = {
        "10110000": "Capital",
        "40810000": "Charges à payer",
        "401000": "Fournisseurs",
        "512000": "Banque",
        "57110000": "Caisse",
        "66100000": "Loyer",
    }
    return CompanyChartOfAccounts(
        entity_id=ENTITY,
        accounts=tuple(
            CompanyAccount(
                id=AccountId(code),
                entity_id=ENTITY,
                code=code,
                label=label,
            )
            for code, label in labels.items()
        ),
    )


def _chart_resolver(chart: CompanyChartOfAccounts) -> InMemoryVersionedCompanyChartResolver:
    definition = CompanyChart(
        chart_id="cfa-chart",
        entity_id=ENTITY,
        code="CFA",
        label="CFA FRA golden chart",
        primary_standard="cfa-fra-mvp",
        code_policy_id="numeric",
        reference_snapshot_id="cfa-fra-sprint-7",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=ChartStatus.ACTIVE,
                effective_from=date(2025, 1, 1),
            ),
        ),
    )
    return InMemoryVersionedCompanyChartResolver(definition, {"v1": chart})


def _accounting_factory() -> tuple[InMemoryUnitOfWorkFactory, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PERIOD,
                entity_id=ENTITY,
                fiscal_year_id=FiscalYearId("fy-2025"),
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
            )
        )
        uow.journals.add(
            Journal(
                id=JOURNAL,
                entity_id=ENTITY,
                code="JOD",
                label="Opérations diverses",
            )
        )
        uow.commit()
    return factory, store


def test_posting_and_reversal_match_cfa_fra_golden() -> None:
    fixture = load_golden_fixture(FIXTURES / "posting_reversal.json")
    factory, _ = _accounting_factory()
    posting = PostingOrchestrator(
        factory,
        _chart_resolver(_chart()),
        PostingService(clock=FrozenClock(NOW)),
    )
    entry = JournalEntry(
        id=EntryId("cfa-post-001"),
        journal_id=JOURNAL,
        period_id=PERIOD,
        entry_date=date(2025, 1, 15),
        description="Écriture Sprint 3",
        lines=(
            JournalLine(
                account_id=AccountId("57110000"),
                debit=_money("1000"),
                credit=_money("0"),
            ),
            JournalLine(
                account_id=AccountId("10110000"),
                debit=_money("0"),
                credit=_money("1000"),
            ),
        ),
    ).validate()
    posted = posting.post(entry, actor_id="golden")

    reversal = ReversalOrchestrator(
        factory,
        reversal_id_factory=lambda: EntryId("cfa-rev-001"),
    ).reverse(
        EntryId("cfa-post-001"),
        PERIOD,
        date(2025, 1, 20),
        actor_id="golden",
    )

    actual = {
        "posting_status": posted.posted_entry.status.value,
        "posting_type": posted.posted_entry.entry_type.value,
        "posting_total_debit": posted.posted_entry.total_debit().amount,
        "posting_total_credit": posted.posted_entry.total_credit().amount,
        "original_after_reversal_status": reversal.marked_original.status.value,
        "reversal_status": reversal.reversal_entry.status.value,
        "reversal_type": reversal.reversal_entry.entry_type.value,
        "reversal_of": str(reversal.reversal_entry.reversal_of_id),
        "reversal_lines": [
            {
                "account": str(line.account_id),
                "debit": line.debit.amount,
                "credit": line.credit.amount,
            }
            for line in reversal.reversal_entry.lines
        ],
    }
    parity = fixture.compare(actual)
    assert parity.exact is True
    assert parity.qualified is True


FEC_HEADER = "\t".join(
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


def _fec_line(account: str, debit: str, credit: str) -> str:
    return "\t".join(
        (
            "AC",
            "Achats",
            "E1",
            "20250115",
            account,
            f"Compte {account}",
            "",
            "",
            "P-001",
            "20250115",
            "Facture fournisseur",
            debit,
            credit,
            "",
            "",
            "20250116",
            "",
            "",
        )
    )


def _fec_payload() -> bytes:
    return (
        FEC_HEADER
        + "\n"
        + _fec_line("401000", "1000", "0")
        + "\n"
        + _fec_line("512000", "0", "1000")
        + "\n"
    ).encode()


def test_fec_pipeline_matches_cfa_fra_golden() -> None:
    fixture = load_golden_fixture(FIXTURES / "fec_import.json")
    payload = _fec_payload()
    artifact = SourceArtifact.from_bytes(
        artifact_ref="cfa-fra:fec:2025",
        source_type="FEC",
        payload=payload,
        acquired_at=datetime(2025, 12, 31, tzinfo=UTC),
        filename="CFAFRA2025.txt",
        media_type="text/plain",
    )
    adapter = FECAdapter(
        FECSourceDescriptor(
            fiscal_year_start=date(2025, 1, 1),
            fiscal_year_end=date(2025, 12, 31),
            default_currency="XAF",
        )
    )
    parsed = adapter.parse(artifact, batch_id="cfa-fec-001", payload=payload)
    normalized = adapter.normalizer().normalize(parsed, batch_id="cfa-fec-001")
    groups = adapter.grouping().group(normalized)
    report = adapter.validator().report(
        batch_id="cfa-fec-001",
        raw_records=parsed.records,
        normalized_records=normalized,
    )
    discovery = discover_fec(normalized)

    actual = {
        "raw_record_count": len(parsed.records),
        "source_line_numbers": [record.source_line_number for record in parsed.records],
        "raw_rows_preserved": all(len(record.raw_fields) == 18 for record in parsed.records),
        "row_checksums_present": all(record.row_checksum is not None for record in parsed.records),
        "normalized_entry_keys": [record.source_entry_key.value for record in normalized],
        "group_count": len(groups),
        "group_balanced": all(group.balanced for group in groups),
        "total_debit": report.total_debit,
        "total_credit": report.total_credit,
        "valid": report.valid,
        "source_accounts": [code for code, _ in discovery.source_accounts],
        "source_journals": [code for code, _ in discovery.source_journals],
    }
    parity = fixture.compare(actual)
    assert parity.exact is True
    assert parity.qualified is True


def _posted_entry(
    entry_id: str,
    entry_type: EntryType,
    debit_account: str,
    credit_account: str,
    amount: str,
) -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JOURNAL,
        period_id=PERIOD,
        entry_date=date(2025, 1, 15),
        description=entry_id,
        entry_type=entry_type,
        status=EntryStatus.POSTED,
        posted_at=NOW,
        lines=(
            JournalLine(
                account_id=AccountId(debit_account),
                debit=_money(amount),
                credit=_money("0"),
            ),
            JournalLine(
                account_id=AccountId(credit_account),
                debit=_money("0"),
                credit=_money(amount),
            ),
        ),
    )


def _balances(query: TrialBalanceQuery, snapshot: TrialBalanceSnapshot) -> dict[str, object]:
    balance = query.balance_for(PERIOD, snapshot)
    return {line.account_code: line.balance.amount for line in balance.lines}


def test_trial_balance_variants_match_cfa_fra_golden() -> None:
    fixture = load_golden_fixture(FIXTURES / "trial_balance_variants.json")
    factory, _ = _accounting_factory()
    with factory.open() as uow:
        for entry in (
            _posted_entry(
                "opening",
                EntryType.OPENING,
                "57110000",
                "10110000",
                "1000",
            ),
            _posted_entry(
                "normal",
                EntryType.NORMAL,
                "66100000",
                "57110000",
                "200",
            ),
            _posted_entry(
                "adjusting",
                EntryType.ADJUSTING,
                "66100000",
                "40810000",
                "50",
            ),
            _posted_entry(
                "closing",
                EntryType.CLOSING,
                "10110000",
                "66100000",
                "250",
            ),
        ):
            uow.entries.add(entry)
        uow.commit()

    query = TrialBalanceQuery(factory, _chart())
    actual = {
        TrialBalanceSnapshot.BEFORE_ADJUSTMENTS.value: _balances(
            query, TrialBalanceSnapshot.BEFORE_ADJUSTMENTS
        ),
        TrialBalanceSnapshot.ADJUSTED.value: _balances(query, TrialBalanceSnapshot.ADJUSTED),
        TrialBalanceSnapshot.POST_CLOSING.value: _balances(
            query, TrialBalanceSnapshot.POST_CLOSING
        ),
    }
    parity = fixture.compare(actual)
    assert parity.exact is True
    assert parity.qualified is True
