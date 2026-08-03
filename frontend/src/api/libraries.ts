import type { Bbox, LibraryDetail, LibraryListResponse, SmokingStatus } from '../types/api'
import { apiGet } from './client'

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
