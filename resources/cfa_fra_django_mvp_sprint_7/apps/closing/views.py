from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

class ClosingView(LoginRequiredMixin, TemplateView):
    template_name = "closing/index.html"
