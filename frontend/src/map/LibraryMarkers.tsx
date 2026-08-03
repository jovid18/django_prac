import { AdvancedMarker, Pin, useMap } from '@vis.gl/react-google-maps'

import type { Bbox, LibraryListItem } from '../types/api'
import styles from './LibraryMarkers.module.css'
import { SMOKING_META } from './smoking'
import { isCluster, useClusters } from './useClusters'

type Props = {
  items: LibraryListItem[]
  /** クラスタは表示範囲とズームで決まるので、地図の状態を受け取る */
  bbox: Bbox | null
  zoom: number
  selectedId: number | null
  onSelect: (item: LibraryListItem) => void
}

/**
 * 図書館のピンとクラスタ。
 *
 * API の既定 limit が 200 なので、1 画面に最大 200 個のマーカーが並びうる。
 * **クラスタリングは最初から入れる**（docs/07-frontend.md）。
 * クラスタの計算は `useClusters`（データ側で計算する理由もそこに書いてある）。
 */
export function LibraryMarkers({ items, bbox, zoom, selectedId, onSelect }: Props) {
  const map = useMap()
  const { index, clusters } = useClusters(items, bbox, zoom)

  return (
    <>
      {clusters.map((feature) => {
        const [lng, lat] = feature.geometry.coordinates
        const position = { lat, lng }

        if (isCluster(feature)) {
          const count = feature.properties.point_count
          return (
            <AdvancedMarker
              key={`cluster-${feature.id}`}
              position={position}
              title={`${count} 件`}
              onClick={() => {
                if (!map) return
                // クリックで「そのクラスタが解ける最小ズーム」まで寄る
                const next = index.getClusterExpansionZoom(Number(feature.id))
                map.panTo(position)
                map.setZoom(next)
              }}
            >
              <div
                className={styles.cluster}
                style={{ '--size': `${clusterSize(count)}px` } as React.CSSProperties}
              >
                {count}
              </div>
            </AdvancedMarker>
          )
        }

        const item = feature.properties.item
        const selected = item.id === selectedId
        return (
          <AdvancedMarker
            key={item.id}
            position={position}
            title={item.name}
            zIndex={selected ? 2 : 1}
            onClick={() => onSelect(item)}
          >
            <Pin
              background={SMOKING_META[item.smoking_status].color}
              borderColor="#ffffff"
              glyphColor="#ffffff"
              scale={selected ? 1.4 : 1}
            />
          </AdvancedMarker>
        )
      })}
    </>
  )
}

/** 件数で大きさを変える。数字が読める下限（36px）は確保する。 */
const clusterSize = (count: number) => Math.min(64, 36 + Math.log2(count) * 6)
