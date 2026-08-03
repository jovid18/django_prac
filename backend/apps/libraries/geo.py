"""距離計算。PostGIS は使わない（docs/01-overview.md「スコープ外」）。

緯度経度カラム + 素の三角関数で足りる規模（490 件）なので、GDAL / GEOS を
Docker イメージに入れる代わりにこちらを選んでいる。件数が数万件に増えたときの
PostGIS への移行手順は docs/04-data-model.md に書いてある。
"""

import math

from django.db.models import ExpressionWrapper, FloatField, Value
from django.db.models.functions import ATan2, Cast, Cos, Greatest, Least, Radians, Sin, Sqrt

# 地球の平均半径（IUGG）。球面近似なので誤差は 0.5% 程度ある。
# 「近い順に並べる」用途には十分で、測量には使えない。
EARTH_RADIUS_M = 6_371_008.8


def bounding_box(lat: float, lng: float, radius_m: int) -> dict[str, float]:
    """半径 `radius_m` の円を必ず内側に含む緯度経度の範囲。

    **距離計算の前にこれで粗く絞る**（docs/04-data-model.md）。いきなり全行に
    三角関数を回すと `(latitude, longitude)` の複合インデックスが使えない。

    経度側は日付変更線をまたぐことがあり、`BETWEEN` では表せない。その場合は
    `min_lng` / `max_lng` を**返さない**。緯度だけで絞って、あとの正確な距離計算に
    任せる（絞りが緩くなるだけで結果は変わらない）。東京都のデータでは起きないが、
    `lat` / `lng` はクエリパラメータなので任意の値が来る。
    """
    lat_delta = math.degrees(radius_m / EARTH_RADIUS_M)

    # 経度 1 度あたりの距離は緯度が高いほど縮む。極付近で 0 除算になるので下限を切る。
    cos_lat = max(math.cos(math.radians(lat)), 1e-9)
    lng_delta = lat_delta / cos_lat

    box = {
        "min_lat": max(lat - lat_delta, -90.0),
        "max_lat": min(lat + lat_delta, 90.0),
    }
    if -180.0 <= lng - lng_delta and lng + lng_delta <= 180.0:
        box["min_lng"] = lng - lng_delta
        box["max_lng"] = lng + lng_delta
    return box


def distance_m_expression(lat: float, lng: float) -> ExpressionWrapper:
    """基準点から各行までの距離（メートル）を **SQL 側で**計算する式。

    **haversine 公式を `atan2` で解く形**を使う。並べ替えと `LIMIT` を DB に
    任せられるので、Python 側で全件回して sort するより素直。

    `RawSQL` ではなく `Func` で組むのは、値のバインドを Django に任せて
    文字列連結を一切しないため。

    定数側（基準点）の三角関数は Python で先に計算して `Value` で渡す。
    SQL に `radians(%s)` を並べても結果は同じだが、式が短くなる。

    ★★ **当初は球面三角法の余弦定理（`acos`）で書いていた**
       （`docs/04-data-model.md` に載せていた SQL がそれ）。`acos` を 1 の近くで
       使う形になり、2 つの問題があったので haversine に変えた:

       1. **定義域を外れて 500 になる。** 数学的には
          `cos(φ1)cos(φ2)cos(Δλ) + sin(φ1)sin(φ2)` が 1 を超えないが、浮動小数の
          誤差で超える。Postgres の `acos` は NaN ではなく
          `DataError: input is out of range` を投げる。シードの 490 件のうち
          **5 件**で `1.0000000000000002` になることを実測した。
       2. **距離 0 が 0 にならない。** `acos` は 1 の近くで傾きが発散するため
          精度が落ちる。Postgres で計測すると**同一点で 0.1343m** が出た
          （haversine なら 0.0000m）。

       どちらも「`acos` を 1 の近くで使う」ことに起因する。haversine には
       両方とも無い。**PostGIS を使えばそもそも自分で書かないので起きなかった**
       種類の問題で、「PostGIS を入れない」判断のコストとして記録しておく
       （`docs/04-data-model.md`）。
    """
    lat_rad = math.radians(lat)
    lng_rad = math.radians(lng)

    # ★ DecimalField をそのまま渡さず FloatField に Cast する。
    #   Postgres の radians() は double precision しか受けないうえ、Django の
    #   数学関数は入力が Decimal だと出力も Decimal と推論してしまう。
    row_lat = Radians(Cast("latitude", FloatField()))
    row_lng = Radians(Cast("longitude", FloatField()))

    # a = sin²(Δφ/2) + cos(φ1)cos(φ2)sin²(Δλ/2)
    half_d_lat = (row_lat - Value(lat_rad)) / Value(2.0)
    half_d_lng = (row_lng - Value(lng_rad)) / Value(2.0)
    along_meridian = Sin(half_d_lat) * Sin(half_d_lat)
    along_parallel = Value(math.cos(lat_rad)) * Cos(row_lat) * Sin(half_d_lng) * Sin(half_d_lng)
    a = along_meridian + along_parallel

    # a は理論上 [0, 1]。対蹠点付近で誤差が 1 を超えると sqrt(1 - a) が
    # 負数の平方根になるので、念のため挟んでおく（半径 20km では到達しない）。
    a_clamped = Least(Greatest(a, Value(0.0)), Value(1.0))

    # d = 2R * atan2(√a, √(1 - a))
    central_angle = ATan2(Sqrt(a_clamped), Sqrt(Value(1.0) - a_clamped))

    return ExpressionWrapper(Value(2 * EARTH_RADIUS_M) * central_angle, output_field=FloatField())
