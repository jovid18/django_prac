import pytest

from apps.libraries.models import Library, SmokingStatus


@pytest.fixture
def libraries(db):
    """東京駅・新宿・八王子・青ヶ島（伊豆諸島）に散らばらせる。

    青ヶ島を混ぜているのは、東京都が伊豆・小笠原諸島まで含むため。
    bbox で都心だけを切ったときに落ちることを確認したい。
    """
    data = [
        # name,           ward,      lat,        lng,         smoking
        ("東京駅前図書館", "千代田区", "35.681236", "139.767125", SmokingStatus.NONE),
        ("丸の内図書館", "千代田区", "35.682000", "139.768000", SmokingStatus.BOTH),
        ("新宿中央図書館", "新宿区", "35.689500", "139.700000", SmokingStatus.HEATED_ONLY),
        ("八王子図書館", "八王子市", "35.655900", "139.338900", SmokingStatus.CIGARETTE_ONLY),
        ("青ヶ島図書館", "青ヶ島村", "32.457000", "139.766000", SmokingStatus.BOTH),
    ]
    return [
        Library.objects.create(
            name=name,
            ward=ward,
            latitude=lat,
            longitude=lng,
            smoking_status=smoking,
            address=f"東京都{ward}",
        )
        for name, ward, lat, lng, smoking in data
    ]


@pytest.fixture
def tokyo_center_bbox():
    """東京駅まわりだけを含む bbox（min_lng,min_lat,max_lng,max_lat）。"""
    return "139.70,35.66,139.80,35.70"
