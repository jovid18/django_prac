import pytest

from apps.libraries.models import Library, SmokingStatus

pytestmark = pytest.mark.django_db

LIST_URL = "/api/libraries/"


def names(res):
    return {r["name"] for r in res.json()["results"]}


# --- 一覧の基本 -----------------------------------------------------------


def test_list_requires_no_login(client, libraries):
    """閲覧はログイン不要。地図を開いた瞬間にログインを求めない。"""
    res = client.get(LIST_URL)

    assert res.status_code == 200
    assert res.json()["count"] == len(libraries)


def test_list_returns_only_fields_needed_for_markers(client, libraries):
    """一覧では住所や website を返さない（数百件を地図に載せるため）。"""
    row = client.get(LIST_URL).json()["results"][0]

    assert set(row) == {
        "id",
        "name",
        "ward",
        "latitude",
        "longitude",
        "smoking_status",
        "smoking_status_label",
    }


def test_label_is_returned_so_frontend_need_not_duplicate_it(client, libraries):
    res = client.get(LIST_URL, {"smoking": SmokingStatus.HEATED_ONLY})

    assert res.json()["results"][0]["smoking_status_label"] == "加熱式のみ可"


# --- bbox -----------------------------------------------------------------


def test_bbox_narrows_to_the_visible_area(client, libraries, tokyo_center_bbox):
    res = client.get(LIST_URL, {"bbox": tokyo_center_bbox})

    assert names(res) == {"東京駅前図書館", "丸の内図書館", "新宿中央図書館"}


def test_bbox_excludes_izu_islands(client, libraries, tokyo_center_bbox):
    """東京都は伊豆諸島まで含む。都心の bbox では落ちること。"""
    assert "青ヶ島図書館" not in names(client.get(LIST_URL, {"bbox": tokyo_center_bbox}))


@pytest.mark.parametrize(
    "bad,reason",
    [
        ("139.70,35.66,139.80", "4 つでない"),
        ("a,b,c,d", "数値でない"),
        ("139.80,35.66,139.70,35.70", "min_lng > max_lng"),
        ("139.70,35.70,139.80,35.66", "min_lat > max_lat"),
        ("139.70,-95,139.80,35.70", "緯度が範囲外"),
        ("-200,35.66,139.80,35.70", "経度が範囲外"),
    ],
)
def test_invalid_bbox_is_rejected(client, libraries, bad, reason):
    """不正な bbox を握りつぶして全件返さない。

    黙って全件返すと、フロントの不具合が「なぜか全部出る」という形でしか
    現れなくなる。
    """
    res = client.get(LIST_URL, {"bbox": bad})

    assert res.status_code == 400, reason
    assert "bbox" in res.json()


# --- フィルタ -------------------------------------------------------------


def test_smoking_filter_single(client, libraries):
    res = client.get(LIST_URL, {"smoking": SmokingStatus.BOTH})

    assert names(res) == {"丸の内図書館", "青ヶ島図書館"}


def test_smoking_filter_accepts_multiple(client, libraries):
    res = client.get(LIST_URL, {"smoking": f"{SmokingStatus.BOTH},{SmokingStatus.CIGARETTE_ONLY}"})

    assert names(res) == {"丸の内図書館", "青ヶ島図書館", "八王子図書館"}


def test_unknown_smoking_value_is_rejected(client, libraries):
    res = client.get(LIST_URL, {"smoking": "vape"})

    assert res.status_code == 400
    assert "smoking" in res.json()


def test_ward_filter(client, libraries):
    res = client.get(LIST_URL, {"ward": "千代田区"})

    assert names(res) == {"東京駅前図書館", "丸の内図書館"}


def test_text_search_matches_name(client, libraries):
    res = client.get(LIST_URL, {"q": "新宿"})

    assert names(res) == {"新宿中央図書館"}


def test_filters_combine(client, libraries, tokyo_center_bbox):
    res = client.get(LIST_URL, {"bbox": tokyo_center_bbox, "smoking": SmokingStatus.BOTH})

    assert names(res) == {"丸の内図書館"}


# --- limit と truncated ---------------------------------------------------


def test_truncated_is_false_when_everything_fits(client, libraries):
    assert client.get(LIST_URL).json()["truncated"] is False


def test_truncated_is_true_when_cut_off(client, libraries):
    """打ち切りを黙って行わない。

    黙って切ると「ズームアウトすると一部のピンが消える」という
    説明のつかない挙動になる。
    """
    body = client.get(LIST_URL, {"limit": 2}).json()

    assert body["count"] == 2
    assert body["truncated"] is True


def test_limit_is_capped(client, libraries):
    """上限を超える limit を指定しても 500 で頭打ちにする。"""
    res = client.get(LIST_URL, {"limit": 100000})

    assert res.status_code == 200


@pytest.mark.parametrize("bad", ["0", "-1", "abc"])
def test_invalid_limit_is_rejected(client, libraries, bad):
    res = client.get(LIST_URL, {"limit": bad})

    assert res.status_code == 400


# --- 詳細 -----------------------------------------------------------------


def test_detail_returns_full_record(client, libraries):
    target = libraries[0]

    body = client.get(f"{LIST_URL}{target.id}/").json()

    assert body["name"] == target.name
    assert body["address"] == target.address
    assert body["smoking_status_label"] == "喫煙不可"
    assert body["is_favorited"] is False


def test_detail_404_for_missing_id(client, libraries):
    assert client.get(f"{LIST_URL}999999/").status_code == 404


def test_is_favorited_is_false_for_anonymous(client, libraries):
    """未ログインでも詳細は見られる。お気に入り状態は常に false。"""
    assert client.get(f"{LIST_URL}{libraries[0].id}/").json()["is_favorited"] is False


# --- モデル ---------------------------------------------------------------


def test_same_spot_cannot_be_registered_twice(libraries):
    """シード投入を 2 回叩いても重複しないための UNIQUE 制約。"""
    from django.db import IntegrityError

    original = libraries[0]

    with pytest.raises(IntegrityError):
        Library.objects.create(
            name=original.name,
            latitude=original.latitude,
            longitude=original.longitude,
            smoking_status=SmokingStatus.NONE,
        )
