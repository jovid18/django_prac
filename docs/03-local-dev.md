# 03. ローカル開発環境（docker compose）

## ゴール

リポジトリを clone して `docker compose up` を打つだけで、ブラウザで `http://localhost:5173` が開き、地図と API が動いている状態。**ホストに Python も Node も入っていなくてよい**ことを目標にする。

## 前提

- Docker Desktop（もしくは OrbStack など）がインストール済み
- ポート `5173` / `8000` / `5432` が空いている

## `docker-compose.yml`（たたき台）

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: django_prac
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"          # ホストの GUI クライアントから覗きたい場合のみ
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d django_prac"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build:
      context: ./backend
    command: python manage.py runserver 0.0.0.0:8000
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
      DJANGO_SECRET_KEY: dev-only-not-a-real-secret
      DATABASE_URL: postgres://postgres:postgres@db:5432/django_prac
      GOOGLE_OAUTH_CLIENT_ID: ${GOOGLE_OAUTH_CLIENT_ID}
      CORS_ALLOWED_ORIGINS: http://localhost:5173
    volumes:
      - ./backend:/app        # ホットリロードのためソースをマウント
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    command: npm run dev -- --host 0.0.0.0
    environment:
      VITE_API_BASE_URL: ""                     # 空 = 相対パス。Vite の proxy に任せる
      VITE_GOOGLE_OAUTH_CLIENT_ID: ${GOOGLE_OAUTH_CLIENT_ID}
    volumes:
      - ./frontend:/app
      - /app/node_modules      # ホストの node_modules で上書きされないようにする
    ports:
      - "5173:5173"
    depends_on:
      - api

volumes:
  pgdata:
```

### 押さえておきたい点

| 箇所 | なぜそう書くか |
|---|---|
| `depends_on: condition: service_healthy` | `depends_on` だけでは「コンテナが起動した」までしか保証されない。Postgres が接続を受け付ける前に Django が起動して落ちるのを防ぐ |
| `volumes: - /app/node_modules` | 匿名ボリュームでコンテナ内の `node_modules` を保護する。これが無いと、ホストの `frontend/` をマウントした瞬間にコンテナ内の `node_modules` が消える（Node の Docker 開発で一番ハマる箇所） |
| `--host 0.0.0.0` | Vite は既定で `localhost` にしか bind しない。コンテナ内の `localhost` はホストからは見えないので必須 |
| `DATABASE_URL` を渡す | 本番の Render と同じ変数名。設定コードに分岐を作らないため（`02-architecture.md` 参照） |
| `.env` は commit しない | `${GOOGLE_OAUTH_CLIENT_ID}` は compose がリポジトリ直下の `.env` から読む。`.env.example` だけを commit する |

## `backend/Dockerfile`（ローカルとデプロイで共用）

```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg[binary] を使うのでビルドツールは基本不要。
# ソースビルド版の psycopg に切り替える場合は libpq-dev / gcc をここで入れる。
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 8000

# デプロイ時のデフォルト。ローカルは compose の command で上書きされる。
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

> 依存管理を `uv` にする場合は `pip install` の代わりに `uv sync --frozen` を使い、`uv.lock` を commit する。どちらでもよいが **Day 0 で決めて途中で変えない**こと。

## `frontend/Dockerfile.dev`

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

デプロイ時は Render の Static Site が `npm ci && npm run build` を直接実行するので、**フロントに本番用 Dockerfile は要らない**。

## Vite の proxy 設定

```ts
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://api:8000",   // compose のサービス名。ホスト直実行なら localhost:8000
        changeOrigin: true,
      },
    },
  },
});
```

> `target` にコンテナのサービス名 `api` を書いているため、**この設定のままホストで `npm run dev` を叩くと解決できない**。両対応にしたいなら `target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000"` として compose 側から渡す。

## 初回セットアップ手順

```bash
# 1. 環境変数ファイルを作る
cp .env.example .env
# .env を開いて GOOGLE_OAUTH_CLIENT_ID を埋める（06-auth.md 参照）
# まだ無ければ空のままでよい。ID/PW ログインだけは動く。

# 2. ビルドして起動
docker compose up --build

# 3. 別ターミナルでマイグレーション
docker compose exec api python manage.py migrate

# 4. 図書館データを投入（04-data-model.md 参照）
docker compose exec api python manage.py loaddata libraries

# 5. 管理者ユーザーを作る
docker compose exec api python manage.py createsuperuser
```

確認先:

| URL | 内容 |
|---|---|
| http://localhost:5173 | フロント |
| http://localhost:8000/api/health/ | API の疎通 |
| http://localhost:8000/admin/ | Django Admin |

## よく使うコマンド

```bash
docker compose up                      # 起動
docker compose up --build              # 依存を変えたとき
docker compose down                    # 停止
docker compose down -v                 # DB のデータごと消す（作り直したいとき）
docker compose logs -f api             # API のログを追う

docker compose exec api python manage.py makemigrations
docker compose exec api python manage.py migrate
docker compose exec api python manage.py shell
docker compose exec api pytest
docker compose exec api ruff check .

docker compose exec web npm run lint
docker compose exec web npm run build  # ビルドが通るかの確認

docker compose exec db psql -U postgres -d django_prac
```

## トラブルシュート

| 症状 | 原因 | 対処 |
|---|---|---|
| `web` が `vite: not found` で落ちる | 匿名ボリュームで `node_modules` が空になっている | `docker compose down -v` してから `docker compose up --build` |
| API が `could not translate host name "db"` | `api` が `db` より先に起動した | `depends_on` の `service_healthy` が入っているか確認 |
| ブラウザから `localhost:5173` が開けない | Vite が `0.0.0.0` に bind していない | `command` の `--host 0.0.0.0` を確認 |
| `/api/...` が 404 | Vite の proxy が効いていない | `vite.config.ts` の `proxy.target` と `docker compose logs api` を確認 |
| マイグレーションを当てても反映されない | ホストとコンテナで別の DB を見ている | `DATABASE_URL` のホスト名が `db` になっているか確認（`localhost` だとコンテナ自身を指す） |
| ホットリロードが効かない | ボリュームマウントの漏れ | `volumes: - ./backend:/app` があるか確認 |
| 地図が真っ白 | タイル URL の誤り、またはネットワーク遮断 | DevTools の Network で `cyberjapandata.gsi.go.jp` へのリクエストを確認 |

## `.env.example`（リポジトリに commit するもの）

```bash
# --- 共通 ---
GOOGLE_OAUTH_CLIENT_ID=

# --- backend（compose が渡す。ローカル値は docker-compose.yml に直書きでよい）---
# DJANGO_SECRET_KEY=
# DATABASE_URL=

# --- frontend ---
# VITE_API_BASE_URL=            # ローカルは空（プロキシ）、デプロイ時のみ設定
```

> **`GOOGLE_OAUTH_CLIENT_ID` はクライアント ID なので公開されても問題ない**（ブラウザに埋まる値）。一方 **client secret は今回の構成では一切使わない** — 理由は `06-auth.md` を参照。
