from django.contrib import admin
from .models import Scenario, ScenarioVariable

admin.site.register([Scenario, ScenarioVariable])
