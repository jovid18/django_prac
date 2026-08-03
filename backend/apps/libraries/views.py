from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Library, SmokingStatus
from .serializers import LibraryDetailSerializer, LibraryListSerializer

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
