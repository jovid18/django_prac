# 07. フロントエンド設計（React + Vite + MapLibre）

## プロジェクトの作り方

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router maplibre-gl react-map-gl @tanstack/react-query
```

> **`create-react-app` は使わない。** メンテナンスが止まっており、ビルドも遅い。Vite の `react-ts` テンプレートから始める。

## ディレクトリ構成

```
frontend/src/
├── main.tsx                 # エントリ。QueryClientProvider / AuthProvider / Router を巻く
├── App.tsx                  # ルート定義
├── env.ts                   # import.meta.env を 1 箇所で型付けして読む
│
├── api/
│   ├── client.ts            # fetch ラッパ。401 → refresh → リトライ
│   ├── auth.ts              # register / login / google / me / logout
│   └── libraries.ts         # 一覧 / 詳細 / nearby / favorite
│
├── auth/
│   ├── AuthContext.tsx      # user / accessToken / login / logout
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── GoogleButton.tsx     # Google Identity Services のボタン描画
│   └── RequireAuth.tsx      # 未ログインなら /login へ
│
├── map/
│   ├── MapPage.tsx          # 地図画面全体（地図 + フィルタ + 詳細パネル）
│   ├── MapView.tsx          # MapLibre のラッパ
│   ├── LibraryMarkers.tsx   # マーカー描画
│   ├── LibraryPanel.tsx     # 選択中の図書館の詳細
│   ├── SmokingFilter.tsx    # 喫煙区分フィルタ
│   ├── useGeolocation.ts    # 現在地フック
│   └── useLibraries.ts      # bbox が変わったら再取得する React Query フック
│
├── components/              # Button / Spinner / ErrorBox など汎用
└── types/
    └── api.ts               # API レスポンスの型
```

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
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "",           // ローカルは "" （プロキシ）
  googleClientId: import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID ?? "",
};
```

**Vite の環境変数は `VITE_` 接頭辞のものだけがバンドルに入る。** そして**バンドルに入るということは、ブラウザから丸見えということ**。ここに秘密の値を置かない。Google のクライアント ID は公開前提の値なので問題ない。

**ビルド時に埋め込まれる**ので、Render の Static Site 側で環境変数を設定してから再ビルドしないと反映されない（`08-deploy-render.md`）。

## 地図

### タイルソース

国土地理院（GSI）の標準地図タイルを使う。

```ts
const mapStyle: StyleSpecification = {
  version: 8,
  sources: {
    gsi: {
      type: "raster",
      tiles: ["https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 18,
      attribution:
        '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noreferrer">地理院タイル</a>',
    },
  },
  layers: [{ id: "gsi", type: "raster", source: "gsi" }],
};
```

| タイル種別 | URL の `xyz/` 以下 | 見た目 |
|---|---|---|
| 標準地図 | `std/{z}/{x}/{y}.png` | 情報量が多い |
| **淡色地図** | `pale/{z}/{x}/{y}.png` | **マーカーを載せるならこれ。** 地図が主張しない |
| 白地図 | `blank/{z}/{x}/{y}.png` | かなり素っ気ない |

**利用にあたっての決めごと**

- **出典表示は必須。** 上の `attribution` を必ず入れる（MapLibre が右下に自動表示する）。
- 大量アクセスをしない。ズーム範囲を `minzoom: 9` 程度に制限し、タイルの無駄な読み込みを抑える。
- 利用規約は[国土地理院タイルの利用について](https://maps.gsi.go.jp/development/ichiran.html)を実装前に一読すること。

> **代替案**: OpenStreetMap の標準タイル（`tile.openstreetmap.org`）も鍵なしで使えるが、Tile Usage Policy が本番サービスでの利用を推奨していない。今回の対象地域は東京なので、日本の公的機関が提供する GSI のほうが素直。

### 初期表示

```ts
const TOKYO_STATION = { longitude: 139.767, latitude: 35.681, zoom: 12 };
```

- 現在地の許可を**起動と同時に求めない。** 地図は先に東京駅中心で表示し、「現在地」ボタンが押されたときに初めて `getCurrentPosition` を呼ぶ。
  → いきなり権限ダイアログが出るとユーザーは反射的に拒否する。地図が見えている状態で押させたほうが許可率が高い。
- 拒否された / 失敗した場合も**すべての機能が動く**設計にする。現在地が無いと使えないのは `nearby` だけで、それはボタンを無効化して案内文を出す。

### `useGeolocation.ts`

```ts
type GeoState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "granted"; lat: number; lng: number }
  | { status: "denied" }
  | { status: "unavailable" };   // HTTPS でない / 非対応ブラウザ / タイムアウト
```

- `navigator.geolocation` は **HTTPS か `localhost` でしか動かない**。ローカルの `localhost:5173` は許可されるので開発中は問題ない。
- `getCurrentPosition` に `{ enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 }` を渡す。高精度を要求すると屋内で長時間待たされる。
- 状態を 5 つに分けているのは、**「まだ押していない」と「拒否された」で UI を変える**ため。拒否された場合は再度ボタンを押しても OS/ブラウザが黙って失敗させるので、「ブラウザの設定から許可してください」と案内する。

### `useLibraries.ts` — 地図の移動と再取得

```ts
// 概念
const [bbox, setBbox] = useState<Bbox | null>(null);
const [smoking, setSmoking] = useState<SmokingStatus[]>([]);

// 地図の moveend で bbox を更新（デバウンス 300ms）
// React Query のキーに bbox と smoking を含める
const { data, isFetching } = useQuery({
  queryKey: ["libraries", roundBbox(bbox), smoking],
  queryFn: () => fetchLibraries({ bbox, smoking }),
  enabled: bbox !== null,
  placeholderData: keepPreviousData,   // 再取得中に前のピンを消さない
  staleTime: 60_000,
});
```

**押さえどころ**

| 論点 | 決めごと |
|---|---|
| いつ再取得するか | `move` ではなく **`moveend`**。ドラッグ中に毎フレーム投げない |
| デバウンス | 300ms。連続操作をまとめる |
| `queryKey` の bbox | **小数第 3 位くらいに丸める**（`roundBbox`）。1px 動かすたびにキーが変わってキャッシュが効かなくなるのを防ぐ |
| 再取得中の表示 | `keepPreviousData` で前の結果を残す。**ピンが一瞬消えてまた出る**のが一番安っぽく見える |
| `truncated: true` のとき | 「表示件数の上限に達しています。地図を拡大してください」を地図上にトースト表示 |
| ズームが浅すぎるとき | `zoom < 10` なら**リクエストを投げない**。「地図を拡大してください」だけ出す |

### マーカー

- 件数が数十件なので、まずは `<Marker>` を素直に並べる。
- 色を喫煙区分で変える（不可=グレー / 加熱式=青 / 紙巻き=橙 / 両方=赤 など）。凡例を出す。
- **クラスタリングは Should。** 件数が増えたら `maplibre-gl` の `cluster: true` オプション付き GeoJSON ソースに切り替える。マーカーを DOM で並べる方式から GeoJSON レイヤー方式への変更になるので、**そのつもりで `LibraryMarkers.tsx` を切り出しておく**。

### 詳細パネル

- マーカークリック → 画面下（モバイル）/ 右（デスクトップ）にパネル。
- 表示: 名称 / 住所 / 区 / 喫煙区分 / 公式サイト / お気に入りボタン。
- **喫煙区分の横に注記を必ず出す**:
  > ※ このアプリの喫煙区分は開発練習用に自動生成したダミーデータで、実際の施設とは関係ありません。
- 未ログインでお気に入りを押したら、ログイン画面に飛ばす（戻り先を保持する）。

## 状態管理

| 状態 | 置き場所 |
|---|---|
| ログインユーザー / アクセストークン | `AuthContext`（React Context） |
| 図書館データ | React Query（サーバ状態はここに一元化） |
| 地図の bbox / 選択中の図書館 / フィルタ | `MapPage` の `useState` |

**Redux も Zustand も入れない。** この規模では Context + React Query で足りる。ライブラリを足すと「なぜそれが必要か」を説明できないまま構成が膨らむ。

## エラーとローディングの扱い

最低限、次の 4 つの状態を画面に出せるようにしておく。ここを省くと「動いているのか壊れているのか分からない画面」になる。

| 状態 | 表示 |
|---|---|
| 読み込み中 | 地図の隅に控えめなスピナー（全画面ローディングにしない） |
| 通信エラー | 「データを取得できませんでした / 再試行」ボタン |
| 0 件 | 「この範囲に図書館はありません」 |
| 上限到達 | 「表示上限に達しています。拡大してください」 |

## スタイリング

- **素の CSS Modules で十分。** UI ライブラリを入れるほどの画面数がない。
- ダークモードは `prefers-color-scheme` で最低限対応する（地図タイルは淡色のままでよい）。
- モバイル幅（375px）で地図とパネルが破綻しないことだけ確認する。

## TypeScript

- `strict: true` は最初から入れる（Vite のテンプレートは既に有効）。
- API レスポンスの型は `types/api.ts` に手書きする。**`drf-spectacular` を入れているなら `openapi-typescript` で自動生成してもよい**が、型定義がずれたときのデバッグが面倒なので、この規模なら手書きのほうが速い。
- `zod` で API レスポンスをパースすると、バックエンドの変更にフロントが気付ける。任意だが、練習としては価値がある。

## ビルドの確認

```bash
docker compose exec web npm run build       # tsc + vite build
docker compose exec web npm run preview     # 本番ビルドをローカルで確認
```

**`npm run build` は CI で必ず回す**（`09-ci-cd.md`）。`vite dev` は型エラーがあっても動いてしまうので、ビルドを通すまで型の壊れに気付けない。
