"""図書館と、そのお気に入り。

設計の意図は docs/04-data-model.md を参照。要点:

- 座標は FloatField ではなく DecimalField(9, 6)
  小数 6 桁 ≒ 約 11cm。浮動小数の丸め誤差で差分比較が揺れるのを避ける。
- 喫煙区分は boolean 2 本ではなく単一の enum
  「加熱式のみ可」「紙巻きのみ可」を boolean では素直に表現できない。
- data_source を持つ
  座標をどこから取ったかを行ごとに残す。元プロジェクトで Google Maps 由来の
  座標に保持期限の制約があった件と同じ発想。
"""

from django.conf import settings
from django.db import models


class SmokingStatus(models.TextChoices):
    """★ 練習用のダミー値。実在する図書館の喫煙可否とは一切関係がない。

    元ドメイン（喫煙可能店のマッチング）のスキーマとフィルタ UI を
    練習するためだけに存在する。値はシード時に固定シードの擬似乱数で割り当てる。
    """

    NONE = "none", "喫煙不可"
    HEATED_ONLY = "heated_only", "加熱式のみ可"
    CIGARETTE_ONLY = "cigarette_only", "紙巻きのみ可"
    BOTH = "both", "両方可"


class DataSource(models.TextChoices):
    OSM_OVERPASS = "osm_overpass", "OpenStreetMap (Overpass API)"
    GSI_REVERSE = "gsi_reverse", "国土地理院 逆ジオコーディング"
    MANUAL = "manual", "手入力"


class Library(models.Model):
    name = models.CharField("名称", max_length=120)
    name_kana = models.CharField("よみ", max_length=160, blank=True)
    address = models.CharField("住所", max_length=255, blank=True)
    ward = models.CharField("区市町村", max_length=40, blank=True, db_index=True)

    latitude = models.DecimalField("緯度", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("経度", max_digits=9, decimal_places=6)

    smoking_status = models.CharField(
        "喫煙区分（練習用ダミー）",
        max_length=20,
        choices=SmokingStatus.choices,
        db_index=True,
    )

    website = models.URLField("公式サイト", max_length=300, blank=True)
    osm_id = models.CharField("OSM ID", max_length=32, blank=True, db_index=True)
    data_source = models.CharField(
        "座標の出所",
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.OSM_OVERPASS,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "図書館"
        verbose_name_plural = "図書館"
        ordering = ["id"]
        indexes = [
            # bbox 検索（緯度経度の範囲条件）で効かせる
            models.Index(fields=["latitude", "longitude"], name="idx_library_latlng"),
        ]
        constraints = [
            # シード投入を 2 回叩いても重複しないようにする upsert のキー
            models.UniqueConstraint(
                fields=["name", "latitude", "longitude"], name="uniq_library_spot"
            ),
        ]

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "お気に入り"
        verbose_name_plural = "お気に入り"
        constraints = [
            models.UniqueConstraint(fields=["user", "library"], name="uniq_user_library")
        ]

    def __str__(self):
        return f"{self.user.email} → {self.library.name}"
