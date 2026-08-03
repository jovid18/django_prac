# 10. 着手手順とチェックリスト

## 進め方の原則

1. **Day 1 に一度デプロイまで通す。** 「Hello World が本番 URL で見える」状態を最初に作る。機能を全部作ってから初めてデプロイすると、CORS・Cookie・環境変数の問題が一度に襲ってきて原因の切り分けができなくなる。
2. **カスタム User モデルは最初のマイグレーションより前に作る。** 後から差し替えるのは本当に面倒（`04-data-model.md`）。
3. **一度に 1 つだけ新しいことをする。** 「認証」と「地図」を同時に触らない。片方が壊れたときにもう片方を疑わずに済む。

## Day 0 — 準備（コードを書く前）

**結論は [`00-decisions.md`](00-decisions.md) にまとめてある。**

- [x] Django のバージョンを決める → **6.0**（LTS の 5.2 ではなく最新。理由は `00-decisions.md`）
- [x] 依存管理を決める → **uv**（`uv.lock` を commit）
- [x] フロントのバージョンを決める → **React 19.2 / Vite 8 / Node 22 LTS**
- [x] **無料 Postgres の条件を確認** → 30 日で失効 + 14 日猶予 / 1 GB / アカウントに 1 個 / バックアップ無し
- [x] GitHub にリポジトリを push する
- [x] **Google Cloud Console で OAuth クライアント ID を作る** ← 手作業（`06-auth.md`）
      - 承認済み JavaScript 生成元に `http://localhost:5173` を登録
      - 本番 URL は Day 1 で確定してから追加した
- [x] **Render のアカウントを作る** ← 手作業。GitHub アカウントで sign up してリポジトリへのアクセスを許可する
- [x] **Google Maps の API キーと Map ID を用意する** ← 手作業。**Day 3 の前提**（`00-decisions.md`）
      - OAuth と**同じ Cloud プロジェクト**で「Maps JavaScript API」を有効化する
        （プロジェクト ID: **`django-prac-504402`** / 表示名は `django-prac`。
        コンソールの URL に `?project=django-prac-504402` を付けると迷わない。
        有効化するサービス名は **`maps-backend.googleapis.com`**（名前が一致しないので探しにくい））
      - **課金アカウントの登録が必要**（無料枠の内側でも必須）
      - キーを作ったら**必ず制限を掛ける**: アプリケーションの制限 = HTTP リファラー
        （`http://localhost:5173/*` と本番の Static Site URL）/ API の制限 = Maps JavaScript API のみ
      - `.env` に `GOOGLE_MAPS_API_KEY` を入れる。`GOOGLE_MAPS_MAP_ID` は空でよい（`DEMO_MAP_ID` にフォールバックする）
      - **Quotas で日次上限（300/日 程度）を掛ける。** キーが漏れても請求ではなくエラーで止まる
      - 予算アラートも設定しておく（こちらは事後通知）

> **リスクは調査済み**: `djangorestframework-simplejwt` の Django 6.0 対応は upstream の master にマージ済み（アプリコードの変更は 0 行）で、依存指定にも上限がない。**PyPI の 5.5.1 をそのまま使ってよい。**
> ただし推論なので、Day 1 に 5 分だけ実測する（`00-decisions.md`）。

## Day 1 — 骨組みとデプロイの貫通

**ゴール: 中身は空でいいから、本番 URL でフロントと API が繋がっている状態。**

### backend

- [x] **★ 最優先: simplejwt × Django 6.0 の動作検証** → **合格**（トークン発行・検証・ブラックリストまで実測。`00-decisions.md`）
- [x] `backend/` に Django プロジェクトを作る（`config` 名で）
- [x] `config/settings/{base,local,production}.py` に分割
- [x] **`apps/accounts` を作り、カスタム `User` を定義する（`migrate` の前に！）**
- [x] `apps/core` に `GET /api/health/` だけ作る
- [x] `Dockerfile` を書く（dev / prod のマルチステージ）
- [x] `pyproject.toml` に依存を書く（`uv.lock` を commit）
- [x] `ruff` / `pytest` が通る（9 tests passed）

### frontend

- [x] `npm create vite@latest frontend -- --template react-ts`
- [x] `Dockerfile.dev` と `vite.config.ts`（proxy 設定）
- [x] 画面は「API の health を叩いて結果を出すだけ」
- [x] `npm run build` / `npm run lint`（oxlint）が通る

### 環境

- [x] `docker-compose.yml` を書く
- [x] `docker compose up` で 3 サービスが起動する
- [x] **`localhost:5173/api/health/` が 200**（Vite proxy → Django が通っている）
- [x] `.env.example` を書く / `.env` に Google クライアント ID を投入
- [x] `.gitignore` を確認（`.env`、`*.sqlite3`、`staticfiles/` を追加）

### デプロイ

- [x] `render.yaml` を書く
- [x] Blueprint でデプロイ（`plan` と `region` の指定ミスを 2 件修正）
- [x] URL 確定後の環境変数入力
- [x] **ヘルスチェックのフラッピングを修正**（`SECURE_REDIRECT_EXEMPT`。`08-deploy-render.md`）
- [x] **本番 URL でフロントが API の health を叩ける** ← **Day 1 のゴール達成**
- [x] Google Cloud に本番の生成元を追加（Day 0 の宿題を回収）

**外形確認の結果**

| 項目 | 結果 |
|---|---|
| API の安定性 | 15/15（修正前は 4/15） |
| CORS 許可オリジン | `access-control-allow-origin` + credentials |
| CORS プリフライト | methods / headers 正常 |
| CORS 未許可オリジン | 許可ヘッダなし = 遮断 |
| フロントのビルド時注入 | API URL・クライアント ID ともに反映 |
| `debug` | `false`（production 設定のロード確認） |

### CI

- [x] `.github/workflows/ci.yml` を置く
- [x] Deploy Hook を Secrets に登録
- [x] `main` にブランチ保護をかける
      → 実体は**旧来の branch protection ではなく ruleset**（`main-protection` / enforcement: active）。
        `gh api repos/{owner}/{repo}/branches/main/protection` は 404 を返すので、
        確認するときは `gh api repos/{owner}/{repo}/rulesets` を見る
- [x] PR を出して CI が緑になることを確認（PR #1〜#3 を squash merge 済み）

> **Day 1 が終わった時点で、残りは「機能を足す」だけになる。** インフラ由来の問題はここで全部踏んである。

## Day 2 — データ ✅

- [x] `Library` / `Favorite` モデルを作る（`04-data-model.md`）
- [x] **データ取得方針を変更**: CSV 人力入力 → **OpenStreetMap (Overpass API)**
      - 490 件、名称と座標が 100%。**人力の CSV 作成が不要になった**
      - 区市町村は `addr:city` → 名称推定 → 国土地理院 逆ジオコーディングの 3 段で 100%
- [x] `fetch_libraries` コマンド（ミラー 3 つのフォールバック / `--dry-run` / 範囲外の警告）
- [x] fixture 生成 → commit → `loaddata` で 490 件投入
- [x] Django Admin で確認
- [x] `GET /api/libraries/`（bbox / smoking / ward / q / limit + `truncated`）
- [x] `GET /api/libraries/{id}/`
- [x] テスト 36 件（うち libraries 27 件）

<details>
<summary>当初の計画（CSV 方式）— 参考として残す</summary>

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

</details>

## Day 3 — 地図

> **当初は MapLibre + 地理院タイルの計画だったが、Google Maps に変更した。**
> 候補を実際に描画して比べた結果と、受け入れたコストは `00-decisions.md` の「地図」の節。
> **API キーが無いと地図が出ない**ので、Day 0 の宿題（キー + 制限）を先に済ませる。

- [x] `APIProvider` を巻く（キーは `env.googleMapsApiKey`）
      → **`main.tsx` ではなく `MapPage` に置いた。** マウントした時点で Maps JS の読み込みが
        始まるので、地図が無い画面にまで巻くと無駄な map load になる
- [x] `<Map>` で地図を表示する（`mapId` / `defaultCenter` = 東京駅 / `minZoom: 9` / `gestureHandling: greedy` / `reuseMaps`）
      - [x] **親要素の高さを確定させる** → `index.css` の `main { max-width }` が地図の `<main>` に
            当たって**幅が 0 になり真っ白**になった。要素セレクタでレイアウトを決めない（`07-frontend.md`）
      - [x] `language="ja"` / `region="JP"` を固定（既定はブラウザ言語に追従するので、
            韓国語ブラウザだと東京の地図にハングルのラベルが出た）
- [x] `onIdle` で `map.getBounds()` から bbox を取り、API を叩く（React Query）
      - `onIdle` は操作が落ち着いてから 1 回発火するので、**自前のデバウンスは要らない**
      - `queryKey` に入れる bbox は小数第 3 位に丸める
      - ⚠ API の `latitude` / `longitude` は **文字列**で返る（`DecimalField` + DRF 既定）。`Number()` で変換する
- [x] `AdvancedMarker` + `Pin` を喫煙区分で色分けして表示 + 凡例（フィルタ UI が凡例を兼ねる）
- [x] **クラスタリングを最初から入れる**（1 画面に最大 200 件 = DOM ノード 200 個になりうる）
      → **`@googlemaps/markerclusterer` は外して `supercluster` を直接使う。** 前者はマーカーの
        DOM 要素から座標を読むため、要素に `position` が入る前に計算してしまい
        **クラスタが 1 つも作られなかった**（`00-decisions.md` / `07-frontend.md`）
      - [x] `radius: 120`（= 画面上 60px）。実測で DOM のマーカー要素が 200 → 88 個に減った
- [x] マーカークリック → 詳細パネル（詳細は `GET /api/libraries/{id}/`）
- [x] **喫煙区分がダミーデータである旨の注記を出す**（ヘッダー / フィルタ / 詳細パネルの 3 か所）
- [x] **図書館データの出典（OpenStreetMap / ODbL）を画面に出す**（Google のロゴは自動で出る）
- [x] 喫煙区分フィルタ UI
- [x] `truncated` / 0 件 / エラー / ローディングの表示
- [x] **地図自体が読めなかったときの表示**（キー未設定 / `VITE_MAP_ENABLED=0` はプレースホルダ）
      - [ ] リファラー制限違反・請求先無効のときの見え方は未確認（Google が地図上にエラーを出す）
- [x] ダークモードは `colorScheme="FOLLOW_SYSTEM"` で当てる
      - ⚠ `colorScheme` は初期化時のみ有効。アプリ内トグルを付けるなら `<Map key={scheme}>` で
        作り直す = **切り替えごとに 1 map load** なので、トグルは UI 側だけに効かせるほうが安い
- [x] 現在地ボタン（`useGeolocation`）
      - [x] 許可された場合に現在地マーカー + `panTo` + zoom 14
      - [ ] **拒否されたときの挙動を実際に試す**（実装はしてあるが未検証。ブラウザの設定で拒否して確認）
- [x] `streetViewControl={false}` / `mapTypeControl={false}`（Street View は別 SKU）
- [x] 開発中に地図を描かないスイッチ（`VITE_MAP_ENABLED=0`）
- [x] **Cloud Console の Quotas で日次上限を掛ける**（300/日。無料枠 10,000/月 ≒ 333/日）← 手作業
      → 予算アラートは事後通知なので、**上限のほうが本命**。リファラー制限は `curl` で Referer を
        偽装できるため請求を止められない。詳細は `07-frontend.md`「課金の単位を間違えないこと」
- [x] **本番にデプロイして地図が出ることを確認**
      - Static Site の環境変数（`VITE_GOOGLE_MAPS_API_KEY`）は**ビルド時に埋まる**ので、
        値を入れてから main にマージする順序にした（後だと Manual Deploy がもう 1 回必要）
      - キーのリファラー制限に本番 URL を追加済み。**Console にエラーが出ないことまで確認**
        （`RefererNotAllowedMapError` が出ていない = 制限が正しい）
- [ ] モバイル幅（375px）で地図とパネルが破綻しないか確認（CSS は書いたが未検証）

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

### 無料 Postgres の期限が来たら（30 日ごと）

```
1. Render で新しい Postgres を作る
2. API の DATABASE_URL を新しい接続文字列に差し替える
3. 再デプロイ（起動時に migrate が走る）
4. External Database URL を使ってローカルからシードを流し込む
     docker compose exec -T -e DATABASE_URL="<external url>?sslmode=require" \
       api python manage.py loaddata libraries
```

**無料プランは Shell 接続が使えない**ので、コンテナに入って実行する手はない。
手順の詳細と注意点は `08-deploy-render.md`「本番 DB へのシード投入」。

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
