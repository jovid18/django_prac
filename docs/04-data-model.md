# 04. データモデルとシードデータ

## ER 図

```mermaid
erDiagram
    USER ||--o{ SOCIAL_ACCOUNT : "持つ"
    USER ||--o{ FAVORITE : "登録する"
    LIBRARY ||--o{ FAVORITE : "登録される"

    USER {
        bigint   id PK
        citext   email UK "ログイン ID"
        varchar  password "ソーシャルのみの場合は unusable"
        varchar  display_name
        bool     is_active
        bool     is_staff
        datetime date_joined
        datetime last_login
    }

    SOCIAL_ACCOUNT {
        bigint   id PK
        bigint   user_id FK
        varchar  provider "google / (将来) line"
        varchar  provider_uid "Google の sub"
        datetime created_at
    }

    LIBRARY {
        bigint   id PK
        varchar  name
        varchar  name_kana "任意"
        varchar  address
        varchar  ward "区・市"
        decimal  latitude "9,6"
        decimal  longitude "9,6"
        varchar  smoking_status "4 値"
        varchar  website "任意"
        varchar  data_source "座標の出所"
        datetime created_at
        datetime updated_at
    }

    FAVORITE {
        bigint   id PK
        bigint   user_id FK
        bigint   library_id FK
        datetime created_at
    }
```

## モデル定義

### `apps/accounts/models.py`

```python
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()


class SocialAccount(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        # LINE = "line", "LINE"   # スコープ外。追加するならここ

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_uid = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_uid"], name="uniq_provider_uid"
            )
        ]
```

**設計の意図**

- **`username` を捨てて `email` を `USERNAME_FIELD` にする。** Django のデフォルト User をそのまま使うと、Google ログインのときに埋めようのない `username` が邪魔になる。**カスタム User はマイグレーションを 1 本でも走らせた後だと差し替えが極めて面倒**なので、`Day 1` の最初、`migrate` を打つ前に必ず作ること。
- **ソーシャル連携を `User` のカラムにせず別テーブルにする。** `google_id` カラムを生やす設計にすると、LINE を足すときに `line_id` を足すことになり、プロバイダが増えるたびにスキーマが変わる。`SocialAccount` を分けておけば行が増えるだけで済む。
- **1 ユーザーが ID/PW と Google の両方を持てる。** 同じメールで Google ログインしたら、新規作成ではなく既存ユーザーに `SocialAccount` を紐付ける（`06-auth.md` のアカウント紐付けを参照）。
- パスワードを持たないユーザー（Google のみ）は `set_unusable_password()` にしておく。

### `apps/libraries/models.py`

```python
class SmokingStatus(models.TextChoices):
    NONE          = "none",          "喫煙不可"
    HEATED_ONLY   = "heated_only",   "加熱式のみ可"
    CIGARETTE_ONLY= "cigarette_only","紙巻きのみ可"
    BOTH          = "both",          "両方可"


class Library(models.Model):
    name          = models.CharField(max_length=120)
    name_kana     = models.CharField(max_length=160, blank=True)
    address       = models.CharField(max_length=255)
    ward          = models.CharField(max_length=40, db_index=True)
    latitude      = models.DecimalField(max_digits=9, decimal_places=6)
    longitude     = models.DecimalField(max_digits=9, decimal_places=6)
    smoking_status= models.CharField(
        max_length=20, choices=SmokingStatus.choices, db_index=True
    )
    website       = models.URLField(max_length=300, blank=True)
    osm_id        = models.CharField(max_length=32, blank=True, db_index=True)
    data_source   = models.CharField(
        max_length=20, choices=DataSource.choices, default=DataSource.OSM_OVERPASS
    )
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["latitude", "longitude"], name="idx_library_latlng")]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "latitude", "longitude"], name="uniq_library_spot"
            ),
        ]


class Favorite(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    library    = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "library"], name="uniq_user_library")
        ]
```

**設計の意図**

- **座標は `FloatField` ではなく `DecimalField(9, 6)`。** 小数 6 桁 ≒ 約 11cm の分解能で、日本国内の用途には十分。浮動小数の丸め誤差で `uniq` 判定や差分比較が揺れるのを避ける。
- **`smoking_status` は boolean 2 本ではなく単一の enum。** 「加熱式のみ可」「紙巻きのみ可」を boolean 2 本（`allow_heated` / `allow_cigarette`）で表すこともできるが、元プロジェクトの仕様書でも「単純な boolean では表現できない」と整理されている。フィルタ UI が enum のほうが素直に書ける。
- **UNIQUE 制約は `(name, address)` ではなく `(name, latitude, longitude)`。**
  当初は住所をキーにする想定だったが、実データでは**住所の充足率が 54% しかなかった**（後述）。
  空文字が多いカラムを一意キーに含めると、別々の施設が衝突する。座標なら 100% 埋まっている。
- **`data_source` を持つ。** 座標をどこから取ったかを行ごとに残す。元プロジェクトで Google Maps 由来の座標に保持期限の制約があった件と同じ発想で、**出所を後から追えるようにしておく**習慣をここで付けておく。実装では `osm_overpass` / `gsi_reverse` / `manual` の 3 値。
- **`osm_id` を持つ。** OpenStreetMap 側の要素 ID（`node/416335894`）。元データを引き直したいときに追える。

## 喫煙区分のランダム割り当てについて

**実際の図書館は当然すべて禁煙である。** このフィールドは元ドメイン（喫煙可能店マッチング）のスキーマとフィルタ UI を練習するためだけに存在する。

- シード生成時に、固定シード値の擬似乱数で 4 値のいずれかを割り当てる（`random.Random(42)` のように seed を固定し、再生成しても同じ結果になるようにする）。
- **UI 上に「このデータは練習用のダミーです」と明示する。** 詳細パネルの喫煙区分の横に注記を出す。実在施設に誤った情報を紐付けたまま公開する状態にはしない。
- 分布は均等でなくてよい（例: 不可 40% / 加熱式のみ 25% / 紙巻きのみ 15% / 両方 20%）。フィルタの動作確認ができればよい。

## シードデータの作り方

> **⚠ この節は実装時に方針を変更した。** 当初は「名称と住所の CSV を人力で作り、
> 国土地理院の住所検索で座標を引く」計画だったが、実際に調べたところ
> **OpenStreetMap に東京都の図書館が 490 件、名称と座標が 100% 揃った状態**で
> 存在したため、そちらに切り替えた。
>
> 当初 CSV 方式を採った理由は「確認していない座標をでっち上げないため」だったが、
> 実測値をそのまま使う OSM のほうがその原則をより満たす。人力の CSV 作成（30 件で 30 分）も不要になった。

### 出所

| 項目 | 出所 | 充足率 |
|---|---|---|
| 名称・緯度経度 | **OpenStreetMap**（Overpass API） | 100%（490 件） |
| website | 同上 | 20% |
| 住所 | 同上（`addr:full` ほか） | 54% |
| 区市町村 | `addr:city` → 名称から推定 → **国土地理院 逆ジオコーディング** | **100%**（66 種類） |
| 喫煙区分 | 固定シードの擬似乱数 | **★ ダミー** |

**★ OpenStreetMap のデータは ODbL。出典表示が義務**なので、UI に必ず明記する。

### 区市町村を 3 段階で埋める理由

OSM の住所タグは充足率が低い（`addr:city` は 25%）。一方、日本の公立図書館は
**名称に自治体名が入っている**ことが多い（「北区立中央図書館」→「北区」）。

```
① addr:city がある                    126 件 (25%)
② 名称の先頭から推定  ^(.+?[区市町村])   255 件 (52%)
③ 残りを国土地理院の逆ジオコーディング    109 件 (22%)
                                    ─────────────
                                    490 件 (100%)
```

③ は `muniCd`（自治体コード）を返すので、国土地理院が公開する
[`muni.js`](https://maps.gsi.go.jp/js/muni.js) の対応表で名称に変換する（`13101` → `千代田区`）。

**③ だけで全件やらないのは、公共 API に 490 回叩く必要がないから。** ①② で 78% が
埋まるので、残り 109 件・約 2 分で済む。

### 実行

```bash
# まず件数と警告だけ確認（ファイルは書かない）
docker compose exec api python manage.py fetch_libraries --dry-run --skip-reverse

# 本番実行（逆ジオコーディングを含むので 2 分ほどかかる）
docker compose exec api python manage.py fetch_libraries

# 投入
docker compose exec api python manage.py loaddata libraries
```

### コマンドの設計上の決めごと

| 決めごと | 理由 |
|---|---|
| **Overpass のミラーを 3 つ順に試す** | 公開インスタンスは混雑すると 429 / 504 を返す。実際に開発中 1 回踏んだ |
| **逆ジオコーディングは 1 件 1 秒スリープ** | 公共 API への礼儀 |
| **東京都の想定範囲外の座標は採用せず警告** | 黙って変な座標を入れない |
| **`--dry-run` を用意** | 件数と失敗行だけ見てからファイルを書く |
| **`created_at` / `updated_at` を fixture に含める** | `loaddata` は `save_base(raw=True)` で保存するため `auto_now_add` が効かない。**入れないと NOT NULL 違反で落ちる** |
| **タイムスタンプは固定値** | `timezone.now()` にすると再生成のたびに全 490 行の diff が出る |
| **喫煙区分は固定シードの乱数** | 再生成しても同じ結果になる |

**生成した `libraries.json` は commit する。** 毎回 API を叩かなくても `loaddata` だけで
環境を再現できるようにするため。無料 Postgres が 30 日で消えたときの復旧手段でもある。

### 伊豆・小笠原諸島について

東京都は**伊豆諸島・小笠原諸島まで含む**。取得結果の最南端は緯度 32.46（青ヶ島）で、
これは誤りではない。

そのため `TOKYO_BOUNDS` は都心だけでなく島嶼部を含む広い範囲にしてある。
一方で地図の初期表示は東京駅中心なので、島の図書館は bbox から自然に外れる。
**この挙動はテストで固定してある**（`test_bbox_excludes_izu_islands`）。

## 検索クエリの方針

### bbox 検索（メイン導線）

地図の表示範囲だけを取る。PostGIS は使わず、素直な範囲条件で書く。

```python
qs = Library.objects.filter(
    latitude__gte=min_lat, latitude__lte=max_lat,
    longitude__gte=min_lng, longitude__lte=max_lng,
)
if smoking:                       # 複数指定可
    qs = qs.filter(smoking_status__in=smoking)
qs = qs[:LIMIT]                   # LIMIT は 500 程度
```

`(latitude, longitude)` の複合インデックスが効く。数十件〜数千件の規模ならこれで十分速い。

### 近い順（実装済み）

距離を SQL 側で計算する。実装は `apps/libraries/geo.py`。**`RawSQL` ではなく `Func`**（`ATan2` / `Sqrt` / `Cos` / `Sin` / `Radians`）で組んだ —— 値のバインドを Django に任せて文字列連結を一切しないため。

**採用したのは haversine 公式を `atan2` で解く形。** 当初このページに書いていた「余弦定理 + `acos`」は**捨てた**（理由は下）。

```sql
-- 実際に生成される式の骨格
SELECT *,
       2 * 6371008.8 * atan2(sqrt(a), sqrt(1 - a)) AS distance_m
       -- a = sin²(Δφ/2) + cos(φ1)cos(φ2)sin²(Δλ/2)
FROM libraries_library
WHERE latitude BETWEEN %(min_lat)s AND %(max_lat)s   -- ← 先に bbox で絞る（重要）
  AND longitude BETWEEN %(min_lng)s AND %(max_lng)s
  AND distance_m <= %(radius_m)s                     -- 外接矩形の角を落とす
ORDER BY distance_m, id
LIMIT 20;
```

**必ず bbox で絞ってから距離計算する。** いきなり全行に対して三角関数を回すとインデックスが使えない。

> ### ⚠ 余弦定理（`acos`）で書いていたのを撤回した（Day 5）
>
> **このページに最初に載せていた SQL は間違っていた。** `acos` を 1 の近くで使う形になり、
> 問題が 2 つあった。どちらも「`acos` を 1 の近くで使う」ことに起因する。
>
> **1. 定義域を外れて 500 になる。**
> 数学的には `cos(φ1)cos(φ2)cos(Δλ) + sin(φ1)sin(φ2)` が 1 を超えないが、
> **浮動小数の誤差で超える。** Postgres の `acos` は NaN を返さず
> `DataError: input is out of range` を投げるのでそのまま 500。
> シードの 490 件で基準点を各館の座標そのものにすると、**5 件**で
> `1.0000000000000002` になった（世田谷区立烏山図書館 `35.668836, 139.600528` で再現）。
>
> **2. 距離 0 が 0 にならない。**
> `acos` は 1 の近くで傾きが発散するので精度が落ちる。Postgres で計測すると
> **同一点で `0.1343m`** が出た。
>
> | 公式 | 同一点での結果（490 件の最大値） |
> |---|---|
> | 余弦定理 + `acos` | **0.1343m**（うち 5 件は定義域外で `DataError`） |
> | haversine + `atan2` | **0.0000m** |
>
> **「現在地の真上にある館」は現実に起こる**ので実害がある。
> `test_base_point_on_top_of_a_library_is_exactly_zero` と
> `test_zero_distance_has_no_rounding_floor` で固定した。
>
> 精度そのものは実用上どちらでも足りる（1km 地点での差は 1mm 未満を実測）。
> **問題は「距離 0 付近」だけに出る。**
>
> #### PostGIS ならこれは起きなかった
>
> `ST_Distance` / `ST_DWithin`（`geography` 型）は測地線アルゴリズムで実装されていて、
> **`acos` を自分で書く場面が無い。** つまりこれは
> **「PostGIS を入れない」判断が連れてきたコスト**で、
> `01-overview.md` の Won't 表に書いていた「GDAL/GEOS を入れる手間 vs bbox で十分」
> という比較には入っていなかった項目。
>
> 判断そのものは変えない（490 件で bbox + haversine は十分速く、正しく動いている）。
> ただし**コストの見積りに「数値計算を自分で正しく書く責任」を足しておく。**

`radius_m` / `limit` の上限超えは **400 にせず黙って頭打ちにする**（`radius_m` は 20km、`limit` は 50）。一覧の `limit` と揃えた方針。一方 `lat` / `lng` の**欠落は 400** —— 黙って都全域を返すと「現在地が取れていない」ことがフロントの不具合として現れなくなる。

### PostGIS へのアップグレード経路（今回はやらない）

将来、件数が数万件に増えて上記が苦しくなったら:

1. Postgres に `CREATE EXTENSION postgis;`（Render の Postgres でも有効化できる）
2. Docker イメージに GDAL / GEOS / PROJ を追加インストール
3. `django.contrib.gis` を `INSTALLED_APPS` に追加、`ENGINE` を `django.contrib.gis.db.backends.postgis` に変更
4. `location = models.PointField(geography=True, srid=4326)` を追加するマイグレーション → 既存の緯度経度から値を埋めるデータマイグレーション → GiST インデックス作成
5. 検索を `ST_DWithin` / `ST_Distance` に置き換え

緯度経度カラムは残しておけば API のレスポンス形式を変えずに済む。**この 5 手順が想像できていれば、今 PostGIS を入れない判断は妥当。**

## Django Admin

管理画面は作り込まないが、データ確認用に最低限を設定しておくと `docker compose exec ... shell` を打つ回数が減る。

```python
@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display  = ("name", "ward", "smoking_status", "latitude", "longitude", "data_source")
    list_filter   = ("ward", "smoking_status", "data_source")
    search_fields = ("name", "address")
```
