from pathlib import Path

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import DetailView, ListView

from apps.organizations.mixins import ActiveOrganizationMixin

from .models import ExportJob


class ExportListView(ActiveOrganizationMixin, ListView):
    model = ExportJob
    template_name = "exports/list.html"
    context_object_name = "jobs"
    paginate_by = 30

    def get_queryset(self):
        return (
            ExportJob.objects.filter(
                organization=self.organization,
            )
            .select_related(
                "requested_by",
                "snapshot",
                "regulatory_profile",
                "regulatory_profile__target_version",
                "regulatory_profile__target_version__framework",
            )
            .order_by("-created_at")
        )


class ExportDetailView(ActiveOrganizationMixin, DetailView):
    model = ExportJob
    template_name = "exports/detail.html"
    context_object_name = "job"

    def get_queryset(self):
        return ExportJob.objects.filter(
            organization=self.organization,
        ).select_related(
            "requested_by",
            "snapshot",
            "regulatory_profile",
            "regulatory_profile__target_version",
            "regulatory_profile__target_version__framework",
        )


class ExportDownloadView(ActiveOrganizationMixin, View):
    def get(self, request, pk):
        job = get_object_or_404(
            ExportJob,
            pk=pk,
            organization=self.organization,
        )
        if (
            job.status != ExportJob.Status.DONE
            or not job.file
        ):
            raise Http404("Export non disponible.")

        file_handle = job.file.open("rb")
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=Path(job.file.name).name,
            content_type=job.mime_type or "application/octet-stream",
        )
