from django.contrib import admin
from .models import AccountingControl, ControlResult, ControlRun

admin.site.register([AccountingControl, ControlRun, ControlResult])
