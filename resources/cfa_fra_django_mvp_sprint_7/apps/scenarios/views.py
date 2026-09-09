from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

class ScenarioListView(LoginRequiredMixin, TemplateView):
    template_name = "scenarios/list.html"
