# 08. Render.com へのデプロイ

## 前提と注意

> **無料枠の条件は 2026-08-03 に確認済み**（`00-decisions.md`）。料金体系は変わりやすいので、実際に作成する直前に [Render の無料枠ドキュメント](https://render.com/docs/free) をもう一度見ること。

## 構成

Render 上に **3 つのリソース**を作る。

| リソース | 種別 | 中身 | 無料枠での挙動 |
|---|---|---|---|
| `django-prac-web` | **Static Site** | React のビルド成果物（`dist/`） | スリープしない。常に速い |
| `django-prac-api` | **Web Service（Docker）** | Django + Gunicorn | **15 分アクセスが無いとスリープ**。復帰に数十秒 |
| `django-prac-db` | **PostgreSQL** | | **作成から 30 日で失効 → 14 日の猶予 → データごと削除。** 1 GB / アカウントあたり 1 個 / バックアップ非対応 |

```mermaid
flowchart LR
  U["ブラウザ"]
  S["Static Site<br/>django-prac-web"]
  A["Web Service<br/>django-prac-api"]
  D[("PostgreSQL<br/>django-prac-db")]

  U --> S
  U -->|"VITE_API_BASE_URL"| A
  A -->|"DATABASE_URL（内部接続）"| D
```

### 無料枠で必ず踏む 2 つの落とし穴

**1. API のコールドスタート**

無料の Web Service は無操作 15 分でスリープし、次のリクエストで起動し直す。**最初の API 呼び出しが 30〜60 秒待たされる。**

対策:
- フロント側で、初回リクエストのタイムアウトを長め（60 秒）に取る
- 起動中と分かるローディング表示を出す（「サーバーを起動しています…」）
- 人に見せる直前に一度アクセスして温めておく

**根本的には有料プランに上げるしか解決しない。** 練習用途なので受け入れる。

**2. 無料 PostgreSQL の 30 日制限**

| 条件 | 内容 |
|---|---|
| 有効期限 | **作成から 30 日** |
| 猶予期間 | 失効後 **14 日**。この間に有料へ上げなければ**データごと削除** |
| 容量 | 1 GB |
| 個数 | **アカウントあたり同時に 1 つまで** |
| バックアップ | **非対応** |

対策:
- **データを失っても復旧できる状態を保つ。** それが `04-data-model.md` で fixture を commit している理由。DB を作り直したら `migrate` + `loaddata` で元に戻る
- ユーザーアカウントは消える。練習用なので許容する
- **作成日から 30 日後をカレンダーに入れておく。** Render からメール通知も来る
- 期限が来たときの手順は `10-roadmap.md` の運用メモに書いてある

> **「無料 DB は 1 アカウント 1 個」なので、dev / prod の DB 分離はできない。** 本番 1 本で進める。ローカルの compose の Postgres が実質的な dev 環境になる。

## `render.yaml`（Blueprint / IaC）

管理画面でポチポチ作らず、リポジトリの `render.yaml` から作る。**構成が誰にでも読める形で残り、作り直しも一発**になる。

```yaml
databases:
  - name: django-prac-db
    databaseName: django_prac
    user: django_prac
    plan: free

services:
  # --- Django API ---
  - type: web
    name: django-prac-api
    runtime: docker
    plan: free
    region: singapore                 # 日本から近いリージョンを選ぶ
    rootDir: backend
    dockerfilePath: ./Dockerfile
    autoDeploy: false                 # ← CI 経由でだけデプロイする（09-ci-cd.md）
    healthCheckPath: /api/health/
    dockerCommand: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2"
    envVars:
      - key: DJANGO_SETTINGS_MODULE
        value: config.settings.production
      - key: DJANGO_SECRET_KEY
        generateValue: true           # Render が生成して保持する
      - key: DATABASE_URL
        fromDatabase:
          name: django-prac-db
          property: connectionString
      - key: DJANGO_ALLOWED_HOSTS
        sync: false                   # 初回デプロイ後に手で入れる
      - key: FRONTEND_ORIGIN
        sync: false                   # 同上
      - key: GOOGLE_OAUTH_CLIENT_ID
        sync: false

  # --- React フロント ---
  - type: web
    name: django-prac-web
    runtime: static
    plan: free
    rootDir: frontend
    buildCommand: npm ci && npm run build
    staticPublishPath: ./dist
    autoDeploy: false
    envVars:
      - key: VITE_API_BASE_URL
        sync: false                   # 初回デプロイ後に API の URL を入れる
      - key: VITE_GOOGLE_OAUTH_CLIENT_ID
        sync: false
    routes:
      - type: rewrite                 # ← SPA のクライアントルーティングに必須
        source: /*
        destination: /index.html
    headers:
      - path: /*
        name: X-Frame-Options
        value: DENY
```

### 各設定の意図

| 設定 | なぜ |
|---|---|
| `dockerCommand` で `migrate` を実行 | Render の `preDeployCommand` は有料プラン向けの機能。無料枠では**起動コマンドの先頭でマイグレーションを流す**のが素直。複数インスタンスに増やすときは分離が必要になるが、`workers 2` の単一インスタンスなら問題ない |
| `autoDeploy: false` | Render 標準の「push したら即デプロイ」を切る。**テストが落ちてもデプロイされてしまう**のを防ぐため。代わりに GitHub Actions が成功したときだけ Deploy Hook を叩く |
| `healthCheckPath` | Render がここを叩いて起動完了を判定する。**DB に触らない軽いエンドポイントにする**こと |
| `routes: rewrite` | これが無いと `/login` を直接開いたときに 404 になる（SPA の典型的な事故） |
| `sync: false` | 「Blueprint では管理せず、ダッシュボードで手入力する」の意味。URL のように**初回デプロイまで確定しない値**に使う |
| `generateValue: true` | `SECRET_KEY` を Render 側で生成させる。リポジトリにも手元にも平文が残らない |
| `region: singapore` | 日本からのレイテンシを抑える。**DB と API は必ず同じリージョンにする**（別リージョンだと内部接続にならない） |

## 環境変数の一覧

### API（`django-prac-api`）

| 変数 | 値 | 出所 |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `render.yaml` |
| `DJANGO_SECRET_KEY` | ランダム | Render 生成 |
| `DATABASE_URL` | `postgres://...` | Render の DB から自動 |
| `DJANGO_ALLOWED_HOSTS` | `django-prac-api.onrender.com` | **初回デプロイ後に手入力** |
| `FRONTEND_ORIGIN` | `https://django-prac-web.onrender.com` | **初回デプロイ後に手入力** |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud の値 | 手入力 |
| `PORT` | Render が自動で注入 | — |

### フロント（`django-prac-web`）

| 変数 | 値 |
|---|---|
| `VITE_API_BASE_URL` | `https://django-prac-api.onrender.com` |
| `VITE_GOOGLE_OAUTH_CLIENT_ID` | Google Cloud の値 |

> **フロントの環境変数はビルド時に埋め込まれる。** 変更したら**必ず再デプロイ（再ビルド）する**こと。環境変数を書き換えただけでは反映されない — Static Site 特有の引っかかりポイント。

## `production.py` で必要な設定

```python
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ["DJANGO_ALLOWED_HOSTS"].split(",")

# --- CORS / CSRF（フロントが別ホストなので必須）---
FRONTEND_ORIGIN = os.environ["FRONTEND_ORIGIN"]
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]

# --- Render のプロキシ配下で HTTPS を正しく認識させる ---
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600

# --- Cookie（06-auth.md）---
REFRESH_COOKIE_SECURE = True
REFRESH_COOKIE_SAMESITE = "None"

# --- 静的ファイル（Django Admin 用）---
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# --- ログ（Render のログビューアに出す）---
LOGGING = { ... }   # console ハンドラに INFO 以上
```

**`SECURE_PROXY_SSL_HEADER` を入れ忘れると `SECURE_SSL_REDIRECT` が無限リダイレクトになる。** Render は TLS を終端してから HTTP でコンテナに渡すので、Django からは「HTTP で来ている」ように見え、HTTPS へリダイレクト → また HTTP で届く、を繰り返す。**この 2 行はセットで書く。**

## 初回デプロイの手順

順番が重要。**URL が確定してからでないと入れられない値がある**ので、2 周する形になる。

```
1.  GitHub にリポジトリを push する
2.  Render で New → Blueprint → リポジトリを選択 → render.yaml が読まれる
3.  DB / API / Static Site の 3 つが作られる（この時点では API は起動失敗してよい）
4.  ★ 発行された URL を 2 つ控える
      API   : https://django-prac-api.onrender.com
      フロント: https://django-prac-web.onrender.com
5.  API の環境変数に入力
      DJANGO_ALLOWED_HOSTS   = django-prac-api.onrender.com
      FRONTEND_ORIGIN        = https://django-prac-web.onrender.com
      GOOGLE_OAUTH_CLIENT_ID = （Google Cloud の値）
6.  フロントの環境変数に入力
      VITE_API_BASE_URL             = https://django-prac-api.onrender.com
      VITE_GOOGLE_OAUTH_CLIENT_ID   = （同上）
7.  ★ Google Cloud Console に戻り、「承認済みの JavaScript 生成元」に
      https://django-prac-web.onrender.com を追加する（06-auth.md の宿題）
8.  両方を Manual Deploy で再デプロイ
9.  API の Shell から初期データを投入
      python manage.py loaddata libraries
      python manage.py createsuperuser
10. 動作確認（下のチェックリスト）
11. GitHub Actions 用に Deploy Hook の URL を 2 本取得（09-ci-cd.md）
```

> **手順 4 → 5・6・7 が「URL が決まらないと入れられない値」。** ここを飛ばして「なぜか本番だけ動かない」になるのが定番なので、初回は必ずこの順で進める。

## デプロイ後チェックリスト

`02-architecture.md` の差分表と対応している。上から順に潰す。

- [ ] `https://<api>.onrender.com/api/health/` が `200` を返す
- [ ] `https://<api>.onrender.com/admin/` が**CSS ありで**表示される → WhiteNoise が効いている
- [ ] フロントを開いて地図が表示される → GSI タイルが読めている
- [ ] 図書館のピンが表示される → **CORS が通っている**（DevTools の Console にエラーが無い）
- [ ] `/login` を**ブラウザで直接開いて** 404 にならない → `routes: rewrite` が効いている
- [ ] メール + パスワードで登録・ログインできる
- [ ] **ページをリロードしてもログイン状態が維持される** → `SameSite=None; Secure` の Cookie が効いている
- [ ] Google ログインができる → JavaScript 生成元の登録が済んでいる
- [ ] 「現在地」ボタンが動く → HTTPS なので Geolocation が使える
- [ ] 無限リダイレクトしていない → `SECURE_PROXY_SSL_HEADER`
- [ ] Render のログにエラーが出ていない

## よくあるエラーと原因

| 症状 | 原因 |
|---|---|
| `DisallowedHost at /` | `DJANGO_ALLOWED_HOSTS` 未設定 or ホスト名が違う |
| ブラウザ Console に `blocked by CORS policy` | `FRONTEND_ORIGIN` の値が違う（末尾スラッシュが余計、`http`/`https` の取り違え） |
| リダイレクトが多すぎる | `SECURE_PROXY_SSL_HEADER` の設定漏れ |
| Admin が CSS 無しの素の HTML | `collectstatic` が走っていない / WhiteNoise ミドルウェア未登録 |
| リロードでログアウトされる | Cookie が `SameSite=Lax` のまま（本番は `None; Secure`） |
| `/login` を直接開くと 404 | Static Site の `routes: rewrite` が無い |
| Google ログインで `origin_mismatch` | Google Cloud に本番の生成元を登録していない |
| 起動時に `relation does not exist` | `migrate` が走っていない（`dockerCommand` を確認） |
| デプロイは成功するのに反映されない | フロントの環境変数を変えただけで再ビルドしていない |
| 突然 DB に繋がらなくなった | **無料 Postgres の有効期限切れ** |

## 独自ドメインについて

元プロジェクトの検討メモ（`smocking-notes/jovid.md`）に「ドメインを買うか」の論点があった。**この練習用リポジトリでは買わない。**

- `*.onrender.com` のままで機能上の問題は一切ない
- 独自ドメインを当てると、Google OAuth の生成元・`ALLOWED_HOSTS`・`FRONTEND_ORIGIN`・CORS を**全部書き換える**ことになる
- ドメインを当てる練習をしたくなったら、上の 4 箇所を直せばよいと分かっている状態がゴール。実際に買う必要はない
