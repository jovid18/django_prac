# 05. API 仕様

## 共通ルール

| 項目 | 決めごと |
|---|---|
| ベースパス | `/api/` |
| 形式 | JSON のみ（`Content-Type: application/json`） |
| 認証 | `Authorization: Bearer <access_token>`（`06-auth.md`） |
| 日時 | ISO 8601 / UTC（`2026-08-03T12:34:56Z`） |
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
| `GET` | `/api/libraries/nearby/` | 不要 | 現在地から近い順（Should） |
| `POST` | `/api/libraries/{id}/favorite/` | 必要 | お気に入り登録（Should） |
| `DELETE` | `/api/libraries/{id}/favorite/` | 必要 | お気に入り解除（Should） |
| `GET` | `/api/favorites/` | 必要 | お気に入り一覧（Should） |

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
  "user": { "id": 1, "email": "taro@example.com", "display_name": "たろう" },
  "access": "eyJhbGciOi..."
}
// + Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=None; Path=/api/auth
```

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
  **どちらが間違っているかは返さない。**
- DRF のスロットリングで `5/min` 程度の制限をかける。

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

- Cookie が無い / 期限切れ / 失効済みなら `401`。フロントはこれを見てログイン画面に飛ばす。

### `POST /api/auth/logout/`

- リフレッシュトークンをブラックリストに入れ、Cookie を削除する（`204`）。

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
| `q` | 文字列 | いいえ | 名称・住所の部分一致（Should） |
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

### `GET /api/libraries/nearby/`（Should）

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

- `lat` / `lng` が無ければ `400`。**現在地が取れないときにフロントがこれを呼ばない**のが前提（`07-frontend.md`）。

### `POST` / `DELETE /api/libraries/{id}/favorite/`（Should）

- `POST` → `201`（既に登録済みでも `201` を返して冪等にする）
- `DELETE` → `204`（未登録でも `204`）
- 未ログインなら `401`

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

## API ドキュメントの自動生成（任意だが推奨）

`drf-spectacular` を入れると OpenAPI スキーマと Swagger UI が生えて、フロント実装時に手元で叩けるようになる。

```
/api/schema/          → OpenAPI YAML
/api/schema/swagger/   → Swagger UI（DEBUG 時のみ公開）
```

**本番では Swagger UI を出さない**（`DEBUG` で分岐する）。

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
| favorite | 未ログインで `401` / 二重 POST が冪等 |
