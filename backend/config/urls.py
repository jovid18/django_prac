from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    # ★ リフレッシュ Cookie の Path=/api/auth に合わせてある。
    #   ここを変えるなら settings の REFRESH_COOKIE_PATH も一緒に直す。
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.libraries.urls")),
]
