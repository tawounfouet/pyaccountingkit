"""pyaccountingkit: a Python toolkit for double-entry accounting."""

from importlib.metadata import version as _distribution_version

from pyaccountingkit.core.currency import Currency, CurrencyCode
from pyaccountingkit.core.money import Money
from pyaccountingkit.public.application import AccountingApplication
from pyaccountingkit.public.context import CommandContext

__version__ = _distribution_version("pyaccountingkit")

__all__ = [
    "AccountingApplication",
    "CommandContext",
    "Currency",
    "CurrencyCode",
    "Money",
    "__version__",
]
