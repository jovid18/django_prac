import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { fetchLibraries } from '../api/libraries'
import type { Bbox, SmokingStatus } from '../types/api'
import type { MapViewState } from './MapView'

/** これより引いた状態では取りに行かない。都全域を毎回引くのを避ける。 */
export const MIN_FETCH_ZOOM = 10

/**
 * bbox を小数第 3 位に丸める（≒ 100m）。
 * 1px 動かすたびに queryKey が変わってキャッシュが効かなくなるのを防ぐ。
 */
const round3 = (n: number) => Math.round(n * 1000) / 1000

export const roundBbox = (b: Bbox): Bbox => ({
  west: round3(b.west),
  south: round3(b.south),
  east: round3(b.east),
  north: round3(b.north),
})

export function useLibraries(view: MapViewState | null, smoking: SmokingStatus[]) {
  const zoomTooLow = view !== null && view.zoom < MIN_FETCH_ZOOM
  const bbox = view && !zoomTooLow ? roundBbox(view.bbox) : null

  const query = useQuery({
    queryKey: ['libraries', bbox, smoking],
    queryFn: () => fetchLibraries({ bbox: bbox!, smoking }),
    enabled: bbox !== null,
    // 再取得中に前のピンを消さない。一瞬消えてまた出るのが一番安っぽく見える。
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  })

  return { ...query, zoomTooLow }
}
