import { Map, type MapEvent } from '@vis.gl/react-google-maps'
import type { ReactNode } from 'react'

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
  children?: ReactNode
}

export function MapView({ onSettled, children }: Props) {
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
      {children}
    </Map>
  )
}

export function MapPlaceholder({ title, detail }: { title: string; detail: string }) {
  return (
    <div className={styles.placeholder}>
      <p className={styles.placeholderTitle}>{title}</p>
      <p className={styles.placeholderDetail}>{detail}</p>
    </div>
  )
}
