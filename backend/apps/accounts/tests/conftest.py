import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """スロットリングの記録をテストごとに捨てる。

    DRF の throttle はカウントを **cache** に持つ。cache はテスト間で共有される
    ので、これが無いと「login を何度も叩くテストのせいで後続のテストが 429」に
    なる。落ち方がテストの実行順に依存するので原因が非常に分かりにくい。
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def credentials():
    return {"email": "taro@example.com", "password": "correct-horse-battery"}


@pytest.fixture
def user(django_user_model, credentials):
    return django_user_model.objects.create_user(**credentials)


@pytest.fixture
def google_client_id(settings):
    """テストが環境変数（.env / CI）の値に依存しないよう固定する。"""
    settings.GOOGLE_OAUTH_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    return settings.GOOGLE_OAUTH_CLIENT_ID


@pytest.fixture
def google_payload():
    """`verify_oauth2_token` が返すペイロードの最小形。"""
    return {
        "iss": "https://accounts.google.com",
        "sub": "google-sub-1",
        "aud": "test-client-id.apps.googleusercontent.com",
        "email": "taro@example.com",
        "email_verified": True,
        "name": "たろう",
    }
