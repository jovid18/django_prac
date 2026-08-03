"""東京都の図書館データを取得して fixture を生成する。

    python manage.py fetch_libraries --dry-run
    python manage.py fetch_libraries --output apps/libraries/fixtures/libraries.json

生成した fixture は commit する。毎回 API を叩かなくても
`loaddata libraries` だけで環境を再現できるようにするため。

--------------------------------------------------------------------------
出所と、そう決めた理由（docs/04-data-model.md からの変更点）
--------------------------------------------------------------------------
当初は「名称と住所の CSV を人力で作り、国土地理院の住所検索で座標を引く」
計画だった。実際に調べたところ OpenStreetMap に東京都の図書館が約 490 件、
**名称と座標が 100% 揃った状態**で存在したため、そちらに切り替えた。

「確認していない座標をでっち上げない」という当初の原則は、実測値をそのまま
使うこちらのほうがより満たせる。人力の CSV 作成も不要になった。

  1. 名称・座標・website … OpenStreetMap (Overpass API)
  2. 区市町村           … addr:city → 名称からの推定 → 国土地理院 逆ジオコーディング
  3. 喫煙区分           … 固定シードの擬似乱数（★ 実在施設とは無関係のダミー）

★ OpenStreetMap のデータは ODbL。**出典表示が必要**なので UI に明記すること。
"""

import json
import random
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.libraries.models import DataSource, SmokingStatus

# 公開の Overpass インスタンスは混雑すると 429 / 504 を返す。
# ミラーを順に試し、各エンドポイントで数回リトライする。
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
]
GSI_REVERSE_URL = "https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress"
GSI_MUNI_URL = "https://maps.gsi.go.jp/js/muni.js"

OVERPASS_QUERY = """
[out:json][timeout:90];
area["name"="東京都"]["admin_level"="4"]->.tokyo;
(
  node["amenity"="library"](area.tokyo);
  way["amenity"="library"](area.tokyo);
);
out center tags;
"""

# 東京都のおおよその範囲。ここから外れた座標は採用しない。
TOKYO_BOUNDS = {"min_lat": 20.0, "max_lat": 36.0, "min_lng": 138.9, "max_lng": 142.5}

# 喫煙区分の出現比率（フィルタの動作確認ができればよいので均等でなくてよい）
SMOKING_WEIGHTS = [
    (SmokingStatus.NONE, 40),
    (SmokingStatus.HEATED_ONLY, 25),
    (SmokingStatus.CIGARETTE_ONLY, 15),
    (SmokingStatus.BOTH, 20),
]

USER_AGENT = "django-prac/0.1 (practice project; https://github.com/jovid18/django_prac)"

# loaddata は save_base(raw=True) で保存するため、auto_now_add / auto_now が働かない。
# fixture 側に値を持たせる必要がある。
#
# ここを timezone.now() にすると再生成のたびに全行の diff が出るので、固定値にする。
# シードデータの作成日時に意味はない。
SEED_TIMESTAMP = "2026-08-03T00:00:00Z"


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as res:  # noqa: S310
        return res.read()


def _post(url: str, data: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, data=data.encode("utf-8"), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as res:  # noqa: S310
        return res.read()


class Command(BaseCommand):
    help = "東京都の図書館データを取得して fixture を生成する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="apps/libraries/fixtures/libraries.json",
            help="出力先。--dry-run のときは書き込まない",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="件数と警告だけ表示し、ファイルを書かない",
        )
        parser.add_argument(
            "--seed", type=int, default=42, help="喫煙区分の割り当てに使う乱数シード"
        )
        parser.add_argument(
            "--skip-reverse",
            action="store_true",
            help="区市町村が埋まらなかった行の逆ジオコーディングを省く（オフライン確認用）",
        )

    # -- 取得 ---------------------------------------------------------------

    def _fetch_overpass(self, attempts_per_endpoint: int = 2) -> list[dict]:
        """ミラーを順に試す。混雑時の 429 / 504 は珍しくないため。"""
        last_error = None
        for url in OVERPASS_ENDPOINTS:
            for attempt in range(1, attempts_per_endpoint + 1):
                self.stdout.write(f"Overpass から取得中… {url} (試行 {attempt})")
                try:
                    raw = _post(url, OVERPASS_QUERY)
                except Exception as e:  # noqa: BLE001
                    last_error = e
                    self.stdout.write(self.style.WARNING(f"  失敗: {e}"))
                    time.sleep(5)
                    continue

                elements = json.loads(raw).get("elements", [])
                named = [e for e in elements if e.get("tags", {}).get("name")]
                self.stdout.write(f"  {len(elements)} 件取得、うち名称ありが {len(named)} 件")
                return named

        raise CommandError(f"どの Overpass エンドポイントからも取得できませんでした: {last_error}")

    def _fetch_muni_table(self) -> dict[str, str]:
        """国土地理院の自治体コード表を取得する（13101 → 千代田区）。"""
        text = _get(GSI_MUNI_URL).decode("utf-8", errors="replace")
        table = {}
        for code, body in re.findall(r'MUNI_ARRAY\["(\d+)"\]\s*=\s*\'([^\']+)\'', text):
            parts = body.split(",")
            if len(parts) >= 4:
                table[code] = parts[3].replace("　", " ").strip()
        return table

    def _reverse_ward(self, lat: float, lng: float, muni: dict[str, str]) -> str | None:
        params = urllib.parse.urlencode({"lat": lat, "lon": lng})
        try:
            raw = _get(f"{GSI_REVERSE_URL}?{params}", timeout=30)
            code = json.loads(raw).get("results", {}).get("muniCd")
        except Exception:
            return None
        if not code:
            return None
        # muniCd は先頭 0 が落ちて返ることがある
        return muni.get(str(code)) or muni.get(str(code).zfill(5))

    # -- 整形 ---------------------------------------------------------------

    @staticmethod
    def _ward_from_tags(tags: dict) -> str | None:
        """addr:city があればそれを、無ければ名称の先頭から推定する。

        「北区立中央図書館」→「北区」のように、日本の公立図書館は
        名称に自治体名が入っていることが多い。これで約半数が埋まる。
        """
        if city := tags.get("addr:city"):
            return city
        m = re.match(r"^(.+?[区市町村])", tags.get("name", ""))
        return m.group(1) if m else None

    @staticmethod
    def _address_from_tags(tags: dict) -> str:
        if tags.get("addr:full"):
            return tags["addr:full"]
        parts = [
            tags.get("addr:province", ""),
            tags.get("addr:city", ""),
            tags.get("addr:neighbourhood", ""),
            tags.get("addr:block_number", ""),
            tags.get("addr:housenumber", ""),
        ]
        return "".join(p for p in parts if p)

    def handle(self, *args, **opts):
        rng = random.Random(opts["seed"])
        weighted = [s for s, w in SMOKING_WEIGHTS for _ in range(w)]

        elements = self._fetch_overpass()

        rows, skipped, need_reverse = [], [], []

        for el in elements:
            tags = el["tags"]
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lng = el.get("lon") or el.get("center", {}).get("lon")

            if lat is None or lng is None:
                skipped.append((tags.get("name"), "座標なし"))
                continue

            # 東京都の想定範囲から外れた座標は黙って採用しない
            b = TOKYO_BOUNDS
            if not (b["min_lat"] <= lat <= b["max_lat"] and b["min_lng"] <= lng <= b["max_lng"]):
                skipped.append((tags.get("name"), f"範囲外 {lat},{lng}"))
                continue

            ward = self._ward_from_tags(tags)
            row = {
                "name": tags["name"][:120],
                "name_kana": (tags.get("name:ja-Hira") or "")[:160],
                "address": self._address_from_tags(tags)[:255],
                "ward": (ward or "")[:40],
                "latitude": f"{lat:.6f}",
                "longitude": f"{lng:.6f}",
                "smoking_status": rng.choice(weighted).value,
                "website": (tags.get("website") or "")[:300],
                "osm_id": f"{el['type']}/{el['id']}",
                "data_source": DataSource.OSM_OVERPASS.value,
                "created_at": SEED_TIMESTAMP,
                "updated_at": SEED_TIMESTAMP,
            }
            rows.append(row)
            if not ward:
                need_reverse.append(row)

        self.stdout.write(f"  採用 {len(rows)} 件 / 除外 {len(skipped)} 件")
        for name, why in skipped[:10]:
            self.stdout.write(self.style.WARNING(f"    除外: {name} — {why}"))

        # -- 区市町村が埋まらなかった行だけ逆ジオコーディングで補う ---------
        if need_reverse and not opts["skip_reverse"]:
            self.stdout.write(
                f"区市町村が未確定の {len(need_reverse)} 件を逆ジオコーディングします"
                "（1 件 1 秒。公共 API への礼儀）"
            )
            muni = self._fetch_muni_table()
            filled = 0
            for i, row in enumerate(need_reverse, 1):
                ward = self._reverse_ward(float(row["latitude"]), float(row["longitude"]), muni)
                if ward:
                    row["ward"] = ward[:40]
                    row["data_source"] = DataSource.GSI_REVERSE.value
                    filled += 1
                if i % 25 == 0:
                    self.stdout.write(f"    {i}/{len(need_reverse)}")
                time.sleep(1)
            self.stdout.write(f"  {filled} 件を補完しました")

        no_ward = sum(1 for r in rows if not r["ward"])
        wards = {r["ward"] for r in rows if r["ward"]}
        self.stdout.write("")
        self.stdout.write(
            f"  区市町村あり : {len(rows) - no_ward} / {len(rows)} 件（{len(wards)} 種類）"
        )
        self.stdout.write(f"  住所あり     : {sum(1 for r in rows if r['address'])} 件")
        self.stdout.write(f"  website あり : {sum(1 for r in rows if r['website'])} 件")

        fixture = [
            {"model": "libraries.library", "pk": i, "fields": row}
            for i, row in enumerate(rows, start=1)
        ]

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("\n--dry-run のためファイルは書きませんでした"))
            return

        path = Path(opts["output"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fixture, ensure_ascii=False, indent=1), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"\n{path} に {len(fixture)} 件を書き出しました"))
        self.stdout.write("次: python manage.py loaddata libraries")
