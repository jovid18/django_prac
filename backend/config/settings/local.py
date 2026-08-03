"""ローカル開発用（docker compose）。"""

import os

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "api"]

# ブラウザは localhost:5173 しか見ないので、本来 Vite の proxy 経由で
# 同一オリジンになり CORS は発生しない。
# ただしホストから直接 :8000 を叩いて試すことがあるので許可しておく。
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# HTTP なので SameSite=None は使えない（ブラウザが Secure 必須にするため）。
REFRESH_COOKIE_SECURE = False
REFRESH_COOKIE_SAMESITE = "Lax"
