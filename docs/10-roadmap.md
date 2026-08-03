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
      - [x] リファラー制限違反のときの見え方を確認した（Day 4。`http://<LAN IP>:5173` から開いて
            **実際に `RefererNotAllowedMapError` を起こした**）。分かったことが 3 つあり、
            **どれも実害だったので直した**（`07-frontend.md`「地図の『キーが弾かれた』を検出する」）:
        1. `APIProvider` のロード状態では検出できない（読み込み成功**後**に失敗するため）
           → `window.gm_authFailure` を使う
        2. Google のエラー画面は**ライト配色固定**でダークモードに追従しない → 自前表示に差し替え
        3. **アプリ全体が真っ暗になる。** 壊れた地図の上で `<AdvancedMarker>` が例外を投げ、
           React 19 がツリー全体を unmount する → **地図の周りにエラーバウンダリを置いた**
        - フッターが「152 件表示中」と嘘をついていたのも直した（地図が死んでも API は生きている）
- [x] ダークモードは `colorScheme="FOLLOW_SYSTEM"` で当てる
      - ⚠ `colorScheme` は初期化時のみ有効。アプリ内トグルを付けるなら `<Map key={scheme}>` で
        作り直す = **切り替えごとに 1 map load** なので、トグルは UI 側だけに効かせるほうが安い
- [x] 現在地ボタン（`useGeolocation`）
      - [x] 許可された場合に現在地マーカー + `panTo` + zoom 14
      - [x] **拒否されたときの挙動を実際に試した**（Day 4）。
            ブラウザの設定をいじる代わりに **Permissions Policy で拒否させた**:
            `<iframe src="/" allow="geolocation 'none'">` に自分自身を埋めると、
            同一オリジンでも `getCurrentPosition` が **code 1（`PERMISSION_DENIED`）**で失敗する。
            結果は設計どおり —— 「位置情報が拒否されています。ブラウザの設定から許可してください。」が出て、
            **地図と検索は動いたまま**（152 件表示中）。
            ⚠ `allow=""` では拒否にならない（空文字は「指定なし」= 既定の `self` が効く）。
            `geolocation 'none'` と明示する必要がある
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
- [x] モバイル幅（375px）で地図とパネルが破綻しないか確認（Day 4 に実測）
      - 横スクロールなし、ヘッダーは 1 行に収まる
      - **実害を 1 件発見して修正: 詳細パネルが Google のロゴを覆っていた。**
        480px 以下でパネルを左右いっぱいに広げているため、地図左下のロゴに重なる。
        **ロゴと著作権表示を覆うのは規約違反**なので `bottom: 36px` で持ち上げた。
        デスクトップ幅では右寄せなので当たらない = **幅を変えて見るまで気づけない類の不具合**

## Day 4 — 認証

順番が大事。**ID/PW を先に完成させてから Google に進む。**

- [x] SimpleJWT の設定、`token_blacklist` を追加（Day 1 で設定済み。ここでは使い始めただけ）
- [x] `POST /api/auth/register/` `login/`
- [x] **Cookie 版の `refresh/` カスタムビュー**（`06-auth.md`。ここが一番手を動かす）
      - ローテーションした refresh を Cookie に書き戻す。**忘れると 2 回目が 401**
      - 使えない Cookie は 401 と一緒に削除する
- [x] `logout/` `me/`
- [x] フロント: `AuthContext` + `api/client.ts`（401 → refresh → 1 回だけリトライ）
      - **refresh は single-flight。** StrictMode の二重マウントでローテーションが競合する
- [x] **起動時に refresh を叩いてログイン状態を復帰させる**
- [x] ログイン / 登録画面（`AuthPage` 1 枚で両方を兼ねる）+ `react-router` 導入
- [x] `POST /api/auth/google/`（ID トークン検証、`aud` と `email_verified` のチェック）
      - sub で突き合わせ / 同一メールの既存ユーザーへの紐付け / client_id 未設定なら 503
- [x] フロント: Google Identity Services のボタン（`?hl=ja` でラベルを日本語に固定）
- [x] **ローカルで一通り通した**（ブラウザで実測）
      - 登録 → 地図に戻ってログイン状態 / **F5 でログイン維持** / ログアウト → 再ログイン
      - パスワード誤りで「メールアドレスまたはパスワードが正しくありません。」
      - `refresh` は StrictMode でも **1 回だけ**飛ぶ
      - **未ログインでも地図・一覧・詳細が見られる**ことを Cookie 無しの独立コンテキストで確認
- [x] テスト 71 件（うち accounts 33 件）
- [x] **本番でリロードしてもログインが維持されることを確認**（Chrome。PR #7 マージ後に実測）
      - `Set-Cookie` は `SameSite=None; Secure; HttpOnly; Path=/api/auth` で正しく出ている
      - 登録 → **F5 → ログイン状態のまま**（`refresh` 200 → `me` 200）
      - ⚠ フロントと API は `*.onrender.com` の別サブドメインで、**別サイト扱い**になる
        （`onrender.com` は Public Suffix List に載っている）。リフレッシュ Cookie は
        third-party cookie なので、**Safari やサードパーティ Cookie ブロック下では
        維持されない見込み（未検証）。** 根本回避は独自ドメインしかないので受け入れる（`06-auth.md`）
- [x] **本番で Google ログインを確認**（実アカウントでのサインインまで完了）
      - [x] クライアント ID がビルドに埋まっている（ボタンが描画される）
      - [x] **`[GSI_LOGGER]: The given origin is not allowed for the given client ID` が出ない**
            = 承認済み JavaScript 生成元に本番 URL が登録できている。
            これが「本番だけ Google ログインが動かない」の最頻出原因なので、ここを先に潰した
      - [x] ボタンのラベルが日本語（`?hl=ja` が本番でも効いている）
      - [x] API 側の `GOOGLE_OAUTH_CLIENT_ID` 設定済み（不正トークンで **401**。
            未設定なら 503 を返す実装なので、これで切り分けられる）
      - [x] 実際の Google アカウントでサインインしてログインできた ← 手作業で確認

> **Day 4 は完了。** 未検証で残っているのは **Safari でのログイン維持**だけで、
> これは実装の不備ではなく third-party cookie の制約（上記）。

## Day 4 の残り課題（Day 5 で拾う）

- [x] フォームの入力欄に `name` / `id` を付ける。`<label>` で包んであるので**アクセシビリティ上の
      関連付けはできている**が、Chrome が `A form field element should have an id or name
      attribute` を出す。パスワードマネージャの自動入力の効きが弱いのが実害
      → 3 つの入力欄に `id` / `name` を付け、`<label htmlFor>` も明示した。
        **ブラウザのコンソールから当該の警告が消えたことを確認済み**

## Day 5 — 仕上げと Should

### お気に入り ✅

- [x] `POST` / `DELETE /api/libraries/{id}/favorite/`（**どちらも冪等**。`05-api.md`）
      - 閲覧は `AllowAny` のまま、**このアクションだけ `permission_classes` を上書き**する。
        ViewSet 全体を `IsAuthenticated` にすると地図がログイン必須になる
      - 未ログインは**存在しない id でも `401`**（権限チェックが先）。
        逆にすると「どの id が存在するか」を未ログインで総当たりできる
- [x] `GET /api/favorites/`
      - **ルータの外に `path()` で 1 本**置いた。`ViewSet` にすると使わない
        detail / update / destroy まで公開されてしまう
      - **`Favorite` をネストせず、一覧の 1 件に `address` と `favorited_at` を足した形**で返す。
        フロントが地図と同じ `LibraryListItem` として扱えるようにするため
      - `Library.objects.filter(favorites__user=u).annotate(...)` にしていない。
        多値リレーションへの join なので join が再利用されるかで件数が変わりうる。
        `Favorite` を主体に `select_related` で 1 クエリ回すほうが読んで分かる
- [x] フロント: `RequireAuth` / `/favorites` 画面 / 詳細パネルの ☆ ボタン
      - **`/favorites` には地図を置かない**（`APIProvider` を巻くと map load が 1 増えるだけ）。
        代わりに API から `address` をもらう
      - 星の状態は**詳細（`is_favorited`）だけが持つ**。一覧に入れると数百件に対して N+1
      - 未ログインで押されたら**ログイン画面に飛ばす**（ボタンは隠さない）
- [x] テスト 87 件（うち favorite 16 件）
- [x] **ローカルで一通り通した**（ブラウザで実測）
      - 登録 → ピンをクリック → ☆ が ★ に変わる → `/favorites` に出る → 解除で行が消える
      - **`/favorites` を開いた状態で F5 → ログイン状態のまま**（`RequireAuth` の `loading` 分岐）
      - ログアウト後に `/favorites` を直打ち → `/login` にリダイレクト
      - 未ログインで ☆ を押す → `/login` → ログイン → **元の地図画面に戻る**
      - コンソールにエラー・警告なし（Day 4 のフォーム警告も消えている）
- [x] **375px で 1 件不具合を発見して修正: 一覧の badge が画面幅いっぱいの赤い帯になっていた。**
      grid を `1fr auto auto` にしていて、モバイル幅で下段に落ちた badge が `1fr` の列を
      受け取っていた。デスクトップ幅では `auto` 列なので当たらない =
      **幅を変えて見るまで気づけない類**（Day 3 の「パネルが Google のロゴを覆う」と同じ性質）

### テキスト検索 ✅

**バックエンドは 0 行。** `q` フィルタは Day 2 で実装済みだった（テストは 2 件足した）。

- [x] 検索ボックス（地図の左上、喫煙区分フィルタの上）+ 結果パネル
- [x] **`bbox` を送らない = 都全域を検索する。** 付けると八王子を見ながら
      「新宿」を検索して 0 件、という説明のつかない挙動になる
- [x] 結果をクリック → `map.panTo` + `setZoom(16)` + 詳細パネルを開く
      - **カメラを制御にしない**（`center` / `zoom` を渡すと操作のたびに React に
        戻ってきて地図が重くなる）。現在地ボタンと同じ `panTo` を使う
      - ⚠ `useMap()` は `<Map>` の内側でしか取れない。検索ボックスは地図の**外**に
        置きたいので、`<Map>` の中に「インスタンスを親へ渡すだけ」の
        `MapInstanceReporter` を噛ませた。**`<MapControl>` で内側に入れると、
        地図が死んだときに検索ボックスまで消える**（Day 3 の方針に反する）
- [x] **地図のピンは絞り込まない。** 検索は「探して飛ぶ」導線で、
      表示中のピンを減らすフィルタではない（それは喫煙区分の役割）
- [x] 250ms デバウンス。**日本語入力は変換の途中でも `onChange` が飛ぶ**ので、
      無いと 1 打鍵ごとにリクエストが出る
- [x] 上限 20 件。切れたら「上限 20 件を表示」と出す（一覧の `truncated` と同じ）
- [x] テスト 89 件（`q` が住所にも当たること / bbox 抜きで都全域になることを追加）
- [x] **ローカルで一通り通した**（ブラウザで実測）
      - 東京駅を見た状態で「八王子」→ 5 件 → クリックで
        **z12 東京駅 → z16 八王子へ移動**し詳細パネルが開く
      - 「図書館」で 20 件 + 「上限 20 件を表示」/ 該当なしのメッセージ
      - Escape・外側クリック・× で閉じる / フォーカスで開き直す
      - 375px: パネルがフィルタに重なる（押し下げない）・横スクロールなし
      - **`window.gm_authFailure()` を直接叩いて「地図が死んだ」状態を作り、
        検索と詳細パネルが動き続けることを確認**（`panTo` だけが無効になる）

> ⚠ **住所は 490 件中 264 件しか入っていない**（OSM 由来）。「名称・住所で検索」と
> 謳っているが、住所側のヒット率はデータの埋まり具合に依存する。

### `nearby`（現在地から近い順）✅

- [x] `GET /api/libraries/nearby/`（`lat` / `lng` 必須、`radius_m` 既定 3km・上限 20km、`limit` 既定 20・上限 50）
      - **PostGIS は使わない。** 緯度経度カラム + 球面三角法（`apps/libraries/geo.py`）。
        判断の理由と移行手順は `01-overview.md` / `04-data-model.md`
      - `RawSQL` ではなく **`Func`（`ATan2` / `Sqrt` / `Cos` / `Sin` / `Radians`）で組んだ。**
        値のバインドを Django に任せて文字列連結を一切しないため
      - **必ず bbox で粗く絞ってから距離計算する。** いきなり全行に三角関数を回すと
        `(latitude, longitude)` の複合インデックスが使えない
      - `lat` / `lng` の**欠落は 400**。黙って都全域を返すと「現在地が取れていない」ことが
        フロントの不具合として現れなくなる。一方 `radius_m` / `limit` の上限超えは頭打ち
- [x] **★ 距離の公式を余弦定理（`acos`）から haversine（`atan2`）に変えた。**
      `04-data-model.md` に最初から書いてあった SQL は**間違っていた。**
      `acos` を 1 の近くで使う形になっていて、問題が 2 つあった:
      1. **500 になる。** 誤差で `cos` が 1 をわずかに超え、Postgres の `acos` は
         NaN ではなく `DataError: input is out of range` を投げる。基準点を館の座標
         そのものにすると**シード 490 件のうち 5 件で再現**（世田谷区立烏山図書館）
      2. **距離 0 が 0 にならない。** `acos` は 1 の近くで傾きが発散して精度が落ちる。
         Postgres で計測すると**同一点で 0.1343m**（haversine なら 0.0000m）
      「現在地の真上にある館」は現実に起こるので実害。テスト 2 件で固定した。
      **PostGIS を使っていれば `acos` を自分で書かないので起きなかった問題**で、
      「PostGIS を入れない」判断のコストとして `01-overview.md` の Won't 表に追記した
      （判断そのものは変えない）
- [x] フロント: 「現在地から近い順」ボタン + 結果パネル（距離つき）
      - **検索と同じパネルを 2 モードで共有。** 375px で左に 3 段積むと地図が見えなくなる
      - **`useGeolocation` は `MapPage` で 1 回だけ呼ぶ。** 現在地ボタン（地図の内側）と
        「近い順」（地図の外側）がそれぞれ呼ぶと**許可を 2 回求める**ことになる
      - 現在地が無いときは**API を呼ばない**（`enabled` で保証）。案内文はパネルに出す
      - `queryKey` の座標は小数第 4 位に丸める（GPS の揺れでキャッシュが無効になるのを防ぐ）
      - **当初案（`07-frontend.md`）の「ボタンを無効化して案内文」は変更した。**
        押せないボタンは理由が伝わらないので、押せるままにしてパネル側に出す
- [x] **`LibraryResultList` を共通化した。** 「汎用化したいものが 2 つ以上出てから作る」という
      自分のルールが初めて発動した箇所（検索結果に続いて近い順が 2 つ目）
- [x] テスト 112 件（うち nearby 23 件。89 → 112）
- [x] **ローカルで一通り通した**（Chrome の位置情報を東京駅に偽装して実測）
      - 「現在地から近い順」→ 20 件が距離順（1.1km / 1.3km / 1.4km …）
      - 結果をクリック → その館へ z16 で移動 + 詳細パネル
      - `getCurrentPosition` を code 1 で失敗させて**拒否時の案内文**を確認（API は呼ばれない）
      - 375px: 横スクロールなし / Google のロゴを覆わない
      - コンソールは `refresh` の 401 だけ（既知・消せない）

### まだ残っているもの

- [ ] README を書く
- ~~`drf-spectacular` で API ドキュメント~~ → **入れない判断をした**（`05-api.md`）。
      手書きの `APIView` が多く、ほぼ全エンドポイントに `@extend_schema` を書く必要があり、
      「自動生成」の利点が消えるうえ `05-api.md` と二重管理になる
- [ ] README を書く
- [x] ダークモード（Day 1〜3 で実装済み。UI 側は `prefers-color-scheme`、
      地図側は `colorScheme="FOLLOW_SYSTEM"`。Day 5 のお気に入り画面も同じ変数で追従する）
- [x] モバイル幅（375px）でレイアウトが崩れないか確認（地図画面は Day 4、
      お気に入り画面は Day 5 に実測。どちらも横スクロールなし）

> **お気に入りから地図へ飛ぶ導線（「地図で見る」）は入れていない。**
> `MapView` の中心は `defaultCenter`（非制御）なので、外から座標を渡すには
> カメラを制御に変える必要があり、それは「操作が重くなる」ので避けた設計
> （`07-frontend.md`）。やるなら `map.panTo` を使う別の口を用意する。

## 動作確認シナリオ（デプロイ後に毎回通す）

上から順に、本番 URL で実際に手を動かす。所要 5 分。

1. トップを開く → 地図が表示される
2. 東京駅周辺にピンが出ている
3. 地図を新宿方面にドラッグ → ピンが入れ替わる
4. フィルタで「両方可」だけにする → ピンが減る
5. ピンをクリック → 詳細パネルに名称・住所・喫煙区分・ダミー注記が出る
6. **検索欄に「八王子」と入れる → 結果をクリック → 地図が八王子まで飛ぶ**
   （表示範囲の外を検索できていることの確認。都心を見たまま実行する）
7. 「現在地」ボタン → 許可 → 現在地マーカーが出る
8. **「現在地から近い順」→ 距離つきで並ぶ → 1 件クリックしてその館へ飛ぶ**
9. ヘッダーの「登録」→ メールとパスワードで登録 → ログイン状態になる
10. **F5 でリロード → ログイン状態のまま**
11. ログアウト → Google ボタンでログイン → ログイン状態になる
12. お気に入りを 1 件登録 → `/favorites` に出る
13. `/login` を**アドレスバーに直接打って開く** → 404 にならない

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
