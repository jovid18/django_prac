"""認証エンドポイントのテスト（docs/05-api.md「テストの最低ライン」）。

⚠ Django のテストクライアントは Cookie の `Path` を無視して全部送る。
  つまり `Path=/api/auth` が効いているかはここでは検証できない。
  そこはブラウザで確認する（docs/06-auth.md）。
"""

import pytest
from django.conf import settings

from apps.accounts.models import SocialAccount

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
GOOGLE_URL = "/api/auth/google/"
REFRESH_URL = "/api/auth/refresh/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"

COOKIE = settings.REFRESH_COOKIE_NAME


def post_json(client, url, payload=None):
    return client.post(url, payload or {}, content_type="application/json")


def bearer(access: str) -> dict:
    return {"headers": {"authorization": f"Bearer {access}"}}


# --- register -------------------------------------------------------------


def test_register_returns_user_and_access_and_sets_cookie(client, credentials):
    res = post_json(client, REGISTER_URL, {**credentials, "display_name": "たろう"})

    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == credentials["email"]
    assert body["user"]["display_name"] == "たろう"
    assert body["user"]["has_password"] is True
    assert body["user"]["providers"] == []
    assert body["access"]

    # ★ refresh は本文に入れない。Cookie だけに載せる。
    assert "refresh" not in body
    assert COOKIE in res.cookies


def test_refresh_cookie_is_httponly_and_scoped_to_auth_path(client, credentials):
    cookie = post_json(client, REGISTER_URL, credentials).cookies[COOKIE]

    # JS から読めないこと。ここが False だと XSS で 14 日間なりすませる。
    assert cookie["httponly"] is True
    assert cookie["path"] == "/api/auth"
    # ローカル設定（HTTP）なので Lax。本番は None + Secure（production.py）。
    assert cookie["samesite"] == "Lax"
    assert cookie["secure"] == ""


def test_register_rejects_duplicate_email(client, user, credentials):
    res = post_json(client, REGISTER_URL, credentials)

    assert res.status_code == 400
    assert "email" in res.json()


def test_register_rejects_duplicate_email_differing_only_in_case(client, user):
    res = post_json(
        client, REGISTER_URL, {"email": "TARO@example.com", "password": "another-long-password"}
    )

    # unique 制約は大文字小文字を区別するので、DB より前に弾いている。
    # ここが 500（IntegrityError）になっていたら serializers.py の iexact を疑う。
    assert res.status_code == 400
    assert "email" in res.json()


@pytest.mark.parametrize(
    "password",
    [
        "short",  # MinimumLengthValidator
        "password",  # CommonPasswordValidator
        "83719204",  # NumericPasswordValidator
        "taro@example.com",  # UserAttributeSimilarityValidator
    ],
)
def test_register_rejects_weak_password(client, password):
    res = post_json(client, REGISTER_URL, {"email": "taro@example.com", "password": password})

    assert res.status_code == 400
    assert "password" in res.json()


# --- login ----------------------------------------------------------------


def test_login_succeeds(client, user, credentials):
    res = post_json(client, LOGIN_URL, credentials)

    assert res.status_code == 200
    assert res.json()["user"]["id"] == user.id
    assert COOKIE in res.cookies


def test_login_updates_last_login(client, user, credentials):
    assert user.last_login is None

    post_json(client, LOGIN_URL, credentials)

    user.refresh_from_db()
    # SIMPLE_JWT の UPDATE_LAST_LOGIN は SimpleJWT 自身のシリアライザにしか
    # 効かない。views.auth_response で自分で更新している（views.py のコメント）。
    assert user.last_login is not None


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "taro@example.com", "password": "wrong-password-here"},
        {"email": "nobody@example.com", "password": "correct-horse-battery"},
    ],
)
def test_login_failure_does_not_reveal_which_field_was_wrong(client, user, payload):
    res = post_json(client, LOGIN_URL, payload)

    assert res.status_code == 401
    # ★ 「そのメールは登録済み」を漏らさない。2 ケースで同一の文言。
    assert res.json()["detail"] == "メールアドレスまたはパスワードが正しくありません。"
    assert COOKIE not in res.cookies


def test_login_of_inactive_user_is_rejected(client, user, credentials):
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert post_json(client, LOGIN_URL, credentials).status_code == 401


def test_login_is_throttled(client, user, credentials):
    wrong = {**credentials, "password": "wrong-password-here"}

    # DEFAULT_THROTTLE_RATES["login"] = 5/min。成否に関係なく回数を数える。
    statuses = [post_json(client, LOGIN_URL, wrong).status_code for _ in range(6)]

    assert statuses == [401, 401, 401, 401, 401, 429]


# --- refresh --------------------------------------------------------------


def test_refresh_without_cookie_is_401(client):
    res = post_json(client, REFRESH_URL)

    assert res.status_code == 401
    # 未ログインの初回アクセスもここに来る。フロントは 401 を
    # 「まだログインしていない」と解釈する。
    assert "access" not in res.json()


def test_refresh_with_cookie_returns_new_access(client, user, credentials):
    post_json(client, LOGIN_URL, credentials)  # Cookie がテストクライアントに残る

    res = post_json(client, REFRESH_URL)

    assert res.status_code == 200
    assert res.json()["access"]


def test_refresh_can_be_called_twice_because_the_cookie_is_rotated(client, user, credentials):
    """★ ローテーションした新しい refresh を Cookie に書き戻せているか。

    書き戻しを忘れると 1 回目は通って 2 回目が 401 になる。
    「しばらく使えるのに 15 分後に落ちる」という形で出るので気づきにくい。
    """
    post_json(client, LOGIN_URL, credentials)
    first = client.cookies[COOKIE].value

    assert post_json(client, REFRESH_URL).status_code == 200
    assert client.cookies[COOKIE].value != first
    assert post_json(client, REFRESH_URL).status_code == 200


def test_reusing_a_rotated_refresh_token_is_rejected(client, user, credentials):
    """BLACKLIST_AFTER_ROTATION。盗まれた古いトークンが使い回せないこと。"""
    post_json(client, LOGIN_URL, credentials)
    stolen = client.cookies[COOKIE].value

    post_json(client, REFRESH_URL)  # ローテーション → 古い方は失効

    client.cookies[COOKIE] = stolen
    res = post_json(client, REFRESH_URL)

    assert res.status_code == 401
    # 使えない Cookie は消す。残すと毎回同じ 401 を踏み続ける。
    assert res.cookies[COOKIE].value == ""


def test_refresh_with_garbage_cookie_is_401(client):
    client.cookies[COOKIE] = "not-a-jwt"

    assert post_json(client, REFRESH_URL).status_code == 401


# --- logout ---------------------------------------------------------------


def test_logout_requires_authentication(client):
    assert post_json(client, LOGOUT_URL).status_code == 401


def test_logout_clears_cookie_and_invalidates_refresh(client, user, credentials):
    access = post_json(client, LOGIN_URL, credentials).json()["access"]

    res = client.post(LOGOUT_URL, **bearer(access))

    assert res.status_code == 204
    assert res.cookies[COOKIE].value == ""
    # Cookie を消しただけでは不十分（既に盗まれていたら使える）。
    # ブラックリストに入っていることまで確認する。
    assert post_json(client, REFRESH_URL).status_code == 401


def test_logout_twice_is_idempotent(client, user, credentials):
    access = post_json(client, LOGIN_URL, credentials).json()["access"]

    assert client.post(LOGOUT_URL, **bearer(access)).status_code == 204
    assert client.post(LOGOUT_URL, **bearer(access)).status_code == 204


# --- me -------------------------------------------------------------------


def test_me_requires_authentication(client):
    assert client.get(ME_URL).status_code == 401


def test_me_returns_the_current_user(client, user, credentials):
    access = post_json(client, LOGIN_URL, credentials).json()["access"]

    res = client.get(ME_URL, **bearer(access))

    assert res.status_code == 200
    assert set(res.json()) == {
        "id",
        "email",
        "display_name",
        "has_password",
        "providers",
        "date_joined",
    }
    assert res.json()["email"] == credentials["email"]


def test_me_rejects_a_garbage_token(client):
    assert client.get(ME_URL, **bearer("not-a-jwt")).status_code == 401


# --- google ---------------------------------------------------------------


@pytest.fixture
def verified_google(monkeypatch, google_client_id, google_payload):
    """`verify_oauth2_token` を差し替えて、Google に通信しないようにする。

    署名検証そのものは google-auth の責務なので、ここでは
    「検証を通った後の分岐」をテストする。
    """

    def fake_verify(raw_token, request, audience):
        assert audience == google_client_id, "aud のチェックに client_id を渡していない"
        return google_payload

    monkeypatch.setattr(
        "apps.accounts.google.google_id_token.verify_oauth2_token", fake_verify, raising=True
    )
    return google_payload


def test_google_login_creates_a_new_user(client, verified_google, django_user_model):
    res = post_json(client, GOOGLE_URL, {"id_token": "dummy"})

    assert res.status_code == 201
    body = res.json()
    assert body["created"] is True
    assert body["user"]["email"] == "taro@example.com"
    assert body["user"]["display_name"] == "たろう"
    # ソーシャルのみのユーザーはパスワードを持たない。
    assert body["user"]["has_password"] is False
    assert body["user"]["providers"] == ["google"]
    assert COOKIE in res.cookies

    user = django_user_model.objects.get(email="taro@example.com")
    assert user.social_accounts.get().provider_uid == "google-sub-1"


def test_second_google_login_reuses_the_same_user(client, verified_google, django_user_model):
    post_json(client, GOOGLE_URL, {"id_token": "dummy"})
    res = post_json(client, GOOGLE_URL, {"id_token": "dummy"})

    assert res.status_code == 200
    assert res.json()["created"] is False
    assert django_user_model.objects.count() == 1
    assert SocialAccount.objects.count() == 1


def test_google_login_links_to_an_existing_password_user(client, verified_google, user):
    """同じメールの ID/PW ユーザーがいたら紐付ける（別アカウントを生やさない）。

    これが安全なのは `email_verified: true` を確認しているから
    （docs/06-auth.md）。未確認メールで同じことをすると乗っ取りになる。
    """
    res = post_json(client, GOOGLE_URL, {"id_token": "dummy"})

    assert res.status_code == 200
    assert res.json()["created"] is False
    assert res.json()["user"]["id"] == user.id
    # ID/PW と Google を 1 ユーザーが併せ持てる。
    assert res.json()["user"]["has_password"] is True
    assert res.json()["user"]["providers"] == ["google"]


def test_google_login_keeps_the_user_when_the_email_changed_on_googles_side(
    client, monkeypatch, google_client_id, google_payload, django_user_model
):
    """★ 突き合わせのキーは sub。メールが変わっても同じユーザーであること。

    email で突き合わせる実装だと、ここで別アカウントが生えてしまう。
    """
    payload = dict(google_payload)

    monkeypatch.setattr(
        "apps.accounts.google.google_id_token.verify_oauth2_token",
        lambda *_args, **_kw: payload,
    )
    post_json(client, GOOGLE_URL, {"id_token": "dummy"})

    payload["email"] = "taro-new@example.com"
    res = post_json(client, GOOGLE_URL, {"id_token": "dummy"})

    assert res.status_code == 200
    assert res.json()["created"] is False
    assert django_user_model.objects.count() == 1


@pytest.mark.parametrize(
    "override",
    [
        {"email_verified": False},
        {"iss": "evil.example.com"},
        {"email": ""},
    ],
)
def test_google_login_rejects_a_payload_that_fails_our_own_checks(
    client, monkeypatch, google_client_id, google_payload, override
):
    monkeypatch.setattr(
        "apps.accounts.google.google_id_token.verify_oauth2_token",
        lambda *_args, **_kw: {**google_payload, **override},
    )

    assert post_json(client, GOOGLE_URL, {"id_token": "dummy"}).status_code == 401


def test_google_login_rejects_a_token_google_refuses(client, monkeypatch, google_client_id):
    def raise_value_error(*_args, **_kw):
        # 署名不正・期限切れ・aud 不一致はすべて ValueError で来る。
        raise ValueError("Token expired")

    monkeypatch.setattr(
        "apps.accounts.google.google_id_token.verify_oauth2_token", raise_value_error
    )

    assert post_json(client, GOOGLE_URL, {"id_token": "dummy"}).status_code == 401


def test_google_login_is_unavailable_when_the_client_id_is_not_configured(client, settings):
    """★ client_id が空なら検証せず 503。

    空文字を渡して verify を通すと aud のチェックが無効化され、
    **他のアプリ向けに発行された ID トークン**を受け入れてしまう。
    """
    settings.GOOGLE_OAUTH_CLIENT_ID = ""

    assert post_json(client, GOOGLE_URL, {"id_token": "dummy"}).status_code == 503


def test_google_login_requires_the_id_token_field(client, google_client_id):
    res = post_json(client, GOOGLE_URL, {})

    assert res.status_code == 400
    assert "id_token" in res.json()
