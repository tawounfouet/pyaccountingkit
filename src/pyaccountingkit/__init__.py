"""pyaccountingkit: a Python toolkit for double-entry accounting."""

from importlib.metadata import version as _distribution_version

__version__ = _distribution_version("pyaccountingkit")
__all__ = ["__version__"]
