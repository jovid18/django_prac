from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """疎通確認。

    Render のヘルスチェックがここを叩いて起動完了を判定するため、
    **DB に触らない軽い処理だけ**にしておく（docs/08-deploy-render.md）。
    """
    return Response({"status": "ok", "debug": settings.DEBUG})
