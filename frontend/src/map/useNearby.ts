import { useQuery } from '@tanstack/react-query'

import { fetchNearby } from '../api/libraries'
import type { SmokingStatus } from '../types/api'
import type { GeoState } from './useGeolocation'

/** 表示件数と半径。API 側の上限は 50 件 / 20km（docs/05-api.md）。 */
export const NEARBY_LIMIT = 20
export const NEARBY_RADIUS_M = 3000

/** 現在地の丸め（小数 4 位 ≒ 11m）。GPS の揺れで queryKey が変わるのを防ぐ。 */
const round4 = (n: number) => Math.round(n * 10000) / 10000

/**
 * 現在地から近い順。
 *
 * ★ **現在地が取れていないときは投げない。** `lat` / `lng` 無しで呼ぶと
 *   API は 400 を返す（docs/05-api.md）。`enabled` でそれを保証している。
 */
export function useNearby(geo: GeoState, smoking: SmokingStatus[], active: boolean) {
  const at = geo.status === 'granted' ? { lat: round4(geo.lat), lng: round4(geo.lng) } : null

  return useQuery({
    queryKey: ['nearby', at, smoking],
    queryFn: () =>
      fetchNearby({
        lat: at!.lat,
        lng: at!.lng,
        radiusM: NEARBY_RADIUS_M,
        smoking,
        limit: NEARBY_LIMIT,
      }),
    enabled: active && at !== null,
    staleTime: 60_000,
  })
}
