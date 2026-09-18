"""Primary framework-neutral composition root for PyAccountingKit consumers."""

from __future__ import annotations

from pyaccountingkit.public.analysis import FinancialAnalysisAPI
from pyaccountingkit.public.charts import ChartsAPI
from pyaccountingkit.public.closing import ClosingAPI
from pyaccountingkit.public.controls import ControlsAPI
from pyaccountingkit.public.entries import EntriesAPI
from pyaccountingkit.public.imports import ImportsAPI
from pyaccountingkit.public.ledger import LedgerAPI
from pyaccountingkit.public.references import ReferencesAPI
from pyaccountingkit.public.reporting import RegulatoryReportingAPI
from pyaccountingkit.public.statements import StatementsAPI
from pyaccountingkit.public.subledgers import SubledgersAPI


class AccountingApplication:
    """Single public entry point composed from framework-neutral application services.

    LOT-21 deliberately accepts already-composed namespace services rather than exposing
    repositories, ORM sessions or transaction controls. Missing services fail closed at the
    operation boundary with PublicOperationUnavailableError.
    """

    __slots__ = (
        "references",
        "charts",
        "entries",
        "ledger",
        "closing",
        "controls",
        "imports",
        "statements",
        "reporting",
        "analysis",
        "subledgers",
    )

    def __init__(
        self,
        *,
        references: object | None = None,
        charts: object | None = None,
        entries: object | None = None,
        ledger: object | None = None,
        closing: object | None = None,
        controls: object | None = None,
        imports: object | None = None,
        statements: object | None = None,
        reporting: object | None = None,
        analysis: object | None = None,
        subledgers: object | None = None,
    ) -> None:
        self.references = ReferencesAPI(references)
        self.charts = ChartsAPI(charts)
        self.entries = EntriesAPI(entries)
        self.ledger = LedgerAPI(ledger)
        self.closing = ClosingAPI(closing)
        self.controls = ControlsAPI(controls)
        self.imports = ImportsAPI(imports)
        self.statements = StatementsAPI(statements)
        self.reporting = RegulatoryReportingAPI(reporting)
        self.analysis = FinancialAnalysisAPI(analysis)
        self.subledgers = SubledgersAPI(subledgers)


__all__ = ["AccountingApplication"]
