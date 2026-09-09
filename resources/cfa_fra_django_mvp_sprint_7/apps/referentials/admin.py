from django.contrib import admin
from .models import (
    AccountMapping,
    AccountingFramework,
    FrameworkAccount,
    FrameworkVersion,
    StatementDefinition,
    StatementLine,
)

admin.site.register([
    AccountingFramework,
    FrameworkVersion,
    FrameworkAccount,
    StatementDefinition,
    StatementLine,
    AccountMapping,
])
