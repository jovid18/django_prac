# マルチステージ。ローカルと本番で同じ Dockerfile を使う。
#
#   dev  … 開発ツール（ruff / pytest）を含む。compose が target: dev で使う
#   prod … 実行に必要なものだけ。最終ステージなので target 未指定だとこれになる
#          （Render は target を指定せずにビルドする）

# --- 共通の土台 ------------------------------------------------------------
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# uv 本体を公式イメージからコピーする（pip 経由より速く、バージョンも固定できる）
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

# psycopg[binary] を使うのでコンパイラは不要。
# ソースビルド版の psycopg に切り替える場合は libpq-dev / gcc をここで入れる。

# ★ 依存だけ先に入れてレイヤを分ける。
#   ソースを 1 行直すたびに全依存を入れ直すのを防ぐ。
COPY pyproject.toml uv.lock ./


# --- 開発用 ----------------------------------------------------------------
FROM base AS dev

RUN uv sync --frozen
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# --- 本番用（最終ステージ）------------------------------------------------
FROM base AS prod

RUN uv sync --frozen --no-dev
COPY . .
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
