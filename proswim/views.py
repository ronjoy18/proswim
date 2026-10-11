from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import dashboard_redirect

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("catalog.urls")),
    path("accounts/", include("accounts.urls")),
    path("clients/", include("clients.urls")),
    path("orders/", include("orders.urls")),

    path("dashboard/", dashboard_redirect, name="dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)