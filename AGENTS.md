# AGENTS.md

このリポジトリで作業する AI エージェント向けの共有ルール。
Claude Code / Codex のどちらから開いても、まずこれを読む。

## このプロジェクトは何か

東京都の図書館を地図で探すウェブアプリ。**React + Django + PostgreSQL + Docker + Render**
を一通り手に馴染ませるための練習用リポジトリ。

図書館は題材（代役）で、**元プロジェクト**のデータドメインを差し替えたもの。
喫煙区分のフィールドは、**enum で表す複数状態のスキーマとフィルタ UI** を
練習するために残してある。

> **図書館に付いている「喫煙区分」は練習用のダミーデータ**であり、
> 実在する施設の喫煙可否とは一切関係がない。UI にもその旨を表示する。

## 使えるスキル

| スキル | いつ使うか |
|---|---|
| `/commit` | ステージ → コミット → push。検証を先に通す |
| `/pr` | 現在のブランチから `main` へ日本語の PR を作成する |

実体は `.claude/skills/` にあり、`.codex/skills` はそこへのシンボリックリンク。
**編集するときは `.claude/skills/` 側を直す。**

> シンボリックリンクが使えない環境（Windows など）で `.codex/skills` が壊れている場合は、
> `.claude/skills/` の中身をコピーして置き換えてよい。

## 言語

| 対象 | 言語 |
|---|---|
| ドキュメント（`docs/`） | **日本語** |
| コード中のコメント | **日本語** |
| コミットメッセージ | 接頭辞のみ英語、本文は**日本語** |
| PR のタイトル・本文 | **日本語** |
| 変数名・関数名 | 英語 |

## 開発の進め方

### 環境

```bash
cp .env.example .env          # GOOGLE_OAUTH_CLIENT_ID と GOOGLE_MAPS_API_KEY を入れる
docker compose up --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py loaddata libraries
```

| | ホストから | コンテナ内 |
|---|---|---|
| フロント | http://localhost:5173 | 5173 |
| API | http://localhost:8001 | 8000 |
| DB | 5433 | 5432 |

**ホスト側のポートは既定値からずらしてある**（`8000` と `5432` は他のプロジェクトと
衝突しやすいため）。コンテナ内の名前解決（`api:8000` / `db:5432`）は変わらない。

### ブランチ運用

**トランクベース。`main` はブランチ保護されており直接 push できない。**

```
main から feat/xxx を切る → PR → CI 通過 → Squash merge → 自動デプロイ
```

`backend` と `frontend` の CI が通らないとマージできない。

### コミット前に必ず通すもの

```bash
docker compose exec -T api ruff format .
docker compose exec -T api ruff check .
docker compose exec -T api python manage.py makemigrations --check --dry-run
docker compose exec -T api pytest -q

docker compose exec -T web npm run lint
docker compose exec -T web npm run build
```

`makemigrations --check` は、**モデルを変えたのにマイグレーションを作り忘れた変更**を
止めるためにある。省かない。

## 技術選定（変更するなら理由を `docs/00-decisions.md` に記録する）

| 領域 | 選定 |
|---|---|
| フロント | React 19.2 + Vite 8 + TypeScript 6（lint は **oxlint**、eslint ではない） |
| バックエンド | Django 6.0 + DRF 3.17（Python 3.13） |
| Python 依存管理 | **uv**（`uv.lock` を commit する） |
| DB | PostgreSQL 16 |
| 地図 | **Google Maps JavaScript API**（`@vis.gl/react-google-maps` + `supercluster`）<br>⚠ API キーは公開値だが**課金に直結する**。リファラー制限と Quotas の日次上限を必ず掛ける |
| 認証 | JWT（access はメモリ / refresh は HttpOnly Cookie）+ Google ID トークン検証 |
| デプロイ | Render（Static Site + Web Service + Postgres） |

## 守ること

- **`.env` や API キーをコミットしない。** ステージ後に必ず確認する。
- **`main` に直接コミットしない。**
- **`git push --force` を使う前にユーザーに確認する。**
- **設計判断を変えたら記録する。** コミットメッセージと、必要なら `docs/` に。
  「なぜこうなっているのか」を後から git log で追えるようにする。
- **踏んだ落とし穴はドキュメントに残す。** 実例は `docs/08-deploy-render.md` の
  「ヘルスチェックと HTTPS リダイレクトの衝突」。
- **外部データの出典表示を守る。** 図書館データは OpenStreetMap（ODbL）で、**表示義務がある**。
  自分で画面に出す必要がある（Google の地図側のロゴ・著作権表示は自動で出るので、それを隠さない）。
- **Maps の API キーを晒さない・制限を外さない。** バンドルに埋まる値なので隠しきれない前提で、
  Cloud Console 側の「HTTP リファラー制限 + Maps JavaScript API のみ」+ **Quotas の日次上限**で守る。
- **地図の課金単位は「map load（地図インスタンスの生成回数）」。** ドラッグ・ズーム・タイル取得は課金されない。
  **タイルを CDN でキャッシュしても節約にならず、そもそも規約で禁止**（`docs/07-frontend.md`）。

## ドキュメント

| # | ファイル | 内容 |
|---|---|---|
| 00 | [decisions](docs/00-decisions.md) | **確定バージョンと判断の根拠。まずここ** |
| 01 | [overview](docs/01-overview.md) | スコープ（Must / Won't） |
| 02 | [architecture](docs/02-architecture.md) | 全体構成、**ローカルと本番の差分表** |
| 03 | [local-dev](docs/03-local-dev.md) | docker compose、トラブルシュート |
| 04 | [data-model](docs/04-data-model.md) | ER 図、シードデータの作り方 |
| 05 | [api](docs/05-api.md) | エンドポイント仕様 |
| 06 | [auth](docs/06-auth.md) | 認証設計 |
| 07 | [frontend](docs/07-frontend.md) | 画面構成、地図 |
| 08 | [deploy-render](docs/08-deploy-render.md) | デプロイ手順と実際に踏んだ罠 |
| 09 | [ci-cd](docs/09-ci-cd.md) | GitHub Actions |
| 10 | [roadmap](docs/10-roadmap.md) | Day 0〜5 の進捗 |
