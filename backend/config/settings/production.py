"""本番用（Render の Web Service）。"""

import os

from .base import *  # noqa: F403
from .base import MIDDLEWARE

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.environ["DJANGO_ALLOWED_HOSTS"].split(",") if h.strip()]

# --- CORS / CSRF ----------------------------------------------------------
# フロント（Static Site）と API が別ホストになるため必須。
FRONTEND_ORIGIN = os.environ["FRONTEND_ORIGIN"].rstrip("/")
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]

# --- HTTPS ----------------------------------------------------------------
# Render は TLS を終端してから HTTP でコンテナに渡す。
# この 2 行はセットで書くこと。SECURE_PROXY_SSL_HEADER が無いまま
# SECURE_SSL_REDIRECT を有効にすると無限リダイレクトになる。
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# --- リフレッシュ Cookie --------------------------------------------------
# クロスサイトで送るので None + Secure が必須。
REFRESH_COOKIE_SECURE = True
REFRESH_COOKIE_SAMESITE = "None"

# --- 静的ファイル（Django Admin 用）--------------------------------------
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
