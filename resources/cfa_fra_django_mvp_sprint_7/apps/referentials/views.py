from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db import models

from .models import FrameworkAccount

class FrameworkAccountListView(LoginRequiredMixin, ListView):
    model = FrameworkAccount
    template_name = "referentials/accounts.html"
    context_object_name = "accounts"
    paginate_by = 50

    def get_queryset(self):
        qs = (
            FrameworkAccount.objects
            .select_related("version", "version__framework")
            .order_by("version__framework__code", "code")
        )
        q = self.request.GET.get("q", "").strip()
        framework = self.request.GET.get("framework", "").strip()
        if q:
            qs = qs.filter(models.Q(code__icontains=q) | models.Q(name__icontains=q))
        if framework:
            qs = qs.filter(version__framework__code=framework)
        return qs
