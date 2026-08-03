/** API レスポンスの型。手書きで持つ（docs/07-frontend.md）。 */

/** 喫煙区分。★ 練習用のダミー値で、実在の施設とは関係がない。 */
export const SMOKING_STATUSES = ['none', 'heated_only', 'cigarette_only', 'both'] as const
export type SmokingStatus = (typeof SMOKING_STATUSES)[number]

/**
 * 一覧の 1 件。
 *
 * ⚠ `latitude` / `longitude` は **文字列**で返る。
 *   モデルが `DecimalField` で、DRF の既定（`COERCE_DECIMAL_TO_STRING`）が
 *   Decimal を文字列にするため。Google Maps は number を要求するので、
 *   境界（`toLatLng`）で 1 回だけ変換する。
 */
export type LibraryListItem = {
  id: number
  name: string
  ward: string
  latitude: string
  longitude: string
  smoking_status: SmokingStatus
  smoking_status_label: string
}

export type LibraryListResponse = {
  count: number
  /** limit で打ち切られたか。true なら「拡大してください」を出す。 */
  truncated: boolean
  results: LibraryListItem[]
}

export type LibraryDetail = LibraryListItem & {
  name_kana: string
  address: string
  website: string
  osm_id: string
  data_source: string
  is_favorited: boolean
  updated_at: string
}

/** `nearby` の 1 件。一覧の項目に基準点からの距離（メートル、整数）が付く。 */
export type NearbyItem = LibraryListItem & {
  distance_m: number
}

export type NearbyListResponse = {
  count: number
  results: NearbyItem[]
}

/**
 * お気に入り一覧の 1 件。
 *
 * ★ `{library: {...}, created_at}` のようなネストではなく、
 *   **地図の一覧と同じ形に `address` / `favorited_at` を足した形**で返る
 *   （backend の `FavoriteListSerializer`）。詳細パネルなど
 *   `LibraryListItem` を受け取る側にそのまま渡せる。
 */
export type FavoriteItem = LibraryListItem & {
  address: string
  favorited_at: string
}

export type FavoriteListResponse = {
  count: number
  results: FavoriteItem[]
}

/** 地図の表示範囲。API には `min_lng,min_lat,max_lng,max_lat` の順で渡す。 */
export type Bbox = {
  west: number
  south: number
  east: number
  north: number
}

export const toLatLng = (item: LibraryListItem): google.maps.LatLngLiteral => ({
  lat: Number(item.latitude),
  lng: Number(item.longitude),
})
