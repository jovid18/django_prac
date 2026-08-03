# 05. API 仕様

## 共通ルール

| 項目 | 決めごと |
|---|---|
| ベースパス | `/api/` |
| 形式 | JSON のみ（`Content-Type: application/json`） |
| 認証 | `Authorization: Bearer <access_token>`（`06-auth.md`） |
| 日時 | ISO 8601。**オフセット付きの `+09:00`** で返る（`2026-08-03T19:14:02.438780+09:00`）<br>⚠ 当初は「UTC / `Z`」と書いていたが、`TIME_ZONE = "Asia/Tokyo"` かつ `USE_TZ = True` のとき DRF は**現在のタイムゾーン**で描画する。DRF に出力タイムゾーンの設定は無い。曖昧さは無いので**実装に合わせて記述を直した** |
| 命名 | JSON のキーは `snake_case`（Django 側と揃える。フロントで変換しない） |
| 一覧の返し方 | `{"count": n, "results": [...]}`。ページネーションは今回は使わないが、形だけ揃えておく |
| 末尾スラッシュ | **あり**（Django のデフォルトに従う）。フロントの fetch ラッパで必ず付ける |

### エラーレスポンス

DRF のデフォルトに乗せつつ、形を 1 つに統一する。

```json
{
  "detail": "認証情報が含まれていません。",
  "code": "not_authenticated"
}
```

バリデーションエラーはフィールド単位で返す（DRF 標準）:

```json
{
  "email": ["この項目は必須です。"],
  "password": ["パスワードが短すぎます。8 文字以上にしてください。"]
}
```

| ステータス | 使う場面 |
|---|---|
| `200` | 取得・更新の成功 |
| `201` | 作成の成功 |
| `204` | 削除の成功（本文なし） |
| `400` | バリデーションエラー、クエリパラメータ不正 |
| `401` | 未ログイン、トークン期限切れ |
| `403` | ログイン済みだが権限なし |
| `404` | 対象なし |
| `429` | レート制限（`/api/auth/login/` のみ） |

## エンドポイント一覧

| メソッド | パス | 認証 | 用途 |
|---|---|---|---|
| `GET` | `/api/health/` | 不要 | 疎通確認 |
| `POST` | `/api/auth/register/` | 不要 | メール + パスワードで登録 |
| `POST` | `/api/auth/login/` | 不要 | メール + パスワードでログイン |
| `POST` | `/api/auth/google/` | 不要 | Google ID トークンでログイン / 登録 |
| `POST` | `/api/auth/refresh/` | Cookie | アクセストークンの再発行 |
| `POST` | `/api/auth/logout/` | 必要 | リフレッシュトークンの無効化 |
| `GET` | `/api/auth/me/` | 必要 | 自分の情報 |
| `GET` | `/api/libraries/` | 不要 | 図書館の一覧・検索（bbox / フィルタ） |
| `GET` | `/api/libraries/{id}/` | 不要 | 図書館の詳細 |
| `GET` | `/api/libraries/nearby/` | 不要 | 現在地から近い順 |
| `POST` | `/api/libraries/{id}/favorite/` | 必要 | お気に入り登録 |
| `DELETE` | `/api/libraries/{id}/favorite/` | 必要 | お気に入り解除 |
| `GET` | `/api/favorites/` | 必要 | お気に入り一覧 |

> **一覧・詳細は未ログインでも見られる。** 地図を開いた瞬間にログインを求める設計にしない。書き込み（お気に入り）だけログインを要求する。

---

## 認証系

### `POST /api/auth/register/`

```jsonc
// リクエスト
{
  "email": "taro@example.com",
  "password": "correct-horse-battery",
  "display_name": "たろう"          // 任意
}
```

```jsonc
// 201
{
  "user": { /* ↓ me/ と同じ形 */ },
  "access": "eyJhbGciOi..."
}
// + Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=None; Path=/api/auth
```

> **`user` の形は register / login / google / me の 4 つで同一**（実装は 1 つの
> `UserSerializer`）。フロントの `AuthContext` が「どこから来た user か」を
> 気にせず 1 つの型で扱えるようにするため。中身は `me/` の節を参照。

- パスワードは Django の `AUTH_PASSWORD_VALIDATORS` で検証する（最低 8 文字、よくあるパスワードの禁止など）。
- メール重複時は `400` に `{"email": ["この メールアドレス は既に使用されています。"]}`。
  **ただし「登録済みかどうか」を外部から総当たりできてしまう点は認識しておく。** 練習用途なので許容するが、実務ならメール確認フローに逃がす。

### `POST /api/auth/login/`

```jsonc
// リクエスト
{ "email": "taro@example.com", "password": "correct-horse-battery" }
```

```jsonc
// 200 — register と同じ形
{ "user": {...}, "access": "..." }
```

- 失敗時は `401` `{"detail": "メールアドレスまたはパスワードが正しくありません。"}`。
  **どちらが間違っているかは返さない。** 無効化されたユーザー（`is_active=False`）も同じ 401。
- DRF のスロットリングで `5/min`。**スコープ `login` を `register/` と `google/` にも掛けている**
  （どれも総当たりの入口になるため）。成否に関係なく回数を数えるので、6 回目は `429`。
- ⚠ 401 を返すには `AuthenticationFailed` ではなく `status_code = 401` の
  `APIException` が必要（理由は `06-auth.md`「実装して分かったこと」）。

### `POST /api/auth/google/`

```jsonc
// リクエスト — ブラウザが Google から受け取った ID トークンをそのまま渡す
{ "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..." }
```

```jsonc
// 200（既存ユーザー）/ 201（新規作成）
{ "user": {...}, "access": "...", "created": false }
```

詳細な検証手順とアカウント紐付けのルールは `06-auth.md`。

### `POST /api/auth/refresh/`

- **本文なし。** リフレッシュトークンは HttpOnly Cookie で送られる。
- フロントは必ず `credentials: "include"` を付ける。

```jsonc
// 200
{ "access": "..." }
```

- Cookie が無い / 期限切れ / 失効済みなら `401`。**使えない Cookie は同時に削除する**
  （残すと毎回同じ 401 を踏み続ける）。
- **未ログインの初回アクセスもここに来て 401 になる。** 異常ではないので、フロントは
  黙って未ログイン状態にする。ただしブラウザのコンソールには赤い 401 が残る（消せない）。
- `ROTATE_REFRESH_TOKENS = True` なので、**成功時は新しい refresh を Cookie に書き戻す。**
  忘れると 1 回目は通って 2 回目が 401 になる（気づきにくい）。

### `POST /api/auth/logout/`

- リフレッシュトークンをブラックリストに入れ、Cookie を削除する（`204`）。
- **認証が必要**（`Authorization` ヘッダ）。Cookie を消すだけでは、既に盗まれた
  トークンが 14 日間使えてしまうので、ブラックリスト登録まで行う。
- 二重に呼んでも `204`（冪等）。

### `GET /api/auth/me/`

```jsonc
// 200
{
  "id": 1,
  "email": "taro@example.com",
  "display_name": "たろう",
  "has_password": true,
  "providers": ["google"],
  "date_joined": "2026-08-03T00:00:00Z"
}
```

> `has_password` と `providers` を返しておくと、設定画面で「Google のみのアカウントにパスワードを設定する」導線を後から足しやすい。

---

## 図書館系

### `GET /api/libraries/`

地図の**メイン導線**。地図を動かすたびに呼ばれる。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `bbox` | `min_lng,min_lat,max_lng,max_lat` | いいえ | 表示範囲。省略時は東京都全域 |
| `smoking` | カンマ区切り | いいえ | `none,heated_only,cigarette_only,both` のうち複数可。省略時は全件 |
| `q` | 文字列 | いいえ | 名称・住所の部分一致 |
| `ward` | 文字列 | いいえ | 区・市名の完全一致 |
| `limit` | 整数 | いいえ | 既定 `200`、最大 `500` |

```
GET /api/libraries/?bbox=139.68,35.66,139.78,35.72&smoking=both,heated_only
```

```jsonc
// 200
{
  "count": 12,
  "truncated": false,        // limit で打ち切られたか
  "results": [
    {
      "id": 3,
      "name": "新宿区立中央図書館",
      "ward": "新宿区",
      "latitude": "35.xxxxxx",
      "longitude": "139.xxxxxx",
      "smoking_status": "both",
      "smoking_status_label": "両方可"
    }
  ]
}
```

**設計上の決めごと**

- **一覧では `address` / `website` を返さない。** 数百件を地図に載せるので、マーカー描画に要らない項目は詰めない。詳細は個別に取りに行く。
- **`truncated` を返す。** `limit` で切れているのに黙って返すと「ズームアウトすると一部のピンが消える」という説明のつかない挙動になる。フロントは `true` のとき「もっと拡大してください」と出す。
- `bbox` が不正（4 個でない、min > max、数値でない）なら `400`。
- **`bbox` が広すぎる場合も普通に処理する**（東京都全域でも数十件しかない）。件数が増えたらここにガードを足す。
- **`q` は `bbox` と独立して使える。** フロントの検索欄は**`bbox` を送らずに**このエンドポイントを叩き、
  都全域から探して結果へ地図を動かす（`07-frontend.md`「テキスト検索」）。
  `bbox` と併用すると「表示範囲の外にあるものは見つからない」検索になる。
- `smoking_status_label` を一緒に返しておくと、フロントに日本語ラベルの辞書を二重管理せずに済む。

### `GET /api/libraries/{id}/`

```jsonc
// 200
{
  "id": 3,
  "name": "新宿区立中央図書館",
  "name_kana": "",
  "address": "（住所）",
  "ward": "新宿区",
  "latitude": "35.xxxxxx",
  "longitude": "139.xxxxxx",
  "smoking_status": "both",
  "smoking_status_label": "両方可",
  "website": "",
  "data_source": "gsi_geocoding",
  "is_favorited": false,      // 未ログイン時は常に false
  "updated_at": "2026-08-03T00:00:00Z"
}
```

### `GET /api/libraries/nearby/`

| パラメータ | 必須 | 説明 |
|---|---|---|
| `lat`, `lng` | **はい** | 基準点 |
| `radius_m` | いいえ | 既定 `3000`、最大 `20000` |
| `smoking` | いいえ | 一覧と同じ |
| `limit` | いいえ | 既定 `20`、最大 `50` |

```jsonc
// 200 — 一覧の項目に distance_m が付く
{
  "count": 5,
  "results": [
    { "id": 3, "name": "...", "distance_m": 420, ... }
  ]
}
```

**設計上の決めごと**

- `lat` / `lng` が無ければ `400`。**現在地が取れないときにフロントがこれを呼ばない**のが前提（`07-frontend.md`）。黙って都全域を返すと「現在地が取れていない」ことがフロントの不具合として現れなくなる。範囲外（`lat` が ±90 超など）も `400`。
- 一方 **`radius_m` / `limit` の上限超えは `400` にせず頭打ち**（20km / 50 件）。一覧の `limit` と揃えた方針。
- `distance_m` は**メートル単位の整数**。球面近似の誤差が 0.5% 程度あるので小数を返す意味が無い。
- `smoking` は一覧と同じように効く。掛けないとフィルタで除外した館が結果から選べてしまい、地図と食い違う。
- `truncated` は返さない。件数は `radius_m` と `limit` で決まり、`bbox` のような「画面外が切れた」概念が無い。
- 並びは距離昇順。**同距離での揺れを防ぐため `id` を第 2 キー**に入れている。
- ⚠ 距離は **haversine + `atan2`** で計算している。当初計画の「余弦定理 + `acos`」は、距離 0 付近で **500 になる / 0 が 0 にならない**の 2 点があって撤回した。実測は `04-data-model.md`。
- ⚠ ルータの都合で、このアクションは `libraries/{pk}/` より**前**にマッチする必要がある（`{pk}` の正規表現は `nearby` にも当たる）。DRF の `SimpleRouter` が `detail=False` のアクションを detail ルートより先に並べるのでそのままで正しいが、**テストで固定してある**。

### `POST` / `DELETE /api/libraries/{id}/favorite/`

```jsonc
// POST → 201（既に登録済みでも 201）
{ "is_favorited": true }
// DELETE → 204（本文なし。未登録でも 204）
```

- **どちらも冪等。** 二重 POST に `409`、未登録の DELETE に `404` を返すと、
  フロントが押す前に「登録済みか」を問い合わせる作りになる。ボタン連打や
  オフライン復帰後の再送で、結果の状態が同じであればよい。
- 未ログインなら `401`。**存在しない id でも `401`**（権限チェックが先）。
  逆にすると「どの id が存在するか」を未ログインで総当たりできる。
- 存在しない id + ログイン済みなら `404`。
- 閲覧系（一覧・詳細）は `AllowAny` のままで、**このアクションだけ
  `permission_classes` を上書き**している。ViewSet 全体を `IsAuthenticated`
  にすると地図がログイン必須になる。

### `GET /api/favorites/`

```jsonc
// 200
{
  "count": 1,
  "results": [
    {
      "id": 3,
      "name": "新宿区立中央図書館",
      "ward": "新宿区",
      "latitude": "35.xxxxxx",
      "longitude": "139.xxxxxx",
      "smoking_status": "both",
      "smoking_status_label": "両方可",
      "address": "（住所）",
      "favorited_at": "2026-08-03T21:47:49.510365+09:00"
    }
  ]
}
```

**設計上の決めごと**

- **`Favorite` をネストしない。** `{"library": {...}, "created_at": ...}` ではなく
  **一覧の 1 件に `address` と `favorited_at` を足した形**で返す。フロントが地図の
  一覧（`LibraryListItem`）と同じ型で扱えるようにするため。
- **`address` を含める。** この画面には地図が無く、名前だけでは場所が分からない。
  地図の一覧では逆に「描画に要らないので返さない」——**同じ項目でも画面によって
  判断が変わる**例。
- 登録が新しい順。同時刻でも順序が揺れないよう `id` を第 2 キーに入れてある。
- `bbox` で切らないので **`truncated` は無い**。
- ルータの外に `path()` で 1 本置いている。`ViewSet` にすると使わない
  detail / update / destroy まで公開されてしまう。

---

## URL の組み立て

```python
# config/urls.py
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),        # health
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.libraries.urls")),   # libraries/, favorites/
]
```

`libraries` は `ViewSet` + `DefaultRouter` にすると `nearby` を `@action(detail=False)`、`favorite` を `@action(detail=True, methods=["post", "delete"])` で素直に書ける。

## API ドキュメントの自動生成はしない

`drf-spectacular`（OpenAPI スキーマ + Swagger UI の自動生成）を候補に挙げていたが、**入れない**ことにした。

自動推論が効くのは **serializer に素直に乗った ViewSet** のとき。この API はそうなっていない:

- 認証系（`register` / `login` / `google` / `refresh` / `logout` / `me`）は全て手書きの `APIView` で、レスポンス本文を `{"user": ..., "access": ...}` の形に自分で組み立てている
- `libraries` の一覧は `{"count", "truncated", "results"}` を直接返す（serializer はこの外側の形を知らない）
- `favorite` は `{"is_favorited": true}` のリテラル、`favorites` / `nearby` も同様

つまり**ほぼ全てのエンドポイントに `@extend_schema` を手で書く**ことになり、「自動生成」の利点が消える。そのうえこのファイル（実物と合わせて管理している）と二重管理になる。**この文書を正とする。**

> 手を動かして OpenAPI を経験する価値はあるので、元プロジェクト側で必要になったら改めて検討する。

## テストの最低ライン

`pytest` + `pytest-django` で、少なくとも以下は書く。CI で回す（`09-ci-cd.md`）。

| 対象 | ケース |
|---|---|
| register | 正常 / メール重複 / パスワードが弱い |
| login | 正常 / パスワード誤り（`401` かつメッセージが漏れないこと） |
| google | ID トークン検証をモックして、新規作成 / 既存紐付けの 2 分岐 |
| refresh | Cookie あり / なし |
| me | 未認証で `401` |
| libraries 一覧 | bbox で絞れること / `smoking` フィルタ / `bbox` 不正で `400` / `truncated` |
| libraries 詳細 | 存在しない id で `404` |
| favorite | 未ログインで `401` / 二重 POST が冪等 / 未登録の DELETE が `204` / 他人の行を消さない |
| favorites 一覧 | 未ログインで `401` / **自分の行だけ**返る / 新しい順 / `address` と `favorited_at` が入る |
| nearby | `lat` / `lng` 欠落と範囲外で `400` / 距離順 / `distance_m` の桁が妥当 / `radius_m` で絞れる / 上限は頭打ち / **基準点が館の座標と一致したとき距離が厳密に 0**（500 にならない・下駄を履かない） / `libraries/{pk}/` に食われない |

> **お気に入りのテストは JWT を直接発行する**（`RefreshToken.for_user`）。
> `client.force_login` は使えない（API に SessionAuthentication を入れていない）し、
> ログイン API 経由にすると `login` スロットリング（5/min）に引っかかる。
> 実装は `apps/libraries/tests/conftest.py` の `bearer` フィクスチャ。
