from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Favorite, Library, SmokingStatus
from .serializers import (
    FavoriteListSerializer,
    LibraryDetailSerializer,
    LibraryListSerializer,
)

DEFAULT_LIMIT = 200
MAX_LIMIT = 500


def parse_bbox(raw: str) -> dict[str, float]:
    """ "min_lng,min_lat,max_lng,max_lat" を読む。

    順序は GeoJSON / MapLibre の慣習に合わせて経度が先。
    不正な値は握りつぶさず 400 にする。黙って全件返すと、
    フロントの不具合が「なぜか全部出る」という形でしか現れなくなる。
    """
    parts = raw.split(",")
    if len(parts) != 4:
        raise ValidationError(
            {"bbox": "min_lng,min_lat,max_lng,max_lat の 4 つを指定してください。"}
        )
    try:
        min_lng, min_lat, max_lng, max_lat = (float(p) for p in parts)
    except ValueError:
        raise ValidationError({"bbox": "数値で指定してください。"}) from None

    if min_lat > max_lat or min_lng > max_lng:
        raise ValidationError({"bbox": "min が max を上回っています。"})
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValidationError({"bbox": "緯度は -90〜90 の範囲で指定してください。"})
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
        raise ValidationError({"bbox": "経度は -180〜180 の範囲で指定してください。"})

    return {"min_lat": min_lat, "max_lat": max_lat, "min_lng": min_lng, "max_lng": max_lng}


def parse_smoking(raw: str) -> list[str]:
    values = [v.strip() for v in raw.split(",") if v.strip()]
    valid = set(SmokingStatus.values)
    unknown = [v for v in values if v not in valid]
    if unknown:
        allowed = ", ".join(sorted(valid))
        raise ValidationError(
            {"smoking": f"未知の値です: {', '.join(unknown)}。使えるのは {allowed}"}
        )
    return values


def parse_limit(raw: str) -> int:
    try:
        limit = int(raw)
    except ValueError:
        raise ValidationError({"limit": "整数で指定してください。"}) from None
    if limit < 1:
        raise ValidationError({"limit": "1 以上で指定してください。"})
    return min(limit, MAX_LIMIT)


class LibraryViewSet(viewsets.ReadOnlyModelViewSet):
    """図書館の一覧・詳細。

    **閲覧はログイン不要。** 地図を開いた瞬間にログインを求める設計にしない
    （docs/05-api.md）。
    """

    permission_classes = [AllowAny]
    queryset = Library.objects.all()

    def get_serializer_class(self):
        return LibraryListSerializer if self.action == "list" else LibraryDetailSerializer

    def list(self, request, *args, **kwargs):
        params = request.query_params
        qs = Library.objects.all()

        if bbox := params.get("bbox"):
            b = parse_bbox(bbox)
            qs = qs.filter(
                latitude__gte=b["min_lat"],
                latitude__lte=b["max_lat"],
                longitude__gte=b["min_lng"],
                longitude__lte=b["max_lng"],
            )

        if smoking := params.get("smoking"):
            qs = qs.filter(smoking_status__in=parse_smoking(smoking))

        if ward := params.get("ward"):
            qs = qs.filter(ward=ward)

        if q := params.get("q"):
            qs = qs.filter(name__icontains=q) | qs.filter(address__icontains=q)

        limit = parse_limit(params.get("limit", str(DEFAULT_LIMIT)))

        # limit + 1 件取って、打ち切られたかどうかを判定する。
        # 黙って切ると「ズームアウトすると一部のピンが消える」という
        # 説明のつかない挙動になる（docs/05-api.md）。
        rows = list(qs.order_by("id")[: limit + 1])
        truncated = len(rows) > limit
        rows = rows[:limit]

        return Response(
            {
                "count": len(rows),
                "truncated": truncated,
                "results": LibraryListSerializer(rows, many=True).data,
            }
        )

    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """`POST` / `DELETE /api/libraries/{id}/favorite/` — お気に入りの登録と解除。

        **どちらも冪等にする**（docs/05-api.md）。二重 POST に 409、未登録の
        DELETE に 404 を返すと、フロントが押す前に「登録済みか」を問い合わせる
        作りになる。ボタンを連打されても、オフラインから復帰して再送されても、
        結果の状態が同じであれば良い。

        ★ 閲覧は AllowAny だが、このアクションだけ `permission_classes` を
          上書きして認証を要求する。ViewSet 全体を IsAuthenticated にすると
          地図がログイン必須になってしまう。
        """
        library = self.get_object()

        if request.method == "DELETE":
            # 未登録でも 204。0 件の delete() はエラーにならない。
            Favorite.objects.filter(user=request.user, library=library).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # 同時に 2 回来ても UniqueConstraint で弾かれるだけ。
        # get_or_create は IntegrityError を拾って get に落ちる。
        Favorite.objects.get_or_create(user=request.user, library=library)
        return Response({"is_favorited": True}, status=status.HTTP_201_CREATED)


class FavoriteListView(APIView):
    """`GET /api/favorites/` — 自分のお気に入り（登録が新しい順）。"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = (
            Favorite.objects.filter(user=request.user)
            .select_related("library")
            # id を second key に入れて同時刻でも順序が揺れないようにする。
            .order_by("-created_at", "-id")
        )

        # ★ `Library.objects.filter(favorites__user=u).annotate(...)` にしていない。
        #   多値リレーション（favorites）への join になるので、filter の join が
        #   再利用されるかどうかで結果の件数が変わりうる。ここは 1 ユーザーあたり
        #   数十件の規模なので、Favorite を主体に 1 クエリ回して属性を載せるほうが
        #   読んで分かる（`select_related` で Library の N+1 は潰してある）。
        rows = []
        for favorite in favorites:
            library = favorite.library
            library.favorited_at = favorite.created_at
            rows.append(library)

        # bbox で切っていないので `truncated` は無い（docs/05-api.md）。
        return Response(
            {"count": len(rows), "results": FavoriteListSerializer(rows, many=True).data}
        )
