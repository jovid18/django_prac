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

# ★ ヘルスチェックのパスだけ HTTPS リダイレクトから除外する。
#
# Render の内部ヘルスチェックは X-Forwarded-Proto を付けずにコンテナを直接叩く
# ことがある。すると Django は「HTTP で来た」と判断して 301 を返し、Render は
# 2xx でないためチェック失敗と見なしてインスタンスをルーティングから外す。
# 次の試行では通るので、また投入される —— これを繰り返して
# 「プロセスは生きているのにリクエストの半分が x-render-routing: no-server で
# 404 になる」という症状が出る。
#
# 正規表現の先頭にスラッシュは付けない（Django が lstrip("/") した後の値と照合するため）。
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]

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
