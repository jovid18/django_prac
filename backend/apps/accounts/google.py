"""Google の ID トークン検証とアカウント紐付け。

`django-allauth` を入れずに `google-auth` で数十行書く判断の理由は
docs/06-auth.md。ここで何を検証しているかが読めることを優先している。
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import status
from rest_framework.exceptions import APIException

from .exceptions import Unauthorized
from .models import SocialAccount

User = get_user_model()

# iss はこの 2 通りのどちらか。どちらも正しい（Google の仕様）。
VALID_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


class GoogleLoginUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Google ログインは設定されていません。"


def verify_id_token(raw_token: str) -> dict:
    """ID トークンを検証してペイロードを返す。

    確認するのは 4 点（docs/06-auth.md の表）:
    署名 / `aud` / `iss` / `exp`。前者 3 つのうち署名・`aud`・`exp` は
    `verify_oauth2_token` がまとめて見てくれる。`iss` と `email_verified` は自分で足す。
    """
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        # ★ client_id が空のまま検証を通してはいけない。
        #   aud のチェックが無効になり、**他のアプリ向けに発行された
        #   ID トークン**をそのまま受け入れてしまう。
        raise GoogleLoginUnavailable

    try:
        info = google_id_token.verify_oauth2_token(
            raw_token,
            google_requests.Request(),
            client_id,  # ← aud のチェック。ここを渡さないと意味がない
        )
    except (GoogleAuthError, ValueError) as exc:
        # 署名不正・期限切れ・aud 不一致はすべてここに来る。
        # 理由を細かく返さない（攻撃者に検証内容を教えないため）。
        raise Unauthorized("Google の ID トークンを検証できませんでした。") from exc

    if info.get("iss") not in VALID_ISSUERS:
        raise Unauthorized("ID トークンの発行元が不正です。")
    if not info.get("email"):
        raise Unauthorized("ID トークンにメールアドレスが含まれていません。")
    if not info.get("email_verified"):
        # ★ この確認は下の「同じメールなら自動で紐付ける」を成立させる前提。
        #   未確認メールで紐付けると他人のアカウントを乗っ取れる。
        raise Unauthorized("Google 側でメールアドレスが確認されていません。")

    return info


@transaction.atomic
def get_or_create_user(info: dict) -> tuple[User, bool]:
    """ID トークンのペイロードからユーザーを特定、無ければ作る。

    戻り値の 2 番目は「新規作成したか」。レスポンスの `created` に使う。

    ★ 突き合わせのキーは `sub`。`email` は補助。
      Google のメールアドレスは変更されうるが `sub` は不変なので、
      email だけで突き合わせるとユーザーがメールを変えた瞬間に別アカウントが生える。
    """
    provider = SocialAccount.Provider.GOOGLE
    sub = info["sub"]
    email = User.objects.normalize_email(info["email"])

    social = (
        SocialAccount.objects.filter(provider=provider, provider_uid=sub)
        .select_related("user")
        .first()
    )
    if social:
        return social.user, False

    # ID/PW で登録済みのユーザーが Google で入ってきたケース。
    # email_verified を確認済みなので「同じメール = 同一人物」と見なして紐付ける。
    user = User.objects.filter(email__iexact=email).first()
    created = user is None
    if created:
        user = User.objects.create_user(
            email=email,
            # password は渡さない = set_unusable_password（models.py の UserManager）
            display_name=(info.get("name") or "")[:50],
        )

    SocialAccount.objects.create(user=user, provider=provider, provider_uid=sub)
    return user, created
