# 01. プロジェクト概要とスコープ

## 何を作るか

東京都の**図書館の位置を地図で探すウェブサービス**。会員登録・ログインがあり、地図上に図書館のピンが表示され、各図書館に喫煙区分（4種）が付く。

> **図書館は「代役」です**
> このリポジトリの目的は **React + Django + PostgreSQL + Docker + Render へのデプロイまでを
> 一通り手に馴染ませる**ことで、図書館はそのための題材。元プロジェクトのデータドメインを
> 差し替えている。
> 喫煙区分のフィールドは、**enum で表す複数状態のスキーマとフィルタ UI** を練習するために残し、
> **値はシード時に固定シードの擬似乱数で割り当てる**（実際の図書館の喫煙可否とは無関係 — 画面上にその旨を明記する）。

## 目標（この練習で身につけたいこと）

| # | 目標 | どこで検証されるか |
|---|---|---|
| 1 | React（最新）+ Vite のプロジェクトをゼロから構成する | `frontend/` |
| 2 | Django + DRF で REST API を設計・実装する | `backend/` |
| 3 | PostgreSQL との接続とマイグレーション運用 | `docker compose` / Render Postgres |
| 4 | `docker compose up` 一発で立ち上がるローカル環境 | `docker-compose.yml` |
| 5 | 自前の会員登録（ID/PW）と Google OAuth を**両方**ひとつの User モデルに載せる | `apps/accounts` |
| 6 | ブラウザの Geolocation + 地図描画 + マーカー・フィルタ | Google Maps JS API |
| 7 | main へのマージで自動デプロイされる CI/CD | GitHub Actions + Render |

## 確定した技術選定

| 領域 | 選定 | 理由 |
|---|---|---|
| フロント | **React 19.2 + Vite 8 + TypeScript** | CRA（`create-react-app`）は使用しない。Vite で生成する |
| バックエンド | **Django 6.0 + DRF 3.17**（Python 3.13） | 練習の対象。LTS ではなく最新を採る理由は `00-decisions.md` |
| DB | **PostgreSQL 16** | ローカルはコンテナ、デプロイは Render Postgres |
| Python 依存管理 | **uv**（`uv.lock` を commit） | ロックファイルで CI と本番のバージョンを揃える |
| 地図 | **Google Maps JavaScript API**（`@vis.gl/react-google-maps`） | 当初は MapLibre + 地理院タイル（キー不要）だったが、**実際に描画して比べた結果、見た目を優先して変更**。キーと課金アカウントが必要になる点は受け入れた（`00-decisions.md`） |
| 認証 | **メール + パスワード（JWT）と Google OAuth（ID トークン検証）** | LINE は[スコープ外](#スコープ外wont)として記録のみ |
| ローカル | **docker compose**（db / api / web の 3 サービス） | |
| デプロイ | **Render.com** — Static Site（フロント）+ Web Service（API）+ Postgres | |
| CI/CD | **GitHub Actions** — テスト通過後に Render の Deploy Hook を叩く | |

> **バージョンは Day 0（2026-08-03）に調査して確定済み。** 根拠とリスクは **[`00-decisions.md`](00-decisions.md)** にまとめてある。
> `djangorestframework-simplejwt` の Django 6.0 対応は PyPI のメタデータ上は未記載だが、**upstream で対応済み**であることを確認済み（`00-decisions.md`）。

## 機能スコープ

### Must — ここまでできれば練習の目的は達成

- [ ] メール + パスワードでの会員登録 / ログイン / ログアウト
- [ ] Google アカウントでのログイン（初回は自動で登録）
- [ ] ログイン状態の維持（アクセストークンの更新）/ 自分の情報の取得
- [ ] 地図の表示（東京中心、ズーム・パン）
- [ ] **現在地の表示**（Geolocation API、拒否されても画面が壊れないこと）
- [ ] 東京都の図書館ピンの表示（地図を動かすたびに表示範囲内のデータだけ取得）
- [ ] ピンをクリック → 図書館の詳細（名称 / 住所 / 喫煙区分）
- [ ] **喫煙区分フィルタ**（不可 / 加熱式のみ / 紙巻きのみ / 両方可）— 元ドメインの中心的な UI の練習

### Should — 時間が余ったら

- [ ] お気に入り（ログインユーザーのみ）— 認証が必要な書き込み API の練習に向く
- [ ] 名称・住所のテキスト検索
- [ ] 現在地からの近い順リスト
- [ ] ピンのクラスタリング

### スコープ外（Won't）— 明示的にやらないこと

| 項目 | 理由 |
|---|---|
| LINE ログイン | Google で OAuth の流れは練習済みになる。必要になったら `06-auth.md` の `SocialAccount.provider` に `line` を足すだけで済むように設計しておく |
| パスワード再設定メール | SMTP の設定は練習の本質と関係がない |
| 管理者向けの図書館登録・編集画面 | Django Admin で代替する |
| ユーザー投稿・レビュー | 元プロジェクトの機能。ここでは不要 |
| PostGIS / GeoDjango | Docker イメージに GDAL・GEOS を入れる必要があり、難易度が上がる。図書館数百件の規模なら **緯度経度カラム + bbox 検索**で十分。アップグレード経路は `04-data-model.md` に記録しておく<br>⚠ **代わりに「距離計算を自分で正しく書く責任」を負う。** Day 5 に実際に踏んだ（`acos` の定義域と精度。`04-data-model.md`）。この判断は変えないが、コストとして数えておく |
| ネイティブアプリ | ウェブのみ |
| SSR / Next.js | 今回は **React SPA + 別立ての Django API** という構成を練習するのが目的 |

## ドキュメントを読む順番

1. `02-architecture.md` — 全体構成とディレクトリ構造
2. `03-local-dev.md` — ローカル環境を立ち上げる
3. `04-data-model.md` — モデルとシードデータ
4. `05-api.md` — API 仕様
5. `06-auth.md` — 認証フロー
6. `07-frontend.md` — フロントの構造と地図
7. `08-deploy-render.md` — Render へのデプロイ
8. `09-ci-cd.md` — GitHub Actions
9. `10-roadmap.md` — 実際の着手順チェックリスト
