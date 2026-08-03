import { Map, type MapEvent, useMap } from '@vis.gl/react-google-maps'
import { type ReactNode, useEffect } from 'react'

import { env } from '../env'
import type { Bbox } from '../types/api'
import styles from './MapView.module.css'

/** 起動時の中心。現在地の許可は起動と同時に求めない（docs/07-frontend.md）。 */
const TOKYO_STATION = { lat: 35.681, lng: 139.767 }

export type MapViewState = {
  bbox: Bbox
  zoom: number
}

type Props = {
  /** 操作が落ち着いたら呼ばれる。`onIdle` なので自前のデバウンスは不要。 */
  onSettled: (view: MapViewState) => void
  /**
   * 地図インスタンスを 1 段上へ渡す。**検索結果から `panTo` するため。**
   * 破棄されたら `null` で呼ばれる。
   */
  onMapReady: (map: google.maps.Map | null) => void
  children?: ReactNode
}

export function MapView({ onSettled, onMapReady, children }: Props) {
  const handleIdle = (e: MapEvent) => {
    const bounds = e.map.getBounds()
    const zoom = e.map.getZoom()
    if (!bounds || zoom === undefined) return

    const sw = bounds.getSouthWest()
    const ne = bounds.getNorthEast()
    onSettled({
      zoom,
      bbox: { west: sw.lng(), south: sw.lat(), east: ne.lng(), north: ne.lat() },
    })
  }

  return (
    <Map
      mapId={env.googleMapsMapId}
      defaultCenter={TOKYO_STATION}
      defaultZoom={12}
      minZoom={9}
      // FOLLOW_SYSTEM 固定。⚠ colorScheme は初期化時にしか効かないので、
      // アプリ内トグルで切り替えると地図の作り直し = 1 map load になる。
      colorScheme="FOLLOW_SYSTEM"
      // 1 本指ドラッグで動かせるようにする。既定だとモバイルで詰まる。
      gestureHandling="greedy"
      // ↓ 課金対策（docs/07-frontend.md「課金の単位を間違えないこと」）
      reuseMaps // 画面遷移で地図を作り直さない
      streetViewControl={false} // Street View は別 SKU。ペグマンを踏ませない
      mapTypeControl={false}
      fullscreenControl={false}
      className={styles.map}
      onIdle={handleIdle}
    >
      <MapInstanceReporter onReady={onMapReady} />
      {children}
    </Map>
  )
}

/**
 * `useMap()` を呼んで、地図インスタンスを親に渡すだけのコンポーネント。
 *
 * ★ `useMap()` は `<Map>` の内側でしか取れない。**検索ボックスを地図の外に
 *   置いたまま `panTo` を呼べるようにするため**にこれを噛ませている。
 *   `<MapControl>` で検索ボックスごと地図の内側に入れる手もあるが、それだと
 *   **地図が死んだときに検索ボックスまで消える。** 地図が壊れてもアプリは
 *   動き続けるようにするのは Day 3 で決めた方針（docs/07-frontend.md）。
 */
function MapInstanceReporter({ onReady }: { onReady: (map: google.maps.Map | null) => void }) {
  const map = useMap()

  useEffect(() => {
    onReady(map)
    return () => onReady(null)
  }, [map, onReady])

  return null
}

export function MapPlaceholder({ title, detail }: { title: string; detail: string }) {
  return (
    <div className={styles.placeholder}>
      <p className={styles.placeholderTitle}>{title}</p>
      <p className={styles.placeholderDetail}>{detail}</p>
    </div>
  )
}
