# 10. 着手手順とチェックリスト

## 進め方の原則

1. **Day 1 に一度デプロイまで通す。** 「Hello World が本番 URL で見える」状態を最初に作る。機能を全部作ってから初めてデプロイすると、CORS・Cookie・環境変数の問題が一度に襲ってきて原因の切り分けができなくなる。
2. **カスタム User モデルは最初のマイグレーションより前に作る。** 後から差し替えるのは本当に面倒（`04-data-model.md`）。
3. **一度に 1 つだけ新しいことをする。** 「認証」と「地図」を同時に触らない。片方が壊れたときにもう片方を疑わずに済む。

## Day 0 — 準備（コードを書く前）

- [ ] Django のバージョンを決める（LTS 5.2 か最新か）。`pyproject.toml` に固定する
- [ ] 依存管理を決める（`pip` + `pyproject.toml` か `uv`）。**途中で変えない**
- [ ] Google Cloud Console で OAuth クライアント ID を作る（`06-auth.md`）
      - 承認済み JavaScript 生成元に `http://localhost:5173` を登録
      - **本番 URL はまだ分からないので後で追加する**（Day 1 の宿題としてメモ）
- [ ] GitHub にリポジトリを push する
- [ ] Render のアカウントを作る
- [ ] **無料 Postgres の有効期限を公式ドキュメントで確認し、期限日をカレンダーに入れる**

## Day 1 — 骨組みとデプロイの貫通

**ゴール: 中身は空でいいから、本番 URL でフロントと API が繋がっている状態。**

### backend

- [ ] `backend/` に Django プロジェクトを作る（`config` 名で）
- [ ] `config/settings/{base,local,production}.py` に分割
- [ ] **`apps/accounts` を作り、カスタム `User` を定義する（`migrate` の前に！）**
- [ ] `apps/core` に `GET /api/health/` だけ作る
- [ ] `Dockerfile` を書く
- [ ] `pyproject.toml` に依存を書く

### frontend

- [ ] `npm create vite@latest frontend -- --template react-ts`
- [ ] `Dockerfile.dev` と `vite.config.ts`（proxy 設定）
- [ ] 画面は「API の health を叩いて結果を出すだけ」でよい

### 環境

- [ ] `docker-compose.yml` を書く
- [ ] `docker compose up` でブラウザに health の結果が出る
- [ ] `.env.example` を書く
- [ ] `.gitignore` を確認（`.env`、`__pycache__`、`node_modules`、`staticfiles` など）

### デプロイ

- [ ] `render.yaml` を書く
- [ ] Blueprint でデプロイ
- [ ] **`08-deploy-render.md` の初回デプロイ手順 4〜8 を実施**（URL 確定後の環境変数入力）
- [ ] 本番 URL でフロントが API の health を叩けることを確認 ← **ここが Day 1 のゴール**
- [ ] Google Cloud に本番の生成元を追加する（Day 0 の宿題を回収）

### CI

- [ ] `.github/workflows/ci.yml` を置く
- [ ] Deploy Hook を Secrets に登録
- [ ] `main` にブランチ保護をかける
- [ ] 適当な PR を出して CI が緑になることを確認

> **Day 1 が終わった時点で、残りは「機能を足す」だけになる。** インフラ由来の問題はここで全部踏んである。

## Day 2 — データ

- [ ] `Library` / `Favorite` モデルを作る（`04-data-model.md`）
- [ ] `backend/data/tokyo_libraries.csv` に図書館名と住所を埋める（30〜50 件、人力）
- [ ] `geocode_libraries` コマンドを書く
      - GSI の住所検索 API を叩く
      - 1 秒スリープ
      - **東京都の範囲外の座標は採用せず警告**
      - 喫煙区分を固定シードの乱数で割り当て
- [ ] `--dry-run` で確認 → fixture を生成して commit
- [ ] `loaddata` で投入
- [ ] Django Admin で中身を目視確認
- [ ] `GET /api/libraries/` と `GET /api/libraries/{id}/` を実装
- [ ] bbox / smoking フィルタのテストを書く

## Day 3 — 地図

- [ ] MapLibre + GSI タイルで地図を表示する
- [ ] `moveend` で bbox を取り、API を叩く（React Query）
- [ ] マーカーを喫煙区分で色分けして表示
- [ ] マーカークリック → 詳細パネル
- [ ] **喫煙区分がダミーデータである旨の注記を出す**
- [ ] 喫煙区分フィルタ UI
- [ ] `truncated` / 0 件 / エラー / ローディングの表示
- [ ] 現在地ボタン（`useGeolocation`）
      - [ ] **拒否されても地図が壊れないことを実際に試す**（ブラウザの設定で拒否して確認）

## Day 4 — 認証

順番が大事。**ID/PW を先に完成させてから Google に進む。**

- [ ] SimpleJWT の設定、`token_blacklist` を追加
- [ ] `POST /api/auth/register/` `login/`
- [ ] **Cookie 版の `refresh/` カスタムビュー**（`06-auth.md`。ここが一番手を動かす）
- [ ] `logout/` `me/`
- [ ] フロント: `AuthContext` + `api/client.ts`（401 → refresh → 1 回だけリトライ）
- [ ] **起動時に refresh を叩いてログイン状態を復帰させる**
- [ ] ログイン / 登録画面
- [ ] ここで一度デプロイして、**本番でリロードしてもログインが維持されるか確認**
      → 維持されなければ Cookie の `SameSite=None; Secure`（`08-deploy-render.md` のエラー表）
- [ ] `POST /api/auth/google/`（ID トークン検証、`aud` と `email_verified` のチェック）
- [ ] フロント: Google Identity Services のボタン
- [ ] 本番で Google ログインを確認

## Day 5 — 仕上げと Should

- [ ] お気に入り（`POST`/`DELETE /api/libraries/{id}/favorite/`、`/favorites` 画面）
- [ ] `nearby`（現在地から近い順）
- [ ] テキスト検索
- [ ] モバイル幅（375px）でレイアウトが崩れないか確認
- [ ] ダークモード
- [ ] `drf-spectacular` で API ドキュメント（任意）
- [ ] README を書く

## 動作確認シナリオ（デプロイ後に毎回通す）

上から順に、本番 URL で実際に手を動かす。所要 5 分。

1. トップを開く → 地図が表示される
2. 東京駅周辺にピンが出ている
3. 地図を新宿方面にドラッグ → ピンが入れ替わる
4. フィルタで「両方可」だけにする → ピンが減る
5. ピンをクリック → 詳細パネルに名称・住所・喫煙区分・ダミー注記が出る
6. 「現在地」ボタン → 許可 → 現在地マーカーが出る
7. ヘッダーの「登録」→ メールとパスワードで登録 → ログイン状態になる
8. **F5 でリロード → ログイン状態のまま**
9. ログアウト → Google ボタンでログイン → ログイン状態になる
10. お気に入りを 1 件登録 → `/favorites` に出る
11. `/login` を**アドレスバーに直接打って開く** → 404 にならない

## 運用メモ

### 無料 Postgres の期限が来たら

```
1. Render で新しい Postgres を作る
2. API の DATABASE_URL を新しい接続文字列に差し替える
3. 再デプロイ（起動時に migrate が走る）
4. Render の Shell から:
     python manage.py loaddata libraries
     python manage.py createsuperuser
```

ユーザーアカウントは消える。**そういうものとして運用する。**

### API がスリープしている

無料 Web Service は 15 分無操作でスリープする。人に見せる前に一度 `https://<api>.onrender.com/api/health/` を開いて温めておく。

### 依存を更新したとき

```bash
docker compose up --build          # ローカルを作り直す
```

`package-lock.json` / `uv.lock`（または `pyproject.toml`）の変更は**必ず commit する**。CI の `npm ci` はロックファイルが無いと失敗する。

## この練習が終わったら

元プロジェクト（[smocking-notes](https://github.com/jovid18/smocking-notes)）に戻ったときに使えるようになっているもの:

| ここで身についたもの | 元プロジェクトでの対応箇所 |
|---|---|
| bbox 検索と地図の再取得 | 店舗の地図表示 |
| 座標の出所を `data_source` に残す習慣 | Google Maps 由来座標の取り扱い |
| ID/PW + ソーシャルを 1 モデルに載せる設計 | Google ログイン + 年齢確認 |
| enum で表す複数状態のフィルタ UI | 喫煙区分（全席可 / 一部可 / 加熱式のみ / 分煙） |
| CI を通過したときだけデプロイする構成 | main マージでのデプロイ |
| 本番と開発の差分表を最初に作っておく発想 | 環境分離 |

**まだ触れていない主な論点**: PostGIS、キャッシュ設計、A/B テスト基盤、LLM の呼び出し、ユーザー投稿の承認フロー。これらは元プロジェクトの設計メモ側に整理がある。
