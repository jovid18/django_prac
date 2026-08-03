"""近い順（docs/05-api.md「図書館系」）。

PostGIS を使わず緯度経度カラム + 球面三角法で出しているので、
**距離の値そのものが妥当か**をここで固定しておく。
"""

import math

import pytest

from apps.libraries.geo import bounding_box
from apps.libraries.models import SmokingStatus

pytestmark = pytest.mark.django_db

NEARBY_URL = "/api/libraries/nearby/"

# conftest の libraries フィクスチャの座標
TOKYO_STATION = {"lat": "35.681236", "lng": "139.767125"}


def names(res):
    return [r["name"] for r in res.json()["results"]]


# --- ルーティング ---------------------------------------------------------


def test_nearby_is_not_swallowed_by_the_detail_route(client, libraries):
    """`libraries/{pk}/` の pk 正規表現は `nearby` にも当たる。

    ルータが detail=False のアクションを detail ルートより先に並べているから
    通っている。順序が変わると 404 になるのでここで固定する。
    """
    res = client.get(NEARBY_URL, TOKYO_STATION)

    assert res.status_code == 200


def test_nearby_requires_no_login(client, libraries):
    assert client.get(NEARBY_URL, TOKYO_STATION).status_code == 200


# --- 必須パラメータ -------------------------------------------------------


@pytest.mark.parametrize(
    "params,missing",
    [
        ({}, "lat"),
        ({"lat": "35.68"}, "lng"),
        ({"lng": "139.76"}, "lat"),
    ],
)
def test_lat_lng_are_required(client, libraries, params, missing):
    """座標が無ければ 400。黙って都全域を返さない。"""
    res = client.get(NEARBY_URL, params)

    assert res.status_code == 400
    assert missing in res.json()


@pytest.mark.parametrize(
    "params",
    [
        {"lat": "abc", "lng": "139.76"},
        {"lat": "35.68", "lng": "abc"},
        {"lat": "95", "lng": "139.76"},
        {"lat": "35.68", "lng": "200"},
    ],
)
def test_invalid_coordinates_are_rejected(client, libraries, params):
    assert client.get(NEARBY_URL, params).status_code == 400


# --- 並び順と距離 ---------------------------------------------------------


def test_results_are_ordered_by_distance(client, libraries):
    """東京駅を基準にすると、東京駅前 → 丸の内 → 新宿の順になる。"""
    res = client.get(NEARBY_URL, {**TOKYO_STATION, "radius_m": 20000})

    assert names(res) == ["東京駅前図書館", "丸の内図書館", "新宿中央図書館"]


def test_distance_m_is_returned_and_plausible(client, libraries):
    """東京駅 → 新宿中央図書館は実測で約 5.5km。

    球面近似なので厳密ではないが、桁が違っていたら計算式が壊れている。
    """
    res = client.get(NEARBY_URL, {**TOKYO_STATION, "radius_m": 20000})
    by_name = {r["name"]: r["distance_m"] for r in res.json()["results"]}

    assert by_name["東京駅前図書館"] == 0
    assert 5000 < by_name["新宿中央図書館"] < 6500
    assert isinstance(by_name["丸の内図書館"], int)


def test_base_point_on_top_of_a_library_is_exactly_zero(client, libraries):
    """★ 基準点が図書館の座標と一致したとき、500 にならず距離が 0 になること。

    当初の余弦定理（`acos`）版はここで 2 つ壊れていた（`geo.py` に実測を記録）:

    - 誤差で cos が 1 を超え、Postgres の acos が `input is out of range` = 500
    - acos は 1 の近くで精度が落ち、**同一点でも 0.1343m** が出る

    haversine + atan2 に変えて両方消えた。**現在地の真上にある館は現実に起こる。**
    """
    res = client.get(NEARBY_URL, TOKYO_STATION)

    assert res.status_code == 200
    assert res.json()["results"][0]["distance_m"] == 0


def test_zero_distance_has_no_rounding_floor(client, libraries):
    """全件を自分自身の座標で引いて、距離 0 が 0 と出ること。

    余弦定理版だと 0.1343m の下駄を履くので、丸める前に潰れていた不具合を
    ここで捕まえる（`distance_m` は整数に丸めて返るため、
    上のテストだけでは 0.1343m でも通ってしまう）。
    """
    for library in libraries:
        res = client.get(NEARBY_URL, {"lat": str(library.latitude), "lng": str(library.longitude)})

        assert res.status_code == 200
        nearest = res.json()["results"][0]
        assert nearest["name"] == library.name
        assert nearest["distance_m"] == 0


# --- radius で絞る --------------------------------------------------------


def test_radius_excludes_the_far_ones(client, libraries):
    """既定の 3km だと新宿（約 5.5km）は入らない。"""
    assert names(client.get(NEARBY_URL, TOKYO_STATION)) == ["東京駅前図書館", "丸の内図書館"]


def test_izu_islands_are_out_of_range(client, libraries):
    """青ヶ島は東京駅から約 360km。上限 20km では絶対に入らない。"""
    res = client.get(NEARBY_URL, {**TOKYO_STATION, "radius_m": 20000})

    assert "青ヶ島図書館" not in names(res)


def test_radius_is_capped_not_rejected(client, libraries):
    """上限超えは 400 にせず 20km で頭打ちにする（一覧の limit と同じ方針）。"""
    res = client.get(NEARBY_URL, {**TOKYO_STATION, "radius_m": 999999})

    assert res.status_code == 200
    # 頭打ちが効いていれば八王子（約 39km）は入らない
    assert "八王子図書館" not in names(res)


# --- 他のパラメータとの組み合わせ -----------------------------------------


def test_smoking_filter_applies(client, libraries):
    res = client.get(
        NEARBY_URL, {**TOKYO_STATION, "radius_m": 20000, "smoking": SmokingStatus.BOTH}
    )

    assert names(res) == ["丸の内図書館"]


def test_limit_applies(client, libraries):
    res = client.get(NEARBY_URL, {**TOKYO_STATION, "radius_m": 20000, "limit": 1})

    assert names(res) == ["東京駅前図書館"]


def test_returns_list_fields_plus_distance(client, libraries):
    row = client.get(NEARBY_URL, TOKYO_STATION).json()["results"][0]

    assert set(row) == {
        "id",
        "name",
        "ward",
        "latitude",
        "longitude",
        "smoking_status",
        "smoking_status_label",
        "distance_m",
    }


def test_empty_when_nothing_is_near(client, libraries):
    """海の上を基準点にする。"""
    res = client.get(NEARBY_URL, {"lat": "34.0", "lng": "141.0"})

    assert res.json() == {"count": 0, "results": []}


# --- bounding_box 単体 ----------------------------------------------------


def test_bounding_box_contains_the_circle():
    """外接矩形なので、半径ぶん離れた真北・真東の点を必ず含む。"""
    lat, lng, radius = 35.681236, 139.767125, 3000
    box = bounding_box(lat, lng, radius)

    north = lat + math.degrees(radius / 6_371_008.8)
    assert box["min_lat"] < lat < box["max_lat"]
    assert box["max_lat"] >= north
    assert box["min_lng"] < lng < box["max_lng"]


def test_bounding_box_omits_longitude_when_it_would_wrap():
    """日付変更線をまたぐ範囲は BETWEEN で表せないので経度を返さない。

    緯度だけで絞って、あとの正確な距離計算に任せる（結果は変わらない）。
    """
    box = bounding_box(0.0, 179.99, 20000)

    assert "min_lng" not in box
    assert "max_lng" not in box


def test_bounding_box_does_not_divide_by_zero_at_the_pole():
    box = bounding_box(90.0, 0.0, 3000)

    assert box["max_lat"] == 90.0
