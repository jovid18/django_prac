from rest_framework import serializers

from .models import Library


class LibraryListSerializer(serializers.ModelSerializer):
    """一覧用。

    地図に数百件のマーカーを載せるので、**描画に要らない項目は詰めない**。
    住所や website は詳細で取りに行く（docs/05-api.md）。
    """

    smoking_status_label = serializers.CharField(
        source="get_smoking_status_display", read_only=True
    )

    class Meta:
        model = Library
        fields = [
            "id",
            "name",
            "ward",
            "latitude",
            "longitude",
            "smoking_status",
            "smoking_status_label",
        ]


class LibraryDetailSerializer(serializers.ModelSerializer):
    smoking_status_label = serializers.CharField(
        source="get_smoking_status_display", read_only=True
    )
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Library
        fields = [
            "id",
            "name",
            "name_kana",
            "address",
            "ward",
            "latitude",
            "longitude",
            "smoking_status",
            "smoking_status_label",
            "website",
            "osm_id",
            "data_source",
            "is_favorited",
            "updated_at",
        ]

    def get_is_favorited(self, obj) -> bool:
        user = getattr(self.context.get("request"), "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.favorites.filter(user=user).exists()
