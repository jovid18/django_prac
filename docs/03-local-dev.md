# 03. ローカル開発環境（docker compose）

## ゴール

リポジトリを clone して `docker compose up` を打つだけで、ブラウザで `http://localhost:5173` が開き、地図と API が動いている状態。**ホストに Python も Node も入っていなくてよい**ことを目標にする。

## 前提

- Docker Desktop（もしくは OrbStack など）がインストール済み
- ホスト側のポート `5173` / `8001` / `5433` が空いている

> **ホスト側のポートは既定値からずらしてある。** `8000` と `5432` は別プロジェクトのコンテナや
> ローカルの PostgreSQL が使っていることが多いため。**コンテナ内のポートは 8000 / 5432 のまま**なので、
> `web` から `api:8000` へ、`api` から `db:5432` へという内部の経路は変わらない。
>
> | | コンテナ内 | ホストから |
> |---|---|---|
> | api | 8000 | **8001** |
> | db | 5432 | **5433** |
> | web | 5173 | 5173 |

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
      VITE_GOOGLE_MAPS_API_KEY: ${GOOGLE_MAPS_API_KEY}      # 無いと地図が出ない
      VITE_GOOGLE_MAPS_MAP_ID: ${GOOGLE_MAPS_MAP_ID}        # 空なら DEMO_MAP_ID
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

依存管理は **uv** に確定している（`00-decisions.md`）。

**マルチステージにしてある。** 開発ツール（ruff / pytest）を本番イメージに含めないため。

```dockerfile
# --- 共通の土台 ---
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

# ★ 依存だけ先に入れてレイヤを分ける
COPY pyproject.toml uv.lock ./

# --- 開発用（compose が target: dev で使う）---
FROM base AS dev
RUN uv sync --frozen
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- 本番用（最終ステージ = target 未指定でこれになる）---
FROM base AS prod
RUN uv sync --frozen --no-dev
COPY . .
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

| 記述 | 意図 |
|---|---|
| `COPY pyproject.toml uv.lock` を先に | **依存のインストールを独立したレイヤにする。** ソースを 1 行直すたびに全依存を入れ直すのを防ぐ |
| `--frozen` | `uv.lock` の通りに入れる。ロックを勝手に更新させない（`npm ci` に相当） |
| `dev` / `prod` の分割 | 本番イメージに `pytest` / `ruff` を入れない。**分けないと `docker compose exec api ruff` が動かない** |
| `prod` を最終ステージに | Render は `--target` を付けずにビルドするので、最後のステージが選ばれる |
| `PATH` に `.venv/bin` | `uv run` を毎回書かずに `gunicorn` / `ruff` を直接叩ける |

> **`uv.lock` は必ず commit する。** これが無いと `--frozen` が失敗し、ビルドが通らない。

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
| http://localhost:5173/api/health/ | **Vite proxy 経由の API**（本来の経路） |
| http://localhost:8001/api/health/ | API を直に叩く |
| http://localhost:8001/admin/ | Django Admin |

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

# 依存を追加する（uv.lock が更新されるので commit する）
docker compose exec api uv add <package>
docker compose exec api uv add --dev <package>   # pytest / ruff など

docker compose exec web npm run lint
docker compose exec web npm run build  # ビルドが通るかの確認

docker compose exec db psql -U postgres -d django_prac
```

## トラブルシュート

| 症状 | 原因 | 対処 |
|---|---|---|
| **イメージを作り直したのに中身が古いまま**（例: `ruff: not found` が消えない） | **匿名ボリュームは `docker compose up --build` では更新されない。** 最初に作られたときの内容を保持し続ける（`/app/.venv` や `/app/node_modules` がこれ） | `docker compose up -d --renew-anon-volumes <service>`。**DB の名前付きボリュームは消えない**ので安全 |
| `web` が `vite: not found` で落ちる | 同上（`node_modules` の匿名ボリューム） | 上と同じ。それでも駄目なら `docker compose down -v` |
| API が `could not translate host name "db"` | `api` が `db` より先に起動した | `depends_on` の `service_healthy` が入っているか確認 |
| ブラウザから `localhost:5173` が開けない | Vite が `0.0.0.0` に bind していない | `command` の `--host 0.0.0.0` を確認 |
| `/api/...` が 404 | Vite の proxy が効いていない | `vite.config.ts` の `proxy.target` と `docker compose logs api` を確認 |
| マイグレーションを当てても反映されない | ホストとコンテナで別の DB を見ている | `DATABASE_URL` のホスト名が `db` になっているか確認（`localhost` だとコンテナ自身を指す） |
| ホットリロードが効かない | ボリュームマウントの漏れ | `volumes: - ./backend:/app` があるか確認 |
| 地図が真っ白 | Maps のキーが無い / 制限に弾かれた / 課金未設定 | DevTools の Console を見る。`InvalidKeyMapError`（キー未設定）/ `RefererNotAllowedMapError`（リファラー制限に `http://localhost:5173/*` が無い）/ `BillingNotEnabledMapError`（課金未設定） |
| 地図が潰れて線になる | 親要素の高さが 0 | `<Map>` の親に高さを与える（`height: 100dvh` など） |
| **ファイルを削除した瞬間に `web` が落ちる** | Vite 8 の dev server が HMR 中の削除で `ENOENT` を unhandled error にして exit する | `docker compose up -d web` で起こし直す。作業ファイルを消すときは dev server を止めてからのほうが安全 |

## `.env.example`（リポジトリに commit するもの）

```bash
# --- 共通 ---
GOOGLE_OAUTH_CLIENT_ID=

# --- 地図（Day 3 以降。無いと地図が表示されない）---
GOOGLE_MAPS_API_KEY=
GOOGLE_MAPS_MAP_ID=             # 空なら DEMO_MAP_ID にフォールバック

# --- backend（compose が渡す。ローカル値は docker-compose.yml に直書きでよい）---
# DJANGO_SECRET_KEY=
# DATABASE_URL=

# --- frontend ---
# VITE_API_BASE_URL=            # ローカルは空（プロキシ）、デプロイ時のみ設定
```

> **`GOOGLE_OAUTH_CLIENT_ID` はクライアント ID なので公開されても問題ない**（ブラウザに埋まる値）。一方 **client secret は今回の構成では一切使わない** — 理由は `06-auth.md` を参照。

> ⚠ **`GOOGLE_MAPS_API_KEY` は同じ「公開される値」だが、こちらは課金に直結する。**
> Cloud Console で「HTTP リファラー制限 + Maps JavaScript API のみ」を掛けてから使う（`00-decisions.md`）。
