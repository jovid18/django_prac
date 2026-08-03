# django_prac — 東京都の図書館マップ

**React + Django + PostgreSQL + Docker + Render** を一通り手に馴染ませるための練習用リポジトリ。

地図上に東京都の図書館を表示し、会員登録・ログイン（メール+パスワード / Google）ができるウェブアプリを作る。
本来のテーマ（屋内で喫煙できる店のマッチング / [smocking-notes](https://github.com/jovid18/smocking-notes)）のデータドメインを図書館に差し替えたもの。

> **現在の状態: Day 0 完了（設計と技術選定）。実装は未着手。**

## 技術構成

バージョンは Day 0（2026-08-03）に確定済み。根拠は [`docs/00-decisions.md`](docs/00-decisions.md)。

| 領域 | 選定 |
|---|---|
| フロント | React 19.2 + Vite 8 + TypeScript（Node 22 LTS） |
| バックエンド | Django 6.0 + DRF 3.17（Python 3.13） |
| Python 依存管理 | uv（`uv.lock`） |
| DB | PostgreSQL 16 |
| 地図 | MapLibre GL JS + 国土地理院タイル |
| 認証 | JWT + Google ID トークン検証 |
| ローカル | docker compose（db / api / web） |
| デプロイ | Render.com（Static Site + Web Service + Postgres） |
| CI/CD | GitHub Actions → Render Deploy Hook |

## ドキュメント

| # | ファイル | 内容 |
|---|---|---|
| 00 | [Day 0 の決定事項](docs/00-decisions.md) | **確定バージョンと根拠、未解決リスク** |
| 01 | [概要とスコープ](docs/01-overview.md) | 何を作るか、Must / Won't |
| 02 | [アーキテクチャ](docs/02-architecture.md) | 全体構成、**ローカルと本番の差分表**、ディレクトリ構造 |
| 03 | [ローカル開発環境](docs/03-local-dev.md) | docker compose、初回セットアップ、トラブルシュート |
| 04 | [データモデル](docs/04-data-model.md) | ER 図、モデル定義、シードデータの作り方 |
| 05 | [API 仕様](docs/05-api.md) | エンドポイント一覧、リクエスト / レスポンス |
| 06 | [認証設計](docs/06-auth.md) | トークンの持ち方、Google ID トークンの検証 |
| 07 | [フロントエンド](docs/07-frontend.md) | 画面構成、地図、現在地、状態管理 |
| 08 | [Render へのデプロイ](docs/08-deploy-render.md) | render.yaml、初回手順、チェックリスト |
| 09 | [CI/CD](docs/09-ci-cd.md) | GitHub Actions、ブランチ運用、ロールバック |
| 10 | [着手手順](docs/10-roadmap.md) | Day 0〜5 のチェックリスト |

**まず読むもの**: `01` → `02` → `10`。実装は `10-roadmap.md` の Day 0 から始める。

## クイックスタート（実装後）

```bash
cp .env.example .env
docker compose up --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py loaddata libraries
docker compose exec api python manage.py createsuperuser
# → http://localhost:5173
```

## 注記

アプリ内で図書館に付与される「喫煙区分」は、**元テーマのスキーマとフィルタ UI を練習するために自動生成したダミーデータ**であり、実在する施設の喫煙可否とは一切関係がない。画面上にもその旨を表示する。
