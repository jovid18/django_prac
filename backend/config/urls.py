from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    # Day 2 で追加: path("api/", include("apps.libraries.urls")),
    # Day 4 で追加: path("api/auth/", include("apps.accounts.urls")),
]
