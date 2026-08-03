# 09. CI/CD（GitHub Actions → Render）

## 方針

**「main にマージされたら自動でデプロイ」を、テストを通過した場合に限って行う。**

Render には「push を検知して自動デプロイ」する標準機能がある。しかしそれをそのまま使うと、**テストが落ちているコードもデプロイされる**。そこで:

1. `render.yaml` で `autoDeploy: false` にして Render 側の自動デプロイを切る
2. GitHub Actions でテストとビルドを回す
3. **すべて成功し、かつ `main` への push のときだけ** Render の Deploy Hook を叩く

```mermaid
flowchart LR
  PR["Pull Request"] --> CI1["backend test<br/>frontend build"]
  CI1 -->|"失敗ならマージ不可"| PR

  M["main へ merge"] --> CI2["backend test<br/>frontend build"]
  CI2 -->|"成功"| H["Deploy Hook を叩く"]
  H --> RA["Render: API"]
  H --> RW["Render: Static Site"]
```

## ジョブ構成

| ジョブ | いつ | 内容 |
|---|---|---|
| `backend` | PR / main への push | ruff → pytest（Postgres サービスコンテナ付き） |
| `frontend` | PR / main への push | eslint → tsc → vite build |
| `deploy` | **main への push のみ**、上 2 つが成功したとき | Deploy Hook を 2 本叩く |

`backend` と `frontend` は**並列に走らせる**。互いに依存がない。

## `.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true        # 連続 push で古いジョブを打ち切る

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 3s
          --health-retries 10

    env:
      DJANGO_SETTINGS_MODULE: config.settings.local
      DJANGO_SECRET_KEY: ci-only-secret
      DATABASE_URL: postgres://postgres:postgres@localhost:5432/test_db
      GOOGLE_OAUTH_CLIENT_ID: dummy-client-id.apps.googleusercontent.com

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip

      - run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check . && ruff format --check .

      - name: Migrations are up to date
        run: python manage.py makemigrations --check --dry-run

      - name: Test
        run: pytest -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npx tsc --noEmit

      - name: Build
        run: npm run build
        env:
          VITE_API_BASE_URL: https://example.invalid    # ビルドが通るかの確認だけ
          VITE_GOOGLE_OAUTH_CLIENT_ID: dummy

  deploy:
    needs: [backend, frontend]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest

    steps:
      - name: Deploy API
        run: curl -fsS -X POST "$HOOK"
        env:
          HOOK: ${{ secrets.RENDER_DEPLOY_HOOK_API }}

      - name: Deploy Frontend
        run: curl -fsS -X POST "$HOOK"
        env:
          HOOK: ${{ secrets.RENDER_DEPLOY_HOOK_WEB }}
```

### 各ステップの意図

| ステップ | なぜ入れるか |
|---|---|
| `concurrency: cancel-in-progress` | 連続で push したときに古いジョブを打ち切る。無料枠の実行時間を無駄にしない |
| `makemigrations --check --dry-run` | **モデルを変えたのにマイグレーションを作り忘れた**PR を落とす。これが無いと、デプロイ時に初めて気付いて本番が壊れる。**地味だが一番効く 1 行** |
| `ruff format --check` | フォーマット差分で PR が汚れるのを防ぐ |
| `npx tsc --noEmit` | Vite の dev サーバは型エラーがあっても動く。CI で型を見る |
| `npm run build` | ビルドが通ることの確認。`VITE_*` はダミーでよい（値の正しさは検証しない） |
| `services: postgres` | SQLite で代用しない。**本番と同じ Postgres で回さないと、`citext` や制約の挙動差で「CI は緑なのに本番で落ちる」が起きる** |
| `curl -fsS` | `-f` を付けないと、Hook が 4xx を返しても curl が成功扱いになり、**デプロイ失敗が緑になる** |

### Deploy Hook を秘密にする理由

Deploy Hook の URL は**それ自体が認証情報**。知っていれば誰でもデプロイを起動できる。ワークフローに直書きせず、必ず Secrets に入れて `env:` 経由で渡す（`run:` に直接 `${{ secrets.X }}` を書くとログにマスクされずに残る可能性がある構成もあるため、`env:` 経由が安全）。

## Deploy Hook の取得と登録

```
Render ダッシュボード
  → 対象サービス → Settings → Deploy Hook → URL をコピー
     （https://api.render.com/deploy/srv-xxxx?key=yyyy の形）

GitHub
  → リポジトリ → Settings → Secrets and variables → Actions → New repository secret
     RENDER_DEPLOY_HOOK_API : API 側の URL
     RENDER_DEPLOY_HOOK_WEB : Static Site 側の URL
```

## ブランチ運用

**トランクベース（`main` 一本）。** 一人開発なので `develop` は作らない。

| ルール | 内容 |
|---|---|
| 作業単位 | `main` から `feat/xxx` を切って PR を出す |
| マージ | **Squash merge** に統一。履歴が 1 機能 1 コミットで並ぶ |
| `main` への直 push | ブランチ保護で禁止する（下記） |
| コミットメッセージ | Conventional Commits（`feat:` / `fix:` / `docs:` / `chore:`） |

### ブランチ保護（Settings → Branches → Add rule）

- [x] Require a pull request before merging
- [x] Require status checks to pass before merging → `backend` と `frontend` を必須にする
- [x] Require branches to be up to date before merging
- [ ] Require approvals — **一人開発なのでオフ**（オンにすると自分の PR をマージできなくなる）

> **`main` を保護しておくと、うっかり直 push でテストを飛ばして壊れたものをデプロイする事故が構造的に起きなくなる。** 一人開発でも設定する価値がある。

## デプロイが失敗したときの戻し方

| 状況 | 対応 |
|---|---|
| デプロイ後に不具合が判明 | **Render の Rollback**（Deploys タブから直前のデプロイを選んで再有効化）が最速。数十秒で戻る |
| コードを直したい | `main` に revert コミットを積む → CI 経由で再デプロイ |
| マイグレーションが原因 | **これが一番厄介。** ロールバックしてもスキーマは戻らない。破壊的な変更（カラム削除・型変更）を含む PR は、当てる前に必ず一度立ち止まる |

**マイグレーションの原則**: 削除は 2 段階に分ける。
1. まずコード側でそのカラムを使うのをやめてデプロイする
2. 次のデプロイでカラムを削除する

こうしておくと、1 の段階でロールバックしてもアプリは動く。

## この構成の限界（把握しておくこと）

| 限界 | 内容 |
|---|---|
| ステージング環境が無い | 本番一本。PR ごとのプレビュー環境は Render の有料機能。**練習用なので許容** |
| E2E テストが無い | Playwright で「地図が開いてピンが出る」1 本だけでも入れると価値は高い。Should |
| マイグレーションが起動コマンド内 | インスタンスを 2 台以上に増やすと同時実行の危険がある。無料枠の 1 台前提の割り切り |
| DB のバックアップが無い | 無料 Postgres にバックアップは期待しない。fixture を commit しているのがバックアップ代わり |
| デプロイの完了を待たない | Hook を叩いたら Actions は成功で終わる。**デプロイ自体の成否は Render のダッシュボードで確認する。** 待ちたければ Render API をポーリングするステップを足す |
