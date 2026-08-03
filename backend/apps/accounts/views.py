"""認証エンドポイント（docs/05-api.md / docs/06-auth.md）。

方針の要約:

- **アクセストークンはレスポンス本文**（フロントはメモリに置く）。
- **リフレッシュトークンは HttpOnly Cookie**。本文には一切入れない。
- SimpleJWT の標準ビューは refresh を本文でやり取りする前提なので、
  **Cookie から読んで Cookie に書き戻すビューを自分で書く**（`RefreshView`）。
"""

from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from . import google
from .cookies import delete_refresh_cookie, read_refresh_cookie, set_refresh_cookie
from .serializers import (
    GoogleLoginSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


def auth_response(user, *, status_code: int = status.HTTP_200_OK, **extra) -> Response:
    """ログイン成功時の共通レスポンス。

    本文に access、Set-Cookie に refresh を載せる。
    register / login / google の 3 つで形を揃える。
    """
    refresh = RefreshToken.for_user(user)

    # ★ SIMPLE_JWT の UPDATE_LAST_LOGIN は SimpleJWT 自身のシリアライザ
    #   （TokenObtainPairSerializer）にしか効かない。`RefreshToken.for_user` を
    #   直接呼ぶ本実装では発火しないので、自分で更新する。
    update_last_login(None, user)

    response = Response(
        {"user": UserSerializer(user).data, "access": str(refresh.access_token), **extra},
        status=status_code,
    )
    set_refresh_cookie(response, str(refresh))
    return response


class RegisterView(APIView):
    """`POST /api/auth/register/` — メール + パスワードで登録して、そのままログイン状態にする。"""

    permission_classes = [AllowAny]
    authentication_classes = []
    # 登録も総当たりの対象になるので login と同じ枠で絞る。
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return auth_response(user, status_code=status.HTTP_201_CREATED)


class LoginView(APIView):
    """`POST /api/auth/login/`"""

    permission_classes = [AllowAny]
    authentication_classes = []
    # DEFAULT_THROTTLE_RATES の "login"（5/min）を使う。
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return auth_response(serializer.validated_data["user"])


class GoogleLoginView(APIView):
    """`POST /api/auth/google/` — Google の ID トークンを検証してログイン / 登録。"""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        info = google.verify_id_token(serializer.validated_data["id_token"])
        user, created = google.get_or_create_user(info)

        return auth_response(
            user,
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            created=created,
        )


class RefreshView(APIView):
    """`POST /api/auth/refresh/` — Cookie の refresh からアクセストークンを再発行する。

    本文は空。フロントは `credentials: "include"` を付けるだけ。
    """

    permission_classes = [AllowAny]
    # access が期限切れでも通したいので、認証は一切通さない。
    authentication_classes = []

    def post(self, request):
        raw = read_refresh_cookie(request)
        if not raw:
            # 未ログインの初回アクセスもここに来る。フロントは 401 を
            # 「まだログインしていない」と解釈して普通に地図を出す。
            return self._unauthenticated("リフレッシュトークンがありません。")

        try:
            refresh = RefreshToken(raw)
        except TokenError:
            # 期限切れ / 改竄 / ローテーション済み（ブラックリスト）。
            # 使えない Cookie を残すと毎回同じ 401 を踏むので消す。
            return self._unauthenticated("リフレッシュトークンが無効です。")

        # ★ アクセストークンはローテーション前の refresh から作る（SimpleJWT の
        #   TokenRefreshSerializer と同じ順序）。逆にすると jti の対応が崩れる。
        data = {"access": str(refresh.access_token)}

        response = Response(data)

        if jwt_settings.ROTATE_REFRESH_TOKENS:
            if jwt_settings.BLACKLIST_AFTER_ROTATION:
                refresh.blacklist()
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            # ★ ここで書き戻さないと 2 回目の refresh がブラックリストで 401 になる。
            #   ローテーションを有効にした以上、必ずセットで実装する。
            set_refresh_cookie(response, str(refresh))

        return response

    @staticmethod
    def _unauthenticated(detail: str) -> Response:
        response = Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)
        delete_refresh_cookie(response)
        return response


class LogoutView(APIView):
    """`POST /api/auth/logout/` — refresh をブラックリストに入れて Cookie を消す。"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw = read_refresh_cookie(request)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                # 既に失効済み。ログアウトは冪等でよいので 204 のまま返す。
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        delete_refresh_cookie(response)
        return response


class MeView(APIView):
    """`GET /api/auth/me/`"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
