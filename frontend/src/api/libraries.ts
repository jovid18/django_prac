import type {
  Bbox,
  FavoriteListResponse,
  LibraryDetail,
  LibraryListResponse,
  SmokingStatus,
} from '../types/api'
import { apiDelete, apiGet, apiPost } from './client'

/**
 * bbox のクエリ表記。
 * **経度が先**（`min_lng,min_lat,max_lng,max_lat`）。GeoJSON の慣習に合わせてあり、
 * 緯度から書くと 400 になる（backend/apps/libraries/views.py の `parse_bbox`）。
 */
export const bboxToParam = (b: Bbox) => `${b.west},${b.south},${b.east},${b.north}`

export function fetchLibraries(args: {
  bbox: Bbox
  smoking: SmokingStatus[]
}): Promise<LibraryListResponse> {
  return apiGet<LibraryListResponse>('/api/libraries/', {
    bbox: bboxToParam(args.bbox),
    smoking: args.smoking.join(','),
  })
}

export function fetchLibraryDetail(id: number): Promise<LibraryDetail> {
  return apiGet<LibraryDetail>(`/api/libraries/${id}/`)
}

/**
 * 名称・住所のテキスト検索。
 *
 * ★ **`bbox` を送らない。** 「表示範囲の外にある館へ飛ぶ」ための検索なので、
 *   bbox を付けると八王子を見ながら「新宿」を検索して 0 件、という
 *   説明のつかない挙動になる。結果をクリックしたら地図を動かす前提
 *   （docs/07-frontend.md）。
 */
export function searchLibraries(args: {
  q: string
  smoking: SmokingStatus[]
  limit: number
}): Promise<LibraryListResponse> {
  return apiGet<LibraryListResponse>('/api/libraries/', {
    q: args.q,
    smoking: args.smoking.join(','),
    limit: args.limit,
  })
}

// --- お気に入り -------------------------------------------------------------
//
// API 側はどちらも冪等（二重登録も未登録の解除も成功扱い）なので、
// フロントは「今どちらの状態か」を送る前に確認しなくてよい（docs/05-api.md）。

export function addFavorite(id: number): Promise<{ is_favorited: boolean }> {
  return apiPost<{ is_favorited: boolean }>(`/api/libraries/${id}/favorite/`)
}

export function removeFavorite(id: number): Promise<void> {
  return apiDelete(`/api/libraries/${id}/favorite/`)
}

export function fetchFavorites(): Promise<FavoriteListResponse> {
  return apiGet<FavoriteListResponse>('/api/favorites/')
}
