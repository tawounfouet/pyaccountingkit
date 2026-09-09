from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from config.views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.analytics.urls")),
    path("organizations/", include("apps.organizations.urls")),
    path("accounting/", include("apps.accounting.urls")),
    path("imports/", include("apps.imports.urls")),
    path("reports/", include("apps.reporting.urls")),
    path("statements/", include("apps.financial_statements.urls")),
    path("controls/", include("apps.controls.urls")),
    path("closing/", include("apps.closing.urls")),
    path("referentials/", include("apps.referentials.urls")),
    path("audit/", include("apps.audit.urls")),
    path("exports/", include("apps.exports.urls")),
    path("scenarios/", include("apps.scenarios.urls")),
]
