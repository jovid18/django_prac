"""お気に入り（docs/05-api.md「図書館系」）。

観点は 3 つ。

1. **書き込みだけログインを要求する。** 閲覧は未ログインで通ること（test_library_api.py）
   と対になっている。
2. **POST / DELETE が冪等。** 連打や再送で状態が壊れない。
3. **他人のお気に入りが混ざらない。** 一覧のフィルタが user で効いていること。
"""

import pytest

from apps.libraries.models import Favorite

pytestmark = pytest.mark.django_db

FAVORITES_URL = "/api/favorites/"


def favorite_url(library_id: int) -> str:
    return f"/api/libraries/{library_id}/favorite/"


def names(res):
    return [r["name"] for r in res.json()["results"]]


# --- 認証 -----------------------------------------------------------------


def test_favorite_requires_login(client, libraries):
    res = client.post(favorite_url(libraries[0].id))

    assert res.status_code == 401


def test_unfavorite_requires_login(client, libraries):
    assert client.delete(favorite_url(libraries[0].id)).status_code == 401


def test_favorites_list_requires_login(client):
    assert client.get(FAVORITES_URL).status_code == 401


def test_login_is_required_even_for_a_missing_library(client, libraries):
    """権限チェックが先。存在しない id でも 404 ではなく 401。

    逆にすると「どの id が存在するか」を未ログインで総当たりできる。
    """
    assert client.post(favorite_url(999999)).status_code == 401


# --- 登録 -----------------------------------------------------------------


def test_favorite_creates_the_row(client, libraries, user, bearer):
    target = libraries[0]

    res = client.post(favorite_url(target.id), **bearer(user))

    assert res.status_code == 201
    assert res.json() == {"is_favorited": True}
    assert Favorite.objects.filter(user=user, library=target).exists()


def test_favorite_twice_is_idempotent(client, libraries, user, bearer):
    """二重 POST でも 201 のまま、行は 1 つ。

    409 を返す設計にすると、フロントが押す前に「登録済みか」を
    問い合わせる作りになる（docs/05-api.md）。
    """
    target = libraries[0]

    first = client.post(favorite_url(target.id), **bearer(user))
    second = client.post(favorite_url(target.id), **bearer(user))

    assert (first.status_code, second.status_code) == (201, 201)
    assert Favorite.objects.filter(user=user, library=target).count() == 1


def test_favorite_404_for_missing_library(client, libraries, user, bearer):
    assert client.post(favorite_url(999999), **bearer(user)).status_code == 404


# --- 解除 -----------------------------------------------------------------


def test_unfavorite_removes_the_row(client, libraries, user, bearer):
    target = libraries[0]
    Favorite.objects.create(user=user, library=target)

    res = client.delete(favorite_url(target.id), **bearer(user))

    assert res.status_code == 204
    assert not Favorite.objects.filter(user=user, library=target).exists()


def test_unfavorite_when_not_registered_is_still_204(client, libraries, user, bearer):
    assert client.delete(favorite_url(libraries[0].id), **bearer(user)).status_code == 204


def test_unfavorite_does_not_touch_other_users(client, libraries, user, other_user, bearer):
    target = libraries[0]
    Favorite.objects.create(user=other_user, library=target)

    client.delete(favorite_url(target.id), **bearer(user))

    assert Favorite.objects.filter(user=other_user, library=target).exists()


# --- 詳細の is_favorited --------------------------------------------------


def test_detail_reflects_is_favorited_for_the_owner(client, libraries, user, bearer):
    target = libraries[0]
    Favorite.objects.create(user=user, library=target)

    body = client.get(f"/api/libraries/{target.id}/", **bearer(user)).json()

    assert body["is_favorited"] is True


def test_detail_is_favorited_is_false_for_another_user(client, libraries, user, other_user, bearer):
    target = libraries[0]
    Favorite.objects.create(user=other_user, library=target)

    body = client.get(f"/api/libraries/{target.id}/", **bearer(user)).json()

    assert body["is_favorited"] is False


# --- 一覧 -----------------------------------------------------------------


def test_favorites_list_returns_only_my_rows(client, libraries, user, other_user, bearer):
    Favorite.objects.create(user=user, library=libraries[0])
    Favorite.objects.create(user=other_user, library=libraries[1])

    res = client.get(FAVORITES_URL, **bearer(user))

    assert res.json()["count"] == 1
    assert names(res) == [libraries[0].name]


def test_favorites_list_is_newest_first(client, libraries, user, bearer):
    for library in libraries[:3]:
        Favorite.objects.create(user=user, library=library)

    res = client.get(FAVORITES_URL, **bearer(user))

    assert names(res) == [libraries[2].name, libraries[1].name, libraries[0].name]


def test_favorites_list_includes_address_and_favorited_at(client, libraries, user, bearer):
    """この画面には地図が無いので、名前だけでは場所が分からない。

    地図の一覧（`/api/libraries/`）では逆に address を返さない。
    """
    target = libraries[0]
    Favorite.objects.create(user=user, library=target)

    row = client.get(FAVORITES_URL, **bearer(user)).json()["results"][0]

    assert row["address"] == target.address
    assert row["favorited_at"]
    # 地図の一覧と同じキーで来ること（フロントが同じ型で扱えるようにしてある）
    assert {"id", "name", "ward", "latitude", "longitude", "smoking_status"} <= set(row)


def test_favorites_list_is_empty_for_a_new_user(client, libraries, user, bearer):
    res = client.get(FAVORITES_URL, **bearer(user))

    assert res.json() == {"count": 0, "results": []}
