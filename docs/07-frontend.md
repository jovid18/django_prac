# 07. フロントエンド設計（React + Vite + Google Maps）

## プロジェクトの作り方

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router @vis.gl/react-google-maps @googlemaps/markerclusterer @tanstack/react-query zod
```

> **`create-react-app` は使わない。** メンテナンスが止まっており、ビルドも遅い。Vite の `react-ts` テンプレートから始める。

> `@types/google.maps` は **`@vis.gl/react-google-maps` の依存に同梱されている**ので、別途インストールしない。

**テンプレートが実際に生成したもの（2026-08 / create-vite 9.1.2）**

| | |
|---|---|
| React | 19.2.8 |
| Vite | 8.2.0 |
| TypeScript | 6.0 |
| Lint | **oxlint**（eslint ではない） |

`create-vite` の既定が **oxlint** に変わっている。Rust 製で eslint より大幅に速く、設定は `.oxlintrc.json`、実行は `npm run lint`。**eslint に差し替えず、このまま使う。**

> **地図は当初 MapLibre GL JS + 国土地理院タイルで組んでいたが、Day 3 の前に Google Maps へ変更した。**
> 候補を実際に描画して比較した結果と、受け入れたコスト（課金アカウント・キーの制限）は
> [`00-decisions.md`](00-decisions.md) の「地図」の節にまとめてある。

## ディレクトリ構成

Day 4 までの実際の構成（当初案から名前が変わった箇所には理由を書いた）。

```
frontend/src/
├── main.tsx                 # エントリ。QueryClientProvider / BrowserRouter / AuthProvider を巻く
├── App.tsx                  # ルート定義
├── env.ts                   # import.meta.env を 1 箇所で型付けして読む
│
├── api/
│   ├── client.ts            # fetch ラッパ。アクセストークン保持 + 401 → refresh → 1 回リトライ
│   └── libraries.ts         # 一覧 / 詳細
│
├── auth/
│   ├── api.ts               # register / login / google / me / logout（api/auth.ts から移した。
│   │                        #   認証の型と呼び出しは auth/ に寄せたほうが追いやすい）
│   ├── context.ts           # Context 定義 + useAuth。**コンポーネントを含めない**
│   │                        #   （oxlint の react/only-export-components に引っかかる）
│   ├── AuthProvider.tsx     # 状態と起動時 refresh
│   ├── AuthPage.tsx         # ログインと登録を 1 枚で兼ねる（差分は文言と 1 フィールドだけ）
│   ├── AuthMenu.tsx         # ヘッダー右上のログイン状態
│   └── GoogleSignInButton.tsx
│
├── map/
│   ├── MapPage.tsx          # 地図画面全体（地図 + フィルタ + 詳細パネル）
│   ├── MapView.tsx          # <Map> のラッパ。カメラの初期値と onIdle をここに閉じる
│   ├── MapErrorBoundary.tsx # 地図の例外でアプリ全体を落とさないための境界
│   ├── LibraryMarkers.tsx   # AdvancedMarker（クラスタは useClusters で計算）
│   ├── LibraryPanel.tsx     # 選択中の図書館の詳細
│   ├── SmokingFilter.tsx    # 喫煙区分フィルタ
│   ├── useClusters.ts       # supercluster でクラスタを計算する
│   ├── useGeolocation.ts    # 現在地フック
│   ├── useLibraries.ts      # bbox が変わったら再取得する React Query フック
│   └── useMapsAuthFailure.ts # gm_authFailure を拾う
│
└── types/
    └── api.ts               # API レスポンスの型
```

**`components/` はまだ作っていない。** 汎用化したいものが 2 つ以上出てから作る。
`RequireAuth.tsx` も未作成（Day 5 のお気に入り画面で初めて必要になる）。

## 画面と経路

| パス | 画面 | 認証 |
|---|---|---|
| `/` | 地図（メイン） | 不要 |
| `/login` | ログイン | 不要 |
| `/register` | 会員登録 | 不要 |
| `/favorites` | お気に入り一覧（Should） | 必要 |

- **`/` は未ログインでも開ける。** 起動して最初に見えるのがログイン画面という構成にしない。
- ヘッダー右上に「ログイン」または「ユーザー名 / ログアウト」を出す。

## 環境変数

```ts
// src/env.ts
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "",              // ローカルは "" （プロキシ）
  googleClientId: import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID ?? "",
  googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? "",
  googleMapsMapId: import.meta.env.VITE_GOOGLE_MAPS_MAP_ID ?? "DEMO_MAP_ID",
};
```

**Vite の環境変数は `VITE_` 接頭辞のものだけがバンドルに入る。** そして**バンドルに入るということは、ブラウザから丸見えということ**。

ただし「丸見えでも困らない」かどうかは値によって違う。**ここを一緒くたにすると事故になる。**

| 変数 | 見えて困るか | 晒したときに起きること |
|---|---|---|
| `VITE_API_BASE_URL` | 困らない | 何も |
| `VITE_GOOGLE_OAUTH_CLIENT_ID` | 困らない | 何も（公開前提の値。シークレットは使わない構成） |
| **`VITE_GOOGLE_MAPS_API_KEY`** | **困る** | **他人が自分の請求先で Maps API を呼べる。** 必ず Cloud Console で「HTTP リファラー制限」＋「API の制限: Maps JavaScript API のみ」を掛ける |
| `VITE_GOOGLE_MAPS_MAP_ID` | 困らない | 何も（スタイルの識別子） |

**ビルド時に埋め込まれる**ので、Render の Static Site 側で環境変数を設定してから再ビルドしないと反映されない（`08-deploy-render.md`）。

## 地図

### 読み込み（`APIProvider`）

Maps JS API は `<script>` を自分で書かない。`APIProvider` が読み込みを管理する。

```tsx
// main.tsx
import { APIProvider } from "@vis.gl/react-google-maps";

<APIProvider apiKey={env.googleMapsApiKey}>
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </QueryClientProvider>
</APIProvider>;
```

- 追加ライブラリ（`marker` / `places` など）が必要なときは `useMapsLibrary("marker")` で取る。`APIProvider` の `libraries` に並べるより、使う場所で取るほうが依存が見える。
- **キーが空だと地図は出ない。** ローカルでも `.env` に `GOOGLE_MAPS_API_KEY` を入れる必要がある（`.env.example` 参照）。

### 地図本体

```tsx
import { Map } from "@vis.gl/react-google-maps";

const TOKYO_STATION = { lat: 35.681, lng: 139.767 };

<Map
  mapId={env.googleMapsMapId}
  defaultCenter={TOKYO_STATION}
  defaultZoom={12}
  minZoom={9}
  colorScheme="FOLLOW_SYSTEM"
  gestureHandling="greedy"
  reuseMaps
  style={{ width: "100%", height: "100%" }}
  onIdle={handleIdle}
/>;
```

| 論点 | 決めごと |
|---|---|
| `mapId` | **Advanced Markers に必須。** ローカルは Google 提供の `DEMO_MAP_ID` で足りる。配色を触りたくなったら Cloud Console で自前の Map ID を作る |
| `colorScheme` | `FOLLOW_SYSTEM`。⚠ **初期化時にしか効かない。** アプリ内にダーク切り替えトグルを付けるなら `<Map key={scheme} …>` で作り直す |
| `defaultCenter` / `defaultZoom` | `default` 付きは非制御。`center` / `zoom`（制御）にすると毎フレーム React に戻ってくるので、地図の操作が重くなる |
| `reuseMaps` | 画面遷移で地図インスタンスを使い回す。**無料枠は「地図ロード数」で数えるので、無駄な作り直しは課金に効く** |
| `gestureHandling` | `greedy`。1 本指ドラッグで動く。既定だとモバイルで「2 本指で操作してください」に詰まる |
| `minZoom: 9` | 東京都の外まで引かせない。範囲外を取りに行くリクエストが減る |
| 高さ | 親が高さを持っていないと**地図が潰れる**。`MapPage` 側で `height: 100dvh` などを確定させる |

### `useGeolocation.ts`

地図ライブラリを変えても**ここは変わらない**（ブラウザ標準 API）。

```ts
type GeoState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "granted"; lat: number; lng: number }
  | { status: "denied" }
  | { status: "unavailable" };   // HTTPS でない / 非対応ブラウザ / タイムアウト
```

- 現在地の許可を**起動と同時に求めない。** 地図は先に東京駅中心で表示し、「現在地」ボタンが押されたときに初めて `getCurrentPosition` を呼ぶ。
  → いきなり権限ダイアログが出るとユーザーは反射的に拒否する。
- `navigator.geolocation` は **HTTPS か `localhost` でしか動かない**。
- `getCurrentPosition` に `{ enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 }` を渡す。高精度を要求すると屋内で長時間待たされる。
- 状態を 5 つに分けているのは、**「まだ押していない」と「拒否された」で UI を変える**ため。拒否された場合は再度押しても OS/ブラウザが黙って失敗させるので、「ブラウザの設定から許可してください」と案内する。
- 拒否された / 失敗した場合も**すべての機能が動く**設計にする。現在地が無いと使えないのは `nearby` だけで、それはボタンを無効化して案内文を出す。

### `useLibraries.ts` — 地図の移動と再取得

```tsx
import type { MapEvent } from "@vis.gl/react-google-maps";

const handleIdle = (e: MapEvent) => {
  const b = e.map.getBounds();
  if (!b) return;
  const sw = b.getSouthWest();
  const ne = b.getNorthEast();
  setBbox(roundBbox({ west: sw.lng(), south: sw.lat(), east: ne.lng(), north: ne.lat() }));
};

const { data, isFetching } = useQuery({
  queryKey: ["libraries", bbox, smoking],
  queryFn: () => fetchLibraries({ bbox, smoking }),
  enabled: bbox !== null,
  placeholderData: keepPreviousData,   // 再取得中に前のピンを消さない
  staleTime: 60_000,
});
```

**押さえどころ**

| 論点 | 決めごと |
|---|---|
| いつ再取得するか | **`onIdle`。** 操作が落ち着いたあとに 1 回だけ発火するので、**自前のデバウンスが要らない** |
| `onCameraChanged` との違い | こちらは操作中ずっと発火する。代わりに `event.detail.bounds`（`{north, south, east, west}`）を**そのまま**もらえる。ドラッグ中の追従表示が欲しくなったらこちらを使い、デバウンスは自分で持つ |
| `queryKey` の bbox | **小数第 3 位くらいに丸める**（`roundBbox`）。1px 動かすたびにキーが変わってキャッシュが効かなくなるのを防ぐ |
| 再取得中の表示 | `keepPreviousData` で前の結果を残す。**ピンが一瞬消えてまた出る**のが一番安っぽく見える |
| `truncated: true` のとき | 「表示件数の上限に達しています。地図を拡大してください」を地図上にトースト表示 |
| ズームが浅すぎるとき | `zoom < 10` なら**リクエストを投げない**。「地図を拡大してください」だけ出す |

### マーカーとクラスタリング

**最初からクラスタリングを入れる。** API の既定 `limit` が 200 なので、1 画面に最大 200 個の
`AdvancedMarker`（= DOM ノード）が並びうる。後から入れると描画の作りを変えることになる。

**クラスタは `supercluster` で「データから」計算する。** マーカーの DOM 要素からではない。

```tsx
// map/useClusters.ts
const index = useMemo(() => {
  const sc = new Supercluster<{ item: LibraryListItem }>({ radius: 120, maxZoom: 16 });
  sc.load(
    items.map((item) => ({
      type: "Feature",
      properties: { item },
      geometry: { type: "Point", coordinates: [Number(item.longitude), Number(item.latitude)] },
    })),
  );
  return sc;
}, [items]);

const clusters = index.getClusters([bbox.west, bbox.south, bbox.east, bbox.north], Math.round(zoom));
```

描画側は「クラスタなら件数バブル、そうでなければ図書館のピン」を出すだけになる。

```tsx
isCluster(feature) ? (
  <AdvancedMarker position={pos} onClick={() => { map.panTo(pos); map.setZoom(index.getClusterExpansionZoom(id)); }}>
    <div className={styles.cluster}>{feature.properties.point_count}</div>
  </AdvancedMarker>
) : (
  <AdvancedMarker position={pos} onClick={() => onSelect(item)}>
    <Pin background={SMOKING_META[item.smoking_status].color} borderColor="#fff" glyphColor="#fff" />
  </AdvancedMarker>
)
```

> **⚠ `@googlemaps/markerclusterer` を最初に入れたが、外した。**
> あれは**マーカーの DOM 要素から座標を読む**。`<AdvancedMarker>` が要素に `position` を
> 入れるのはさらに後なので、クラスタ計算の時点で座標が `[null, 0]` になり
> **クラスタが 1 つも作られない**（200 個のピンが素で並ぶ）。
> `rAF` を 1 つ挟むといった対処はタイミング依存が残るので、
> **データ（API の緯度経度）から計算する形に変えた。** 中身のアルゴリズムは同じ `supercluster`。
> 副作用として、Google 既定のクラスタ描画（非推奨の `google.maps.Marker` を使う）も不要になった。

**`radius` はピクセルではない。** `extent`（既定 512）に対する相対値なので、画面上の距離は
`radius × 256 / extent`（Google のタイルは 256 CSS px）。**ズームに依らず一定**。

| `radius` | 画面上の距離 | 体感 |
|---|---|---|
| 40（supercluster 既定） | 20px | ほとんどまとまらない |
| 60（`markerclusterer` 既定） | 30px | 「2 件」の小さなクラスタが大量に出る |
| **120（採用）** | **60px** | Google 地図の POI のまとまりに近い |
| 160 | 80px | かなり大胆にまとまる |

- 色を喫煙区分で変える（不可=グレー / 加熱式=青 / 紙巻き=橙 / 両方=赤）。**凡例を兼ねたフィルタ UI を出す。**
- `maxZoom: 16` は「z17 以上ではクラスタを作らない」。
- `Pin` で足りない見た目にしたいときは `<AdvancedMarker>` の子に任意の JSX を置ける（DOM なので CSS が効く）。クラスタのバブルもこれで描いている。
- 実測: 200 件のとき **DOM のマーカー要素は 88 個**（クラスタ 54 + 単独ピン 34）に減った。

### 詳細パネル

- マーカークリック → 画面下（モバイル）/ 右（デスクトップ）にパネル。`InfoWindow` は情報量が増えると窮屈なので、パネルを主にする。
- 表示: 名称 / 住所 / 区 / 喫煙区分 / 公式サイト / お気に入りボタン。
- **喫煙区分の横に注記を必ず出す**:
  > ※ このアプリの喫煙区分は開発練習用に自動生成したダミーデータで、実際の施設とは関係ありません。
- 未ログインでお気に入りを押したら、ログイン画面に飛ばす（戻り先を保持する）。

### 出典表示

| 対象 | どう出すか |
|---|---|
| Google の地図 | ロゴと著作権表示が**地図に自動で出る**。**隠さない・重ねない** |
| 図書館データ（OpenStreetMap / ODbL） | **自分で出す。** 画面のどこかに「データ: © OpenStreetMap contributors (ODbL)」を置く |

> 地理院タイルを使わなくなったので、**国土地理院の表示義務は無くなった。**
> ただし区市町村の補完に地理院の逆ジオコーディングを使っている（`04-data-model.md`）ので、
> データ生成の出典としては引き続き `docs` に記録を残す。

### 課金の単位を間違えないこと

**Dynamic Maps の課金イベントは「successful map load」＝ `new google.maps.Map()` の回数だけ。**
公式の SKU 説明にこう書かれている。

> User interactions with the map don't generate additional map loads,
> including panning, zooming, or switching map layers.

| よくある誤解 | 実際 |
|---|---|
| 「ドラッグやズームでタイルを取るたびに課金される」 | **されない。** 490 件のピンの上で地図をいくら動かしても追加課金は 0 |
| 「タイルを CDN（Cloudflare など）でキャッシュすれば安くなる」 | **ならない。** タイル取得は課金対象ではないので節約額が 0。**そのうえ Maps のコンテンツのキャッシュ・保存は原則禁止**（例外は place ID）で、自分のサーバや CDN を間に挟むことも許されていない |
| 「サーバ側でキーを持ってプロキシすれば安全」 | **できない。** Maps JS はブラウザが Google と直接通信する構成。キーを API 経由で配っても最終的にブラウザに出る |

**節約できる唯一のレバーは「地図インスタンスを何回作るか」。**

| 状況 | コスト |
|---|---|
| ページを読み込む | **1 ロード**（SPA でもリロードすれば新しいインスタンス） |
| SPA 内で `/` ↔ `/login` を往復 | `reuseMaps` が無いと戻るたびに **+1** |
| ダークモード切り替えを `<Map key={scheme}>` で作り直す | **切り替えるたび +1** → `FOLLOW_SYSTEM` 固定にして、アプリ内トグルは UI 側だけに効かせるほうが安い |
| 開発中の保存・リロード | **1 回 1 ロード。開発が最大の消費者になる** |

### 課金を増やさないための決めごと

| やること | 効果 |
|---|---|
| **Cloud Console の Quotas で日次上限を掛ける** | **請求に対する唯一の実質的な防御。** 無料枠 10,000/月 ≒ 333/日 なので 300/日 程度で止める。キーが漏れても請求ではなくエラーで終わる |
| キーに HTTP リファラー制限を掛ける | 他人のサイトから使われるのを防ぐ（漏洩対策）。上の上限とセットで意味を持つ |
| `reuseMaps` を付ける | 画面遷移での作り直しを防ぐ |
| `streetViewControl={false}` | **Street View は別 SKU**（`Dynamic Street View` は Pro ティア・パノラマ単位）。既定 UI のペグマンを踏ませない。<br>※ 衛星写真・地形への切り替えは追加課金にならない（上の引用） |
| Places / Directions のライブラリを読み込まない | 使わなければ 0。`useMapsLibrary` で必要なものだけ取る |
| 一覧や詳細の小さな地図は **Maps Static API** にする | **Static Maps は別 SKU で無料枠も別枠**（ラッパに `StaticMap` / `createStaticMapsUrl` がある）。インタラクティブな地図は `/` だけに置く |
| 開発中は地図を描かないスイッチを持つ | フィルタ・パネル・一覧の UI を作っている間は地図が不要。プレースホルダに差し替えれば開発中の消費をほぼ 0 にできる |
| Cloud Console で予算アラートを設定する | 事後通知。上限の代わりにはならない |

## Day 3 で踏んだ落とし穴（同じ所で止まらないように）

| 症状 | 原因 | 対処 |
|---|---|---|
| **地図が真っ白。`bbox` の west と east が同じ値** | `index.css` に `main { max-width: 640px; padding: 48px 20px }` があり、地図の `<main>` にも当たって**幅が 0**になっていた（Day 1 の疎通確認画面用の指定） | **要素セレクタでレイアウトを決めない。** 画面ごとのレイアウトは CSS Modules に持たせる |
| **「有効なマップ ID を使用せずに地図が初期化されています」が延々と出て、Advanced Markers が壊れる** | `import.meta.env.VITE_GOOGLE_MAPS_MAP_ID ?? "DEMO_MAP_ID"` と書いたが、docker compose は未設定の変数を**空文字**で渡すので `??` ではフォールバックしない | **`??` ではなく `\|\|`。** 空文字も既定値に落とす |
| `Cannot find namespace 'google'` | `tsconfig.app.json` の `types: ["vite/client"]` があると、他の `@types/*` が自動で読まれない | `types` に **`"google.maps"`** を足す（型自体はラッパの依存に同梱） |
| `This syntax is not allowed when 'erasableSyntaxOnly' is enabled` | テンプレートが `erasableSyntaxOnly` を有効にしているので、**コンストラクタの引数プロパティ**（`constructor(readonly x: number)`）が使えない | 普通のフィールド宣言に書き換える |
| `Maximum update depth exceeded`（マーカーで無限ループ） | `ref={(m) => f(m, id)}` は毎レンダーで識別子が変わるため、React が「古い ref を null で呼ぶ → 新しい ref を呼ぶ」を繰り返す。そこで `setState` すると回り続ける | ref で受けた実体を state に入れない。**そもそもクラスタをデータ側で計算すれば ref は不要**（上の節） |
| 依存を入れ替えた直後に画面が白くなり `504 (Outdated Optimize Dep)` | Vite の依存最適化キャッシュが古い | `docker compose restart web` |

## Day 4 で踏んだ落とし穴

| 症状 | 原因 | 対処 |
|---|---|---|
| **リロードのたびにログアウトされる**（になりかけた） | access はメモリにしか持たないので、リロードで消える | 起動時に `refresh` を 1 回叩いて復帰させる（`AuthProvider`）。**その間の `loading` 状態を `anonymous` と混ぜない**。混ぜるとヘッダーが「ログイン」→ユーザー名にチラつく |
| **StrictMode で refresh が 2 本飛ぶ** | 開発時は effect が 2 回走る。`ROTATE_REFRESH_TOKENS` を有効にしているので、後から届いた方が**ブラックリスト済みの Cookie**を使い、正しいトークンまで無効化される | 進行中の refresh の Promise を保持して共有する（single-flight）。`client.ts` の `inFlightRefresh`。実測で「refresh は 1 回だけ」を確認した |
| 起動時に **Console に赤い 401 が出る** | 未ログインの初回アクセスでも `refresh` は 401 を返す。fetch の失敗はブラウザが必ずコンソールに出す | **異常ではない。** 消せないので消さない。仕様として覚えておく |
| Google のログインボタンのラベルが英語になる | GSI も既定はブラウザの言語に追従する。`renderButton` の `locale` だけでは効かなかった | スクリプト URL に **`?hl=ja`** を付ける（地図の `language="ja"` と同じ話） |
| `declare global { interface Window { google } }` を書くと型が壊れる | `@types/google.maps` が同名の `google` 名前空間を持っている | グローバル拡張をせず、参照する場所で `globalThis` をキャストして畳む（`GoogleSignInButton.tsx`） |

## 状態管理

| 状態 | 置き場所 |
|---|---|
| ログインユーザー / アクセストークン | `AuthContext`（React Context） |
| 図書館データ | React Query（サーバ状態はここに一元化） |
| 地図の bbox / 選択中の図書館 / フィルタ | `MapPage` の `useState` |

**Redux も Zustand も入れない。** この規模では Context + React Query で足りる。ライブラリを足すと「なぜそれが必要か」を説明できないまま構成が膨らむ。

## エラーとローディングの扱い

最低限、次の 5 つの状態を画面に出せるようにしておく。ここを省くと「動いているのか壊れているのか分からない画面」になる。

| 状態 | 表示 |
|---|---|
| 読み込み中 | 地図の隅に控えめなスピナー（全画面ローディングにしない） |
| 通信エラー | 「データを取得できませんでした / 再試行」ボタン |
| 0 件 | 「この範囲に図書館はありません」 |
| 上限到達 | 「表示上限に達しています。拡大してください」 |
| **地図が読めない** | キー未設定 / `VITE_MAP_ENABLED=0` は自前のプレースホルダ。**リファラー制限違反・請求先無効は下の節を参照**（検出方法が違う） |

### 地図の「キーが弾かれた」を検出する（実測して分かったこと）

`http://<LAN IP>:5173` から開いてリファラー制限違反を**実際に起こして**確認した。

| 分かったこと | 対処 |
|---|---|
| **`APIProvider` のロード状態では検出できない。** `RefererNotAllowedMapError` はスクリプトの読み込みに成功した**後**に起きるので、状態は `LOADED` のまま成功扱いになる | `window.gm_authFailure` に関数を代入して待つ（`useMapsAuthFailure.ts`）。Google が用意している唯一の入口 |
| Google は地図の枠内に**自前のライト配色のエラー画面**を出す。`colorScheme="FOLLOW_SYSTEM"` に追従しないので、ダークモードだと白い塊になる | 自分のプレースホルダに差し替える |
| **フッターが「152 件表示中」と嘘をつく。** 地図が死んでも API は生きているため、件数だけ正常に更新され続ける | `gm_authFailure` を見て「地図を読み込めていません」に差し替える |
| **アプリ全体が真っ暗になる。** Maps の内部状態が壊れた状態で `<AdvancedMarker>` が `Cannot read properties of undefined (reading 'getRootNode')` を投げ、React 19 が**ツリー全体を unmount する**（ヘッダーもフッターも消える） | **地図の周りにだけエラーバウンダリを置く**（`MapErrorBoundary.tsx`）。地図は「他人のコードが自分のツリーの中で DOM を触る」箇所なので、ここは境界を作る価値がある |

## スタイリング

- **素の CSS Modules で十分。** UI ライブラリを入れるほどの画面数がない。
- ダークモードは UI 側を `prefers-color-scheme` で、地図側を `colorScheme="FOLLOW_SYSTEM"` で対応する。
  ⚠ アプリ内トグルを付ける場合、地図の `colorScheme` は初期化時のみ有効なので `key` を変えて作り直す。
- **地図の上に置くボタンは白地固定**（`LocateControl.module.css`）。半透明 + `var(--fg)` にすると
  ダークの地図に溶けて見えなくなる。Google 純正のコントロールと同じ扱いにする。

### モバイル幅（375px）の確認結果（Day 4 で実測）

`375x667` をエミュレートして、詳細パネルを開いた状態まで確認した。

- 横スクロールは発生しない（`scrollWidth === clientWidth === 375`）。
- ヘッダーはタイトルと認証メニューが 1 行に収まる（収まらなくなったら `flex-wrap` で折り返す）。
- **見つかった実際の問題: 詳細パネルが Google のロゴを覆っていた。**
  480px 以下でパネルを左右いっぱい（`left/right: 10px`）に広げているため、地図の**左下**にある
  ロゴと重なる。**ロゴと著作権表示を覆うのは Maps の規約違反**なので、
  その帯（実測 22px 前後）の分だけ `bottom: 36px` で持ち上げた。
  デスクトップ幅では右寄せなので当たらない —— **だから幅を変えて見るまで気づけなかった。**

## TypeScript

- **`strict: true` は入れてある。** Vite のテンプレートには入っていなかったので、`tsconfig.app.json` に明示的に追加した（`00-decisions.md` の変更履歴）。
- API レスポンスの型は `types/api.ts` に手書きする。**`drf-spectacular` を入れているなら `openapi-typescript` で自動生成してもよい**が、型定義がずれたときのデバッグが面倒なので、この規模なら手書きのほうが速い。
- Google Maps の型は `@types/google.maps`（ラッパの依存に同梱）から `google.maps.*` として使える。`declare` は不要。
- `zod` で API レスポンスをパースすると、バックエンドの変更にフロントが気付ける。任意だが、練習としては価値がある。

## ビルドの確認

```bash
docker compose exec web npm run build       # tsc + vite build
docker compose exec web npm run preview     # 本番ビルドをローカルで確認
```

**`npm run build` は CI で必ず回す**（`09-ci-cd.md`）。`vite dev` は型エラーがあっても動いてしまうので、ビルドを通すまで型の壊れに気付けない。

> **地図エンジンをバンドルしなくなったので、ビルド結果は軽い。**
> MapLibre 構成では `index.js` が 1,181 kB（gzip 317 kB）+ CSS 70 kB + worker 468 kB だったが、
> Google 構成では **191 kB（gzip 61 kB）+ CSS 0.9 kB**。Maps JS は実行時に Google の CDN から読み込まれる。
