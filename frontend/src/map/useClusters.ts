import { useMemo } from 'react'
import Supercluster from 'supercluster'

import type { Bbox, LibraryListItem } from '../types/api'

export type ClusterProps = { item: LibraryListItem }

// クラスタ側のプロパティ（point_count など）は supercluster が付けるので、
// 元の properties 型（ClusterProps）ではなく AnyProps になる。
export type ClusterFeature = Supercluster.ClusterFeature<Supercluster.AnyProps>
export type PointFeature = Supercluster.PointFeature<ClusterProps>
export type ClusterOrPoint = ClusterFeature | PointFeature

export const isCluster = (f: ClusterOrPoint): f is ClusterFeature =>
  (f.properties as { cluster?: boolean }).cluster === true

/**
 * クラスタリング。
 *
 * **マーカー要素ではなく、API から来た座標（データ）でクラスタを計算する。**
 * `@googlemaps/markerclusterer` はマーカーの DOM 要素から座標を読むが、
 * `<AdvancedMarker>` が `position` を入れるのは要素を作った後なので、
 * 計算のタイミングで座標が空（`[null, 0]`）になり**クラスタが 1 つも作られなかった**。
 * データ側で計算すれば、要素の生成タイミングに一切依存しない。
 *
 * `supercluster` は `@googlemaps/markerclusterer` が内部で使っているものと同じ実装。
 */
export function useClusters(items: LibraryListItem[], bbox: Bbox | null, zoom: number) {
  const index = useMemo(() => {
    // `radius` はピクセルではなく **`extent`（既定 512）に対する相対値**。
    // Google Maps のタイルは 256 CSS px なので、画面上の距離はこうなる:
    //
    //   画面 px = radius × 256 / extent = 120 × 256 / 512 = 60 px
    //
    // ズームに依らず常に画面上 60px で、これは Google 地図の POI の
    // まとまり方に近い体感。既定の 40（= 20px）や markerclusterer の
    // 60（= 30px）だと「2 件」の小さなクラスタが大量に出て煩い。
    //
    // `maxZoom: 16` は「z17 以上ではクラスタを作らない」の意味。
    const sc = new Supercluster<ClusterProps>({ radius: 120, maxZoom: 16 })
    sc.load(
      items.map((item) => ({
        type: 'Feature' as const,
        properties: { item },
        geometry: {
          type: 'Point' as const,
          coordinates: [Number(item.longitude), Number(item.latitude)],
        },
      })),
    )
    return sc
  }, [items])

  const clusters = useMemo<ClusterOrPoint[]>(() => {
    if (!bbox) return []
    return index.getClusters([bbox.west, bbox.south, bbox.east, bbox.north], Math.round(zoom))
  }, [index, bbox, zoom])

  return { index, clusters }
}
