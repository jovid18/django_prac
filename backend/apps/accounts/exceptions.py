from rest_framework import status
from rest_framework.exceptions import APIException


class Unauthorized(APIException):
    """401 を返す例外。

    ★ DRF の `AuthenticationFailed` は使えない。
      `authentication_classes = []` のビューで投げると、DRF が
      **403 に書き換える**（`WWW-Authenticate` ヘッダを組み立てられないため。
      実体は `APIView.handle_exception`）。

      ログイン系のビューは「期限切れの Authorization ヘッダに邪魔されない」よう
      意図して認証を外してあるので、401 を返したいならこちらを使う。
      docs/05-api.md のステータス表と実装を一致させるための都合。
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "認証に失敗しました。"
    default_code = "authentication_failed"
