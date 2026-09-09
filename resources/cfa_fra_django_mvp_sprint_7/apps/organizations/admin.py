from django.contrib import admin
from .models import (
    AccountingPeriod,
    AccountingSettings,
    FiscalYear,
    Organization,
    OrganizationMembership,
)

admin.site.register([
    Organization,
    OrganizationMembership,
    FiscalYear,
    AccountingPeriod,
    AccountingSettings,
])
