"""リフレッシュトークンを載せる Cookie の読み書き。

`secure` / `samesite` は環境ごとに違う（local.py / production.py）。
**ここ 1 箇所でだけ Cookie を触る。** ビューに散らすと、set と delete で
属性が食い違って「消えたつもりの Cookie が残る」事故になる。
"""

from django.conf import settings
from rest_framework.response import Response


def _cookie_kwargs() -> dict:
    return {
        "path": settings.REFRESH_COOKIE_PATH,
        "samesite": settings.REFRESH_COOKIE_SAMESITE,
    }


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        # トークン自体の寿命と Cookie の寿命を揃える。
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        # JS から読めない = XSS で持ち出せない（docs/06-auth.md）。
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        **_cookie_kwargs(),
    )


def delete_refresh_cookie(response: Response) -> None:
    # ★ path と samesite を set 時と揃えること。理由が 2 つある。
    #   1. 違う path で delete すると、ブラウザは別の Cookie と見なして消さない。
    #   2. samesite を渡さないと削除用の Set-Cookie に Secure が付かない。
    #      `SameSite=None` かつ Secure 無しの Cookie はブラウザに捨てられるので、
    #      本番だけ「ログアウトしたのに Cookie が残る」ことになる。
    #      Django の delete_cookie は samesite="None" を受け取ったときだけ
    #      secure=True を自動で足す実装になっている。
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, **_cookie_kwargs())


def read_refresh_cookie(request) -> str | None:
    return request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
