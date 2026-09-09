from django.contrib import admin
from .models import ClosingEntryLink, ClosingRun

admin.site.register([ClosingRun, ClosingEntryLink])
