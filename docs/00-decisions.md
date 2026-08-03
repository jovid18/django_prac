# 00. Day 0 の決定事項（バージョン固定と根拠）

> 2026-08-03 時点で各公式情報を確認して確定した。**以降のドキュメントの記述はこのファイルを正とする。**
> 変更する場合はここを直し、理由を追記する。

## 確定バージョン

**すべて PyPI / npm のパッケージメタデータを直接読んで確認した**（検索結果の要約ではない）。

| 対象 | 固定するバージョン | 確認したメタデータ |
|---|---|---|
| Python | **3.13**（Docker: `python:3.13-slim`） | **下記「なぜ 3.13 なのか」** |
| Django | **6.0.7** | `requires_python >=3.12` / classifiers: Python 3.12・3.13・3.14 |
| Django REST Framework | **3.17.1** | `requires_python >=3.10` / Django 4.2〜**6.0** / Python 3.10〜3.14 |
| djangorestframework-simplejwt | **5.5.1** | `requires_python >=3.9` / Django 4.2〜**5.2**（**6.0 の記載なし**）/ Python 3.9〜**3.13** |
| PostgreSQL | **16** | ローカルは `postgres:16-alpine`、本番は Render Postgres |
| Python 依存管理 | **uv**（`uv.lock` を commit） | 下記 |
| Node.js | **22 LTS** | ローカルは v22.22.1 |
| React | **19.2.8** | |
| Vite | **8.2.0** | `engines.node`: `^20.19.0 \|\| >=22.12.0` → ローカルの 22.22.1 で条件を満たす |
| TypeScript | 最新（Vite テンプレート準拠） | |

### なぜ Python は 3.13 なのか（3.14 ではなく）

3 つのライブラリが対応を宣言している範囲の**共通部分**が 3.13 までだから。

```
Django 6.0        3.12 ────────── 3.13 ── 3.14
DRF 3.17          3.10 ────────── 3.13 ── 3.14
simplejwt 5.5.1   3.9  ────────── 3.13
                                   ↑
                           共通部分の上限 = 3.13
```

ホストには Python 3.14.2 が入っているが**使わない**。コンテナ内の 3.13 に統一する。

## なぜ Django は LTS（5.2）ではなく最新（6.0）なのか

「React は最新で」という方針をバックエンドにも揃える。**フロントだけ最新でバックだけ 3 年前の系列、という非対称を作らない。**

| ライブラリ | Django 6.0 対応 | 根拠 |
|---|---|---|
| Django REST Framework 3.17.1 | **○** | classifiers に `Framework :: Django :: 6.0` あり |
| djangorestframework-simplejwt 5.5.1 | **実質○**（メタデータが古いだけ） | 下記 |

### simplejwt の「Django 6.0 未対応」は表示上の問題

PyPI の classifiers は Django 5.2 までしか書かれていないが、**これは単にリリースが切られていないだけ**で、実体としては動く。upstream を直接確認した結果:

| 確認項目 | 結果 |
|---|---|
| PR [#959](https://github.com/jazzband/djangorestframework-simplejwt/pull/959) 「add django 6.0 and python 3.14 support」 | **2026-02-09 に master へマージ済み** |
| その PR の変更内容 | 6 ファイル・+26/-9。中身は **CI ワークフロー / tox / pre-commit / docs / setup.py の classifiers のみ**。**アプリケーションコードの変更は 0 行** |
| `requires_dist`（5.5.1） | `django>=4.2` / `djangorestframework>=3.14` — **どちらも上限なし** |
| リポジトリの生存状況 | 最終 push 2026-07-27、star 4.3k、アーカイブされていない |

**読み取れること**

1. 「Django 6.0 対応」の実体は「CI マトリクスに追加したらそのまま通った」であり、**ランタイムのコードは元から 6.0 で動く**
2. 依存指定に上限がないので、**Django 6.0 と一緒にインストールしても解決に失敗しない**
3. classifiers は情報提供用のメタデータであって**インストール時の制約ではない**

**したがって PyPI の 5.5.1 をそのまま使う。** master を git 参照でピン留めする必要はない（コードに差がなく、動くコミットに縛られる不利益だけが残る）。

> 最終リリース 2025-07-21 → Django 6.0 リリース 2025-12-03 → PR マージ 2026-02-09。**master に 1 年分の未リリース分が溜まっている状態。** リリース間隔が長いプロジェクトなので、今後もメタデータが実態より古いことを前提に読む。

LTS（5.2、2028-04 まで）を採る手もあったが、**今回は「Django 6.0 でしか使えない機能を使うから」ではなく「新しい API で覚えるほうが後で困らないから」**最新を選ぶ。練習用リポジトリなので、サポート期限の長さは判断材料にならない。

> **6.0 で入った主な機能**: 組み込みのバックグラウンドタスク、ネイティブ CSP サポート。**今回のスコープでは使わない。**

### 一度撤回した判断の記録

当初「simplejwt が Django 5.2 に未対応の可能性があるので LTS の 5.2 に留める」と書いたが、**これは誤り**だった。参照していたのが simplejwt **4.4.0（旧版）**のページで、実際の 5.5.1 のメタデータには Django 5.2 が含まれている。

**教訓**: 検索結果の要約でバージョン互換を判断しない。**PyPI / npm のメタデータを直接読む。** 上の表はすべてそうやって取り直した。

未対応の表明がないのは **Django 6.0 のみ**で、これは「動かない」ではなく「upstream がまだテストしていない」状態。JWT ライブラリが触る Django の API は比較的安定した領域なので、そのまま動く公算が高い。

### ✅ 実測で確認済み（2026-08-03 / Day 1）

推論だけで終わらせず、実際にインストールして端から端まで動かした。**結果は問題なし。**

```
Django 6.0.7 / DRF 3.17.1 / simplejwt 5.5.1

access token 発行        len=231        ✅
token → user 復元        match=True     ✅  JWTAuthentication 経由
blacklist                rows=1         ✅  ROTATE + BLACKLIST 有効
```

依存解決も 28 パッケージが衝突なしで解決した。**PyJWT 自前実装への切り替えは不要。**

### 実測で分かった追加の制約: `SECRET_KEY` は 32 バイト以上

検証中、PyJWT 2.13 が次の警告を出した。

```
InsecureKeyLengthWarning: The HMAC key is 29 bytes long,
below the minimum recommended length of 32 bytes for SHA256
```

HS256 で署名する以上、**`DJANGO_SECRET_KEY` は 32 バイト以上必要**。

| 環境 | 対応 |
|---|---|
| ローカル | `docker-compose.yml` に書く開発用の値も **32 文字以上**にする |
| 本番 | `render.yaml` の `generateValue: true` が生成する値は十分な長さ |
| Django 標準 | `get_random_secret_key()` は 50 文字なので問題なし |

**短い値を置くと警告が出続けるだけでなく、署名強度が推奨を下回る。**

| | 内容 |
|---|---|
| 影響範囲 | `06-auth.md` の**設計はそのまま使える**。差し替わるのは実装だけ |
| 追加で書く量 | 100〜150 行程度（トークンの発行・検証、DRF の認証クラス、ブラックリスト） |
| なぜ大した話ではないか | **`06-auth.md` では refresh を HttpOnly Cookie でやり取りする都合上、simplejwt の標準ビューをそのまま使えず、どのみちカスタムビューを書く前提になっている。** simplejwt から実際に受け取っていたのは「トークンのエンコード / デコード」「DRF 認証クラス」「ブラックリスト + ローテーション」の 3 つで、前の 2 つは PyJWT で数十行 |
| 唯一まともに手が要る所 | **ブラックリストとローテーション。** ここだけはテストを書いて守る |

## Django と「セッション」の関係（設計上の整理）

Django の認証は層が分かれていて、**セッションは必須ではない**。

| コンポーネント | 役割 | JWT 構成での扱い |
|---|---|---|
| `django.contrib.auth` | User モデル、パスワードハッシュ、権限、`authenticate()` | **使う** |
| `django.contrib.sessions` | 独立したアプリ。セッションテーブル + ミドルウェア | **API では使わない** |
| DRF の `authentication_classes` | リクエスト → `request.user` の決定 | **JWT に差し替える** |

`SessionMiddleware` を完全に外して純粋な JWT 構成にすることもできる。ただし **Django Admin はセッション前提のサーバレンダリングアプリ**なので、Admin を残す以上セッションは有効にしておく。

**結論**: セッションは Admin 用に残し、API の認証は JWT のみ。DRF の `DEFAULT_AUTHENTICATION_CLASSES` に `SessionAuthentication` を**入れない**ことで、この分離を明示する。

## なぜ依存管理は uv か

| | pip | uv |
|---|---|---|
| ロックファイル | なし（`pip freeze` を手で管理） | **`uv.lock`** |
| 速度 | 遅い | 圧倒的に速い（Docker 再ビルドと CI に効く） |
| 仮想環境 | `venv` を別途 | 内蔵 |
| Python 本体の管理 | `pyenv` を別途 | 内蔵 |

**決め手はロックファイル。** ロックが無いと、ローカルと CI と本番が別々のバージョンを引く可能性があり、「CI は緑なのに本番で落ちる」の原因になる。フロント側は `package-lock.json` + `npm ci` で既にロックされているので、**バックエンドだけ緩いのは不整合**。

| 場面 | フロント | バックエンド |
|---|---|---|
| 依存の追加 | `npm install x` | `uv add x` |
| ロック通りに再現 | `npm ci` | `uv sync --frozen` |
| 実行 | `npm run x` | `uv run x` |

**`uv.lock` は必ず commit する**（`package-lock.json` と同じ扱い）。

## なぜ Vite は 8 系か

- 2026-03 に stable、バンドラが Rolldown（Rust 製）に統一され、ビルドが大幅に高速化
- Rolldown 自体も 2026-05 に 1.0 stable、実運用事例あり
- 主要プラグインの互換性テストが整備されている
- 今回は **React の SPA という最も素直な構成**なので、エコシステム互換の問題を踏む可能性は低い

「React は最新版で」という要望に沿って、フロント側は最新を採る。

## 地図: MapLibre + 地理院タイル → **Google Maps に変更**（2026-08-03 / Day 3 の前）

**結論**

| | 変更前 | 変更後 |
|---|---|---|
| 地図エンジン | MapLibre GL JS 6.1.0 | **Google Maps JavaScript API** |
| React ラッパ | `react-map-gl` 8.1.2 | **`@vis.gl/react-google-maps` 1.9.0** |
| クラスタリング | MapLibre の GeoJSON `cluster: true` | **`supercluster` 8.0.1**（下記の理由で `@googlemaps/markerclusterer` から変更） |
| タイル | 国土地理院 淡色ラスター | Google |
| キー / 課金 | どちらも不要 | **API キーと課金アカウントが必要** |

### 変えた理由は「見た目」。ただし実際に描画して比べた

`01-overview.md` で MapLibre + 地理院タイルを選んだ根拠は「キーもクレジットカードも不要」だった。
これは今も正しい。**変えたのは、地理院の淡色ラスターがアプリの主画面としては見劣りしたから。**

推測で決めないために、同じ視点（東京駅 z12.4）に候補を並べて描画し、ダミーのピンを載せて比較した。

| 候補 | 描画 | ラベル | キー | 結果 |
|---|---|---|---|---|
| 地理院 淡色ラスター（変更前） | ○ | 日本語 | 不要 | 実用的だが素っ気ない |
| OpenFreeMap Liberty（ラベル日本語化） | ○ | 日本語 | 不要 | **無料の中では最良。Google に近い** |
| OpenFreeMap positron / dark / fiord | ○ | 併記 | 不要 | ダークの相方が同じ提供元にある |
| CARTO Positron / Dark Matter / Voyager | ○ | z13 未満は英字 | 不要 | 仕上げは綺麗 |
| 地理院 最適化ベクトル | **×（白紙）** | 日本語 | 不要 | スタイルが `pmtiles://` を使う。`pmtiles` パッケージが別途必要 |
| VersaTiles colorful / eclipse | **×** | — | 不要 | タイル配信が接続を切る（`ERR_CONNECTION_RESET`） |

**その上で Google を選んだ。** 日本の施設・道路の見え方と利用者の慣れが、無料であることより優先だと判断した。

### 受け入れたコスト（ここを忘れると事故になる）

| 項目 | 内容 |
|---|---|
| 課金アカウント | **必須。** Cloud プロジェクトを作る時点で billing account が要る（無料枠の内側でも） |
| 無料枠 | Dynamic Maps（地図ロード）は **Essentials で月 10,000 回まで無料**。超過は 1,000 回あたり $7 から。練習用の流量なら収まる |
| **キーの露出** | `VITE_` 変数はバンドルに埋まる。**OAuth クライアント ID と違い、Maps のキーは課金に直結する。** Cloud Console で「HTTP リファラー制限」＋「Maps JavaScript API のみ」を必ず設定する。制限の無いキーを晒すと他人の利用が自分の請求に乗る |
| Map ID | Advanced Markers に**必須**。ローカルは Google 提供の `DEMO_MAP_ID` で足りる |

### 実装前に確認した事実（パッケージのメタデータと dist を直接読んだ）

| 確認項目 | 結果 |
|---|---|
| `@vis.gl/react-google-maps` 1.9.0 の peer | `react >=16.8 \|\| ^19.0` → **React 19.2 で問題なし** |
| 型定義 | `@types/google.maps` を**依存に同梱**。別途インストール不要 |
| ダークモード | `ColorScheme` を export（`LIGHT` / `DARK` / `FOLLOW_SYSTEM`） |
| ⚠ その制約 | `colorScheme` は**地図の初期化時にしか設定できない**。実行中に切り替えるには地図を作り直す（再マウント）必要がある |
| bbox 再取得のきっかけ | `onIdle` / `onBoundsChanged` / `onCameraChanged` を props で受けられる。**MapLibre の `moveend` + 手書きデバウンスより素直** |
| `@googlemaps/markerclusterer` 2.6.2 | `AdvancedMarkerElement` 対応。内部は `supercluster`。**ただし実装時に外した（下記）** |
| 提供元 | `react-map-gl` と**同じ vis.gl チーム**。API の作りが似ているので乗り換えの学習コストが低い |

### 副作用: バンドルが小さくなった（実測）

Maps JS API は Google の CDN から実行時に読み込まれるので、アプリのバンドルには入らない。

```
MapLibre 構成:  index.js 1,181 kB (gzip 317 kB) + CSS 70.7 kB + worker 468 kB
Google 構成:    index.js   191 kB (gzip  61 kB) + CSS  0.9 kB
```

「地図が無い画面（ログイン・お気に入り）でも地図エンジンを丸ごと読ませてしまう」問題が消えたので、
**`MapPage` の遅延読み込み（`React.lazy`）は必須ではなくなった。** 必要になったら入れる。

### 失う練習項目と、その代替

| MapLibre で触るはずだった論点 | Google での対応物 |
|---|---|
| スタイル JSON（`StyleSpecification`） | Cloud ベースのマップスタイル（Map ID に紐づく。コードではなく管理画面） |
| GeoJSON ソース + `circle` レイヤー | `AdvancedMarker`（DOM） |
| 内蔵クラスタリング | `supercluster` を直接使う（MapLibre の `cluster: true` も中身はこれ） |
| `moveend` + デバウンス | `onIdle`（操作が落ち着いてから 1 回発火） |

**ベクトルタイル・スタイル仕様そのものの練習は落ちる。** そこは元プロジェクトでも Google Maps を使う前提なので、
今回は取りに行かない。

### MapLibre 側で分かったこと（戻す時のために残す）

一度 MapLibre 6 で組んで通したので、その知見を捨てずに書いておく。

| 事実 | 影響 |
|---|---|
| `maplibre-gl` 6.0.0 は 2026-07-22 リリース。**ESM 専用**（UMD / CSP バンドルは廃止） | `import maplibregl from` は動かない。`import * as maplibregl` か名前付き import |
| v6 は `map.transform` を削除、イベントをクラス化 | ラッパが追従していないと壊れる。`@vis.gl/react-maplibre` 8.1.2 は `utils/transform.js` で v4/v5/v6 を吸収済み（確認済み） |
| **バンドラでは `setWorkerUrl()` が必須** | Vite は `import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'`。**`?url` だと本番ビルドで worker が兄弟モジュールを失って死ぬ**（dev では動くので気付きにくい） |
| `react-map-gl` 8 は別名パッケージ | 依存は `@vis.gl/react-mapbox` と `@vis.gl/react-maplibre` だけ。ルート export が無く `react-map-gl/maplibre` からしか import できない。**MapLibre だけなら `@vis.gl/react-maplibre` を直接使う** |

## Render の無料枠（確認済みの制約）

**ここが本構成で最も強い制約。** `08-deploy-render.md` に反映済み。

| 項目 | 実際の条件 |
|---|---|
| 無料 PostgreSQL の有効期限 | **作成から 30 日**（以前は 90 日だった）。その後 **14 日の猶予期間**があり、有料に上げなければ**データごと削除される** |
| 無料 PostgreSQL の容量 | 1 GB |
| 無料 PostgreSQL の個数 | **アカウントあたり同時に 1 つまで** |
| バックアップ | **無料 DB は非対応** |
| 無料 Web Service | 一定時間アクセスが無いとスリープ。復帰に時間がかかる |

**対応方針（変更なし）**: シードを fixture として commit してあるので、DB が消えても `migrate` + `loaddata` で復旧できる。ユーザーアカウントは失われるが、練習用途として許容する。

> **「1 アカウントに無料 DB は 1 つ」という制約により、`08-deploy-render.md` で触れていた dev / prod の DB 分離はできない。** 本番 1 本で進める。

## なぜ Terraform を使わないのか

Render には[公式の Terraform プロバイダ](https://render.com/docs/terraform-provider)（`render-oss/render`）があり、`render_web_service` / `render_static_site` / `render_postgres` を管理できる。**それでも今回は `render.yaml`（Blueprint）で行く。**

| | `render.yaml` | Terraform |
|---|---|---|
| 追加ツール | 不要 | Terraform CLI、Render API キー、state の保管先 |
| 変更前の差分確認 | なし | **`terraform plan`** |
| Preview 環境 | 対応 | **Blueprint 専用機能のため不可** |

**判断理由**

1. **リソースが 3 つしかなく、依存関係も `DATABASE_URL` の 1 本だけ。** `terraform plan` の差分確認が活きる場面がない。Terraform が価値を出すのは VPC / サブネット / セキュリティグループ / IAM のように、リソースが多く絡み合っているとき
2. **転用価値が低い。** 元プロジェクト（smocking）で Terraform を想定していたのは AWS（EC2・RDS・ECR・ネットワーク）を管理するため。Render に Terraform を当てて覚えられるのは **Render の API の形**であって、その AWS の概念ではない
3. **コストが練習時間を食う。** state の保管、API キー管理、CI への `plan` / `apply` の追加でおよそ 1 日。その 1 日は Django / React の練習から引かれる

> **Terraform を練習したくなったら、対象は AWS にする。** それは実質的に元プロジェクトそのものなので、この練習リポジトリではやらない。

## 未決定 / 後回しにしたもの

| 項目 | 状態 |
|---|---|
| 独自ドメイン | **買わない**（`08-deploy-render.md` に理由） |
| 独自の地図スタイル（Map ID） | 後回し。まず `DEMO_MAP_ID` で進め、配色を触りたくなったら Cloud Console で作る |
| Terraform | **使わない**（上記） |
| Render のリージョン | Blueprint に `singapore` と書いているが、作成時に選択肢を確認する |
| E2E テスト（Playwright） | Should。Day 5 に余裕があれば |
| `drf-spectacular` | 任意。入れるなら Day 2 |

## 変更履歴

| 日付 | 内容 |
|---|---|
| 2026-08-03 | 初版。Day 0 の調査に基づき全バージョンを確定 |
| 2026-08-03 | **Django を 5.2 LTS → 6.0 に変更。** 5.2 を選んだ根拠（simplejwt の 5.2 非対応疑い）が誤りだったため撤回。フロントと揃えて最新を採る |
| 2026-08-03 | **地図を MapLibre + 地理院タイル → Google Maps に変更。** 候補を実際に並べて描画した結果、見た目を優先。キーと課金アカウントが必要になる点を受け入れた（上の節） |
| 2026-08-03 | `frontend/tsconfig.app.json` に **`strict: true` を追加**。文書には「テンプレートで有効」と書いていたが実際には入っていなかった |
